"""
Traffic Camera Stream and Snapshot Simulator
Generates visual camera frames with junction overlays, traffic light status,
and vehicle detection bounding boxes.
"""
import os
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from ..config import EVIDENCE_DIR, SIGNAL_RED, SIGNAL_YELLOW, SIGNAL_GREEN
from ..models.camera import TrafficCamera, CameraFrame, DetectedObject

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class CameraSimulator:
    """Generates synthetic video frames and evidence snapshots for traffic cameras."""

    def __init__(self, camera: TrafficCamera):
        self.camera = camera
        self.frame_counter = 0

    def capture_frame(
        self,
        detected_vehicles: Optional[List[DetectedObject]] = None,
        save_snapshot: bool = False,
        custom_signal: Optional[str] = None,
    ) -> CameraFrame:
        """Capture or generate a simulated camera frame."""
        self.frame_counter += 1
        signal = custom_signal or self.camera.signal_status
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame_id = f"FRM-{self.camera.camera_id}-{self.frame_counter:05d}"

        if detected_vehicles is None:
            detected_vehicles = self._generate_default_detections()

        image_path = None
        if save_snapshot:
            filename = f"capture_{self.camera.camera_id}_{self.frame_counter}_{int(datetime.now().timestamp())}.png"
            image_path = str(EVIDENCE_DIR / filename)
            self._render_and_save_image(
                image_path=image_path,
                signal=signal,
                timestamp_str=timestamp_str,
                detected_vehicles=detected_vehicles,
            )

        return CameraFrame(
            frame_id=frame_id,
            camera_id=self.camera.camera_id,
            timestamp=timestamp_str,
            signal_status=signal,
            detected_objects=detected_vehicles,
            image_path=image_path,
        )

    def _generate_default_detections(self) -> List[DetectedObject]:
        """Generate a random passing vehicle for continuous feed."""
        plates = ["TN-07-AB-1234", "KA-01-EF-9012", "TN-09-CD-5678", "TN-22-JK-7890"]
        types = ["Car", "Car", "Motorcycle", "Auto Rickshaw"]
        idx = random.randint(0, len(plates) - 1)
        speed = round(random.uniform(35.0, 58.0), 1)

        return [
            DetectedObject(
                object_id=f"OBJ-{random.randint(100, 999)}",
                vehicle_number=plates[idx],
                vehicle_type=types[idx],
                speed_kmh=speed,
                bbox=[180, 220, 240, 160],
                has_helmet=True if types[idx] == "Motorcycle" else None,
                seatbelt_fastened=True if types[idx] == "Car" else None,
                is_wrong_way=False,
                is_parked=False,
            )
        ]

    def _render_and_save_image(
        self,
        image_path: str,
        signal: str,
        timestamp_str: str,
        detected_vehicles: List[DetectedObject],
    ) -> None:
        """Render a realistic traffic snapshot with road, signal, and vehicle overlay."""
        if not PIL_AVAILABLE:
            # Fallback text representation if PIL is unavailable
            with open(image_path + ".txt", "w", encoding="utf-8") as f:
                f.write(f"CAM: {self.camera.camera_id} | Junction: {self.camera.junction_name}\n")
                f.write(f"Signal: {signal} | Time: {timestamp_str}\n")
                for obj in detected_vehicles:
                    f.write(f"Detected: {obj.vehicle_number} ({obj.vehicle_type}) at {obj.speed_kmh} km/h\n")
            return

        # Canvas Dimensions
        width, height = 720, 480
        img = Image.new("RGB", (width, height), color=(45, 52, 54))  # Dark asphalt
        draw = ImageDraw.Draw(img)

        # Draw Road Lane Markings (White dashed lines)
        draw.line([(width // 2, 80), (width // 2, height)], fill=(255, 255, 255), width=4)
        for y in range(100, height, 40):
            draw.line([(width // 4, y), (width // 4, y + 20)], fill=(223, 230, 233), width=2)
            draw.line([(3 * width // 4, y), (3 * width // 4, y + 20)], fill=(223, 230, 233), width=2)

        # Draw Stop Line
        draw.line([(0, 340), (width, 340)], fill=(255, 255, 255), width=6)

        # Draw Traffic Signal Box (Top Right)
        sig_x, sig_y = width - 70, 20
        draw.rectangle([sig_x, sig_y, sig_x + 50, sig_y + 110], fill=(20, 20, 20), outline=(200, 200, 200), width=2)
        # Red lamp
        red_fill = (255, 30, 30) if signal == SIGNAL_RED else (70, 20, 20)
        draw.ellipse([sig_x + 15, sig_y + 10, sig_x + 35, sig_y + 30], fill=red_fill)
        # Yellow lamp
        yel_fill = (255, 200, 0) if signal == SIGNAL_YELLOW else (70, 60, 10)
        draw.ellipse([sig_x + 15, sig_y + 45, sig_x + 35, sig_y + 65], fill=yel_fill)
        # Green lamp
        grn_fill = (0, 230, 80) if signal == SIGNAL_GREEN else (10, 60, 20)
        draw.ellipse([sig_x + 15, sig_y + 80, sig_x + 35, sig_y + 100], fill=grn_fill)

        # Draw Vehicle Bounding Boxes & Tags
        for obj in detected_vehicles:
            bbox = obj.bbox or [240, 260, 200, 140]
            x, y, w, h = bbox
            draw.rectangle([x, y, x + w, y + h], outline=(0, 200, 255), width=3)
            # Vehicle body placeholder
            draw.rectangle([x + 10, y + 10, x + w - 10, y + h - 10], fill=(60, 99, 130))
            # License Plate Label Tag
            tag_text = f"{obj.vehicle_number or 'UNKNOWN'} | {obj.speed_kmh} km/h"
            draw.rectangle([x, y - 22, x + 220, y], fill=(0, 200, 255))
            draw.text((x + 6, y - 18), tag_text, fill=(0, 0, 0))

        # Top Information Header Banner
        draw.rectangle([0, 0, width, 40], fill=(15, 20, 30))
        header_text = f"CAM: {self.camera.camera_id} - {self.camera.junction_name} | SPEED LIMIT: {self.camera.speed_limit} km/h | {timestamp_str}"
        draw.text((15, 12), header_text, fill=(255, 255, 255))

        # Save to disk
        img.save(image_path, "PNG")
