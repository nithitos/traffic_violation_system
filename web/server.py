"""
Zero-Dependency Multi-Threaded Web & REST API Server
Integrates Python Modules 1-4 with a modern browser frontend.
"""
import cgi
import json
import mimetypes
import os
import sys
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.config import DB_PATH, EVIDENCE_DIR, REPORTS_DIR, DATA_DIR
from traffic_violation_system.database.db_manager import DatabaseManager
from traffic_violation_system.database.seed_data import seed_database
from traffic_violation_system.auth.auth_service import AuthService, ROLE_ADMIN, ROLE_TRAFFIC_OFFICER, ROLE_CONTROL_ROOM_OPERATOR
from traffic_violation_system.detection.detector import ViolationDetector
from traffic_violation_system.inputs.data_collector import DataCollector
from traffic_violation_system.inputs.sensor_simulator import SensorSimulator, TrafficSignalSimulator
from traffic_violation_system.models.camera import TrafficCamera, DetectedObject
from traffic_violation_system.processing.challan_service import ChallanService
from traffic_violation_system.processing.report_service import ReportService
from traffic_violation_system.vision.video_processor import VideoTrafficProcessor
from traffic_violation_system.vision.sample_video_generator import generate_sample_traffic_video

STATIC_DIR = Path(__file__).resolve().parent / "static"


class TrafficAPIHandler(SimpleHTTPRequestHandler):
    """Handles REST API endpoints and serves static dashboard files."""

    db: DatabaseManager = None
    auth: AuthService = None
    detector: ViolationDetector = None
    collector: DataCollector = None
    challan_svc: ChallanService = None
    report_svc: ReportService = None
    signal_sim: TrafficSignalSimulator = None
    video_processor: VideoTrafficProcessor = None

    @classmethod
    def initialize_services(cls):
        cls.db = DatabaseManager()
        seed_database(cls.db)
        cls.auth = AuthService(cls.db)
        cls.detector = ViolationDetector(cls.db)
        cls.collector = DataCollector(cls.db)
        cls.challan_svc = ChallanService(cls.db)
        cls.report_svc = ReportService(cls.db)
        cls.signal_sim = TrafficSignalSimulator()

        # Initialize AI Video Surveillance Stream
        sample_video = DATA_DIR / "sample_traffic.mp4"
        if not sample_video.exists():
            generate_sample_traffic_video(sample_video)
        cls.video_processor = VideoTrafficProcessor(video_source=str(sample_video), db_manager=cls.db)
        cls.video_processor.start()

    def do_OPTIONS(self):
        """Enable CORS pre-flight."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Live MJPEG Video Stream
        if path == "/api/video/feed":
            self._serve_mjpeg_stream()
            return

        # 1. API Endpoints
        if path.startswith("/api/"):
            self._handle_api_get(path, query)
            return

        # 2. Evidence Image Serving
        if path.startswith("/evidence/"):
            img_name = path[len("/evidence/"):]
            file_path = EVIDENCE_DIR / img_name
            if file_path.exists() and file_path.is_file():
                self._serve_file(file_path, "image/png")
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Evidence not found")
            return

        # 3. Login Page
        if path == "/login" or path == "/login.html":
            html_file = STATIC_DIR / "login.html"
            self._serve_file(html_file, "text/html; charset=utf-8")
            return

        # 4. Static Web Files (Dashboard)
        if path == "/" or path == "/index.html":
            html_file = STATIC_DIR / "index.html"
            self._serve_file(html_file, "text/html; charset=utf-8")
            return

        # Fallback to serving static files from STATIC_DIR
        file_path = STATIC_DIR / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            mime, _ = mimetypes.guess_type(str(file_path))
            self._serve_file(file_path, mime or "application/octet-stream")
        else:
            # Default to index.html for SPA routing
            html_file = STATIC_DIR / "index.html"
            self._serve_file(html_file, "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            raw_data = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw_data)
            except Exception:
                body = {}

        if path.startswith("/api/"):
            self._handle_api_post(path, body)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_api_get(self, path: str, query: Dict[str, Any]):
        try:
            # Signal tick & state
            current_signal = self.signal_sim.tick()

            if path == "/api/status":
                cameras = self.collector.get_all_junction_cameras()
                cam_list = [c.to_dict() for c in cameras]
                self._send_json({
                    "status": "ONLINE",
                    "current_signal": current_signal,
                    "cameras": cam_list,
                    "timestamp": datetime.now().isoformat(),
                })

            elif path == "/api/cameras":
                cameras = self.collector.get_all_junction_cameras()
                self._send_json([c.to_dict() for c in cameras])

            elif path == "/api/violations":
                limit = int(query.get("limit", [50])[0])
                vios = self.detector.get_recent_violations(limit=limit)
                self._send_json(vios)

            elif path == "/api/challans":
                status = query.get("status", [None])[0]
                items = self.challan_svc.get_all_challans(status=status)
                self._send_json(items)

            elif path == "/api/vehicles":
                vehicles = self.collector.get_all_registered_vehicles()
                self._send_json(vehicles)

            elif path == "/api/analytics":
                stats = self.report_svc.get_summary_statistics()
                self._send_json(stats)

            elif path == "/api/receipt":
                challan_id = query.get("id", [None])[0]
                if not challan_id:
                    self._send_json({"error": "Missing challan id"}, status=400)
                    return
                html_path = self.report_svc.generate_printable_receipt(challan_id)
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))

            elif path == "/api/export/violations":
                csv_path = self.report_svc.export_violations_csv()
                self._serve_download(csv_path, "violations_export.csv", "text/csv")

            elif path == "/api/export/challans":
                csv_path = self.report_svc.export_challans_csv()
                self._serve_download(csv_path, "challans_export.csv", "text/csv")

            elif path == "/api/video/stats":
                self._send_json({
                    "tracked_vehicles": len(self.video_processor.tracked_vehicles) if self.video_processor else 0,
                    "violations_detected": self.video_processor.total_violations_detected if self.video_processor else 0,
                    "recent_plates": self.video_processor.recent_plates if self.video_processor else [],
                    "signal_status": self.video_processor.camera.signal_status if self.video_processor else "GREEN",
                    "model": "YOLOv8 AI" if (self.video_processor and self.video_processor.yolo_model) else "OpenCV MOG2 Tracking",
                })

            elif path == "/api/map":
                # Returns cameras + recent violation pins for the live map
                cameras = self.collector.get_all_junction_cameras()
                conn = self.db.get_connection()
                cam_data = []
                for cam in cameras:
                    cur = conn.execute(
                        "SELECT COUNT(*) as cnt FROM violations WHERE camera_id = ?",
                        (cam.camera_id,)
                    )
                    row = cur.fetchone()
                    violation_count = row["cnt"] if row else 0
                    d = cam.to_dict()
                    d["violation_count"] = violation_count
                    cam_data.append(d)

                # Recent violation pins (last 30 with lat/lon)
                cur = conn.execute(
                    """SELECT violation_id, vehicle_number, violation_type, fine_amount,
                              latitude, longitude, location, timestamp, status
                       FROM violations
                       WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                       ORDER BY timestamp DESC LIMIT 30"""
                )
                pins = [dict(r) for r in cur.fetchall()]
                self._send_json({"cameras": cam_data, "violation_pins": pins})

            else:
                self._send_json({"error": f"Endpoint not found: {path}"}, status=404)

        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_api_post(self, path: str, body: Dict[str, Any]):
        try:
            if path == "/api/auth/login":
                username = body.get("username", "")
                password = body.get("password", "")
                try:
                    session = self.auth.login(username, password)
                    self._send_json({
                        "success": True,
                        "session": {
                            "user_id": session.user_id,
                            "username": session.username,
                            "role": session.role,
                            "full_name": session.full_name,
                            "display_role": session.display_role,
                        }
                    })
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=401)

            elif path == "/api/cameras/signal":
                camera_id = body.get("camera_id", "CAM-CHN-01")
                new_signal = body.get("signal_status", "GREEN").upper()
                self.signal_sim.force_state(new_signal)
                self.collector.update_signal_status(camera_id, new_signal)
                self._send_json({"success": True, "camera_id": camera_id, "signal_status": new_signal})

            elif path == "/api/violations/trigger":
                # Simulated detection trigger
                camera_id = body.get("camera_id", "CAM-CHN-01")
                scenario = body.get("scenario", "RED_SIGNAL")
                vehicle_num = body.get("vehicle_number")

                cam = self.db.get_camera(camera_id)
                if not cam:
                    cam = self.collector.get_all_junction_cameras()[0]

                # Default values
                speed = 42.0
                is_wrong_way = False
                has_helmet = True
                seatbelt = True
                is_parked = False
                parked_sec = 0.0
                v_type = "Car"

                if not vehicle_num:
                    vehicle_num = "TN-07-AB-1234"

                if scenario == "RED_SIGNAL":
                    cam.update_signal("RED")
                    self.signal_sim.force_state("RED")
                    speed = 52.0
                elif scenario == "OVER_SPEEDING":
                    cam.update_signal("GREEN")
                    speed = 88.5  # 38.5 km/h over 50 km/h limit -> fine multiplier
                elif scenario == "WRONG_SIDE":
                    is_wrong_way = True
                elif scenario == "NO_HELMET":
                    vehicle_num = "TN-09-CD-5678"  # Registered bike
                    v_type = "Motorcycle"
                    has_helmet = False
                elif scenario == "NO_SEATBELT":
                    seatbelt = False
                elif scenario == "ILLEGAL_PARKING":
                    is_parked = True
                    parked_sec = 95.0

                obj = DetectedObject(
                    object_id=f"OBJ-{datetime.now().strftime('%H%M%S')}",
                    vehicle_number=vehicle_num,
                    vehicle_type=v_type,
                    speed_kmh=speed,
                    bbox=[220, 240, 220, 150],
                    has_helmet=has_helmet,
                    seatbelt_fastened=seatbelt,
                    is_wrong_way=is_wrong_way,
                    is_parked=is_parked,
                    parked_duration_sec=parked_sec,
                )

                vios = self.detector.analyze_event(cam, obj)
                self._send_json({
                    "success": True,
                    "violations_detected": len(vios),
                    "violations": [v.to_dict() for v in vios],
                    "signal_state": cam.signal_status,
                })

            elif path == "/api/challans/generate":
                violation_id = body.get("violation_id")
                if not violation_id:
                    self._send_json({"error": "Missing violation_id"}, status=400)
                    return
                ch = self.challan_svc.generate_challan_from_violation(violation_id)
                self._send_json({"success": True, "challan": ch})

            elif path == "/api/challans/pay":
                challan_id = body.get("challan_id")
                ref = body.get("payment_reference")
                if not challan_id:
                    self._send_json({"error": "Missing challan_id"}, status=400)
                    return
                success = self.challan_svc.mark_challan_paid(challan_id, ref)
                self._send_json({"success": success, "challan_id": challan_id})

            elif path == "/api/video/source":
                src = body.get("source", "sample")
                if self.video_processor:
                    self.video_processor.stop()
                    if src == "webcam":
                        self.video_processor.video_source = 0
                    else:
                        sample_video = DATA_DIR / "sample_traffic.mp4"
                        self.video_processor.video_source = str(sample_video)
                    self.video_processor.start()
                self._send_json({"success": True, "source": src})

            else:
                self._send_json({"error": f"Endpoint not found: {path}"}, status=404)

        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _serve_mjpeg_stream(self):
        """Streams live processed video frames with bounding boxes as multipart/x-mixed-replace."""
        if not self.video_processor:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Video processor not initialized")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            for frame_chunk in self.video_processor.generate_mjpeg_stream():
                self.wfile.write(frame_chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, Exception):
            pass

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, file_path: Path, mime_type: str):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")

    def _serve_download(self, file_path: str, filename: str, mime: str):
        p = Path(file_path)
        if not p.exists():
            self._send_json({"error": "File not found"}, status=404)
            return
        with open(p, "rb") as f:
            data = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start_server(port: int = 5000):
    TrafficAPIHandler.initialize_services()
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, TrafficAPIHandler)
    print(f"[OK] Traffic Violation Web Server running at: http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    start_server(5000)
