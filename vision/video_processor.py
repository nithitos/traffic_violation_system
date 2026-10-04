"""
Computer Vision Video Processing & AI Violation Detection Engine
Integrates YOLOv8 / OpenCV tracking, virtual stop lines, optical speed calculation, and ANPR.
"""
import math
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np

from ..config import EVIDENCE_DIR, SIGNAL_RED, SIGNAL_YELLOW, SIGNAL_GREEN
from ..database.db_manager import DatabaseManager
from ..detection.detector import ViolationDetector
from ..models.camera import TrafficCamera, DetectedObject
from .plate_reader import PlateReader

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except Exception:
    ULTRALYTICS_AVAILABLE = False


class TrackedVehicle:
    """Stores movement history and state for a single vehicle across video frames."""

    def __init__(self, track_id: int, bbox: Tuple[int, int, int, int], vehicle_type: str = "Car"):
        self.track_id = track_id
        self.bbox = bbox  # (x, y, w, h)
        self.vehicle_type = vehicle_type
        self.centroids: List[Tuple[int, int, float]] = []  # (cx, cy, timestamp)
        self.speed_kmh: float = 0.0
        self.plate_text: Optional[str] = None
        self.violated: bool = False
        self.violation_type: Optional[str] = None
        self.crossed_stop_line: bool = False
        self.last_seen: float = time.time()

        cx = bbox[0] + bbox[2] // 2
        cy = bbox[1] + bbox[3] // 2
        self.centroids.append((cx, cy, time.time()))

    def update(self, bbox: Tuple[int, int, int, int], pixel_to_meter: float = 0.05):
        """Update position and calculate instantaneous optical speed."""
        self.bbox = bbox
        self.last_seen = time.time()
        cx = bbox[0] + bbox[2] // 2
        cy = bbox[1] + bbox[3] // 2

        now = time.time()
        if self.centroids:
            prev_cx, prev_cy, prev_t = self.centroids[-1]
            dt = now - prev_t
            if dt > 0.03:  # At least 1-2 frames elapsed
                pixel_dist = math.sqrt((cx - prev_cx)**2 + (cy - prev_cy)**2)
                meter_dist = pixel_dist * pixel_to_meter
                speed_mps = meter_dist / dt
                calc_kmh = speed_mps * 3.6
                # Exponential moving average filter for stable speed display
                if self.speed_kmh == 0.0:
                    self.speed_kmh = round(calc_kmh, 1)
                else:
                    self.speed_kmh = round(0.7 * self.speed_kmh + 0.3 * calc_kmh, 1)

        self.centroids.append((cx, cy, now))
        if len(self.centroids) > 25:
            self.centroids.pop(0)


class VideoTrafficProcessor:
    """Processes video frames, tracks vehicles, detects violations, and runs ANPR."""

    def __init__(
        self,
        video_source: Any = 0,
        camera: Optional[TrafficCamera] = None,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.video_source = video_source
        self.camera = camera or TrafficCamera(
            camera_id="CAM-AI-01",
            junction_name="AI Video Surveillance Feed",
            latitude=13.0522,
            longitude=80.2503,
            speed_limit=50.0,
            signal_status="GREEN",
        )
        self.db = db_manager or DatabaseManager()
        self.detector = ViolationDetector(self.db)
        self.plate_reader = PlateReader()

        # Detection Model Setup
        self.yolo_model = None
        if ULTRALYTICS_AVAILABLE:
            try:
                # Load lightweight nano model
                self.yolo_model = YOLO("yolov8n.pt")
            except Exception:
                self.yolo_model = None

        # Fallback Background Subtractor for OpenCV
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=50, detectShadows=True)

        self.cap: Optional[cv2.VideoCapture] = None
        self.tracked_vehicles: Dict[int, TrackedVehicle] = {}
        self.next_track_id = 1
        self.is_running = False

        # Virtual Trap Lines (percentages of frame height)
        self.stop_line_ratio = 0.55
        self.speed_trap_ratio = 0.70

        # Stats
        self.fps = 0.0
        self.total_violations_detected = 0
        self.recent_plates: List[str] = []

    def start(self):
        """Open video capture stream."""
        if self.cap is not None:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.video_source)
        self.is_running = True

    def stop(self):
        """Release video capture stream."""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def process_frame(self, frame: np.ndarray, signal_status: Optional[str] = None) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Main frame analysis pipeline:
        1. Object Detection (YOLO or Background Subtraction)
        2. Centroid Tracking & Optical Speed
        3. Violation Rule Evaluation
        4. ANPR Plate Localization
        5. Visual HUD Annotation
        """
        if frame is None or frame.size == 0:
            return frame, []

        signal = signal_status or self.camera.signal_status
        h, w = frame.shape[:2]
        stop_line_y = int(h * self.stop_line_ratio)
        speed_trap_y = int(h * self.speed_trap_ratio)

        # 1. Detection
        detections = self._detect_vehicles(frame)

        # 2. Tracking Association
        self._update_tracks(detections)

        # 3. Violation Evaluation & ANPR
        active_violations = []
        for track_id, vehicle in list(self.tracked_vehicles.items()):
            vx, vy, vw, vh = vehicle.bbox
            cy = vy + vh // 2

            # Red Light Violation Check
            if signal == SIGNAL_RED and not vehicle.crossed_stop_line:
                if cy > stop_line_y:
                    vehicle.crossed_stop_line = True
                    vehicle.violated = True
                    vehicle.violation_type = "RED_SIGNAL"
                    self._record_video_violation(vehicle, frame, "RED_SIGNAL")
                    active_violations.append({"id": track_id, "type": "RED_SIGNAL", "plate": vehicle.plate_text})

            # Speed Limit Violation Check
            if vehicle.speed_kmh > self.camera.speed_limit and not vehicle.violated:
                vehicle.violated = True
                vehicle.violation_type = "OVER_SPEEDING"
                self._record_video_violation(vehicle, frame, "OVER_SPEEDING")
                active_violations.append({"id": track_id, "type": "OVER_SPEEDING", "plate": vehicle.plate_text})

            # Trigger ANPR if plate not yet read
            if not vehicle.plate_text and vy + vh < h:
                crop = frame[max(0, vy):min(h, vy + vh), max(0, vx):min(w, vx + vw)]
                plate_crop = self.plate_reader.localize_plate(crop)
                fallback = self._get_fallback_plate(track_id)
                vehicle.plate_text = self.plate_reader.read_plate_text(plate_crop, known_fallback=fallback)
                if vehicle.plate_text not in self.recent_plates:
                    self.recent_plates.append(vehicle.plate_text)
                    if len(self.recent_plates) > 10:
                        self.recent_plates.pop(0)

        # 4. Annotate Frame
        annotated = self._render_annotations(frame, signal, stop_line_y, speed_trap_y)
        return annotated, active_violations

    def _detect_vehicles(self, frame: np.ndarray) -> List[Tuple[Tuple[int, int, int, int], str]]:
        """Run YOLOv8 or OpenCV Background Subtractor to locate vehicles."""
        results = []

        if self.yolo_model:
            try:
                # Class 2: car, 3: motorcycle, 5: bus, 7: truck (COCO dataset)
                yolo_res = self.yolo_model(frame, classes=[2, 3, 5, 7], conf=0.35, verbose=False)[0]
                names = yolo_res.names
                for box in yolo_res.boxes:
                    cls_id = int(box.cls[0])
                    v_type = names.get(cls_id, "Car").title()
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    results.append(((x1, y1, x2 - x1, y2 - y1), v_type))
                return results
            except Exception:
                pass

        # Fallback: Background Subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        opening = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        dilated = cv2.dilate(opening, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > 2500:  # Minimum vehicle blob size
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = float(w) / float(h)
                if 0.5 <= aspect <= 3.0:
                    results.append(((x, y, w, h), "Car"))

        return results

    def _update_tracks(self, detections: List[Tuple[Tuple[int, int, int, int], str]]):
        """Associate detections to existing tracked vehicles using minimum Euclidean distance."""
        now = time.time()
        # Remove stale tracks older than 1.5 seconds
        self.tracked_vehicles = {
            t_id: v for t_id, v in self.tracked_vehicles.items() if now - v.last_seen < 1.5
        }

        unmatched_dets = list(detections)

        for track_id, vehicle in self.tracked_vehicles.items():
            vx, vy, vw, vh = vehicle.bbox
            v_cx, v_cy = vx + vw // 2, vy + vh // 2

            best_match = None
            min_dist = 85.0  # Max pixel search radius

            for det in unmatched_dets:
                (dx, dy, dw, dh), _ = det
                d_cx, d_cy = dx + dw // 2, dy + dh // 2
                dist = math.sqrt((v_cx - d_cx)**2 + (v_cy - d_cy)**2)
                if dist < min_dist:
                    min_dist = dist
                    best_match = det

            if best_match:
                vehicle.update(best_match[0])
                unmatched_dets.remove(best_match)

        # Create new tracks for remaining unmatched detections
        for det in unmatched_dets:
            bbox, v_type = det
            new_v = TrackedVehicle(self.next_track_id, bbox, v_type)
            self.tracked_vehicles[self.next_track_id] = new_v
            self.next_track_id += 1

    def _record_video_violation(self, vehicle: TrackedVehicle, frame: np.ndarray, violation_type: str):
        """Saves legal evidence snapshot and registers violation in database."""
        self.total_violations_detected += 1
        plate = vehicle.plate_text or self._get_fallback_plate(vehicle.track_id)

        # Trigger DB persistence & evidence snapshot
        detected_obj = DetectedObject(
            object_id=f"OBJ-VID-{vehicle.track_id}",
            vehicle_number=plate,
            vehicle_type=vehicle.vehicle_type,
            speed_kmh=vehicle.speed_kmh or 55.0,
            bbox=list(vehicle.bbox),
        )
        self.detector.analyze_event(self.camera, detected_obj)

    def _render_annotations(self, frame: np.ndarray, signal: str, stop_line_y: int, speed_trap_y: int) -> np.ndarray:
        """Draw bounding boxes, virtual stop lines, and HUD indicators on frame."""
        annotated = frame.copy()
        h, w = frame.shape[:2]

        # 1. Draw Virtual Stop Line
        stop_color = (0, 0, 255) if signal == SIGNAL_RED else (0, 255, 0)
        cv2.line(annotated, (0, stop_line_y), (w, stop_line_y), stop_color, 3)
        cv2.putText(annotated, f"VIRTUAL STOP-LINE ({signal})", (20, stop_line_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, stop_color, 2)

        # 2. Draw Virtual Speed Trap Line
        cv2.line(annotated, (0, speed_trap_y), (w, speed_trap_y), (255, 200, 0), 2)
        cv2.putText(annotated, "SPEED TRAP BOUNDARY", (20, speed_trap_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)

        # 3. Draw Vehicle Bounding Boxes & Tags
        for track_id, vehicle in self.tracked_vehicles.items():
            x, y, vw, vh = vehicle.bbox
            box_color = (0, 0, 255) if vehicle.violated else (0, 255, 120)

            # Bounding box
            cv2.rectangle(annotated, (x, y), (x + vw, y + vh), box_color, 2)

            # Top Tag Badge
            plate_display = vehicle.plate_text or f"VEH #{track_id}"
            speed_display = f"{vehicle.speed_kmh} km/h" if vehicle.speed_kmh > 0 else "Tracking..."
            tag_text = f"{plate_display} | {speed_display}"

            # Tag background
            cv2.rectangle(annotated, (x, max(0, y - 24)), (x + len(tag_text) * 9 + 10, y), box_color, -1)
            cv2.putText(annotated, tag_text, (x + 4, max(12, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)

            # Violation Alert Tag
            if vehicle.violated:
                vio_badge = f"! {vehicle.violation_type} !"
                cv2.rectangle(annotated, (x, y + vh), (x + len(vio_badge) * 9, y + vh + 20), (0, 0, 255), -1)
                cv2.putText(annotated, vio_badge, (x + 2, y + vh + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        # 4. Top HUD Dashboard
        cv2.rectangle(annotated, (0, 0), (w, 42), (20, 24, 33), -1)
        hud_text = f"CAM: {self.camera.camera_id} | SIGNAL: {signal} | VEHICLES: {len(self.tracked_vehicles)} | VIOLATIONS: {self.total_violations_detected}"
        cv2.putText(annotated, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        return annotated

    def _get_fallback_plate(self, track_id: int) -> str:
        """Deterministic plate numbers from registered database for sample demo vehicles."""
        sample_plates = ["TN07AB1234", "KA01EF9012", "TN09CD5678", "GJ01GH3456", "TN22JK7890"]
        return sample_plates[(track_id - 1) % len(sample_plates)]

    def generate_mjpeg_stream(self):
        """Generator yielding MJPEG encoded bytes for direct web streaming."""
        if not self.is_running or self.cap is None:
            self.start()

        while self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                # Loop video for continuous streaming
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            processed_frame, _ = self.process_frame(frame)
            _, buffer = cv2.imencode(".jpg", processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            time.sleep(0.03)  # ~30 FPS
