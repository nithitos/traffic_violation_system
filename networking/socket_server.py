"""
Socket Programming: Central Traffic Monitoring Server (Module 3)
Receives real-time telemetry from edge cameras, evaluates violations,
and broadcasts live alert notifications to connected dashboards.
"""
import json
import socket
import threading
import time
from typing import Callable, List, Optional, Dict, Any
from ..config import SOCKET_HOST, SOCKET_PORT, BUFFER_SIZE
from ..database.db_manager import DatabaseManager
from ..detection.detector import ViolationDetector
from ..models.camera import TrafficCamera, DetectedObject


class TrafficSocketServer:
    """Multi-threaded TCP Socket Server for live telemetry ingestion & alerts."""

    def __init__(
        self,
        host: str = SOCKET_HOST,
        port: int = SOCKET_PORT,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.host = host
        self.port = port
        self.db = db_manager or DatabaseManager()
        self.detector = ViolationDetector(self.db)

        self.server_socket: Optional[socket.socket] = None
        self.is_running = False
        self.clients: List[socket.socket] = []
        self.alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._thread: Optional[threading.Thread] = None

    def register_alert_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback to notify UI or subscribers of live violations."""
        self.alert_callbacks.append(callback)

    def start(self) -> None:
        """Start the socket server in a background daemon thread."""
        if self.is_running:
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.is_running = True

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        print(f"[Socket Server] Running on {self.host}:{self.port}")

    def stop(self) -> None:
        """Gracefully shut down server and close active client connections."""
        self.is_running = False
        for client in self.clients:
            try:
                client.close()
            except Exception:
                pass
        self.clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        print("[Socket Server] Stopped.")

    def _accept_loop(self) -> None:
        while self.is_running:
            try:
                self.server_socket.settimeout(1.0)
                client_sock, client_addr = self.server_socket.accept()
                self.clients.append(client_sock)
                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, client_addr),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, sock: socket.socket, addr: tuple) -> None:
        buffer = ""
        while self.is_running:
            try:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._process_message(sock, line.strip())
            except Exception:
                break

        if sock in self.clients:
            self.clients.remove(sock)
        try:
            sock.close()
        except Exception:
            pass

    def _process_message(self, sock: socket.socket, raw_json: str) -> None:
        try:
            payload = json.loads(raw_json)
            msg_type = payload.get("type", "EVENT")

            if msg_type == "CAMERA_EVENT":
                # Edge camera sending live vehicle detection
                cam_id = payload.get("camera_id")
                camera = self.db.get_camera(cam_id)
                if not camera:
                    camera = TrafficCamera(
                        camera_id=cam_id,
                        junction_name=payload.get("junction_name", "Unknown Junction"),
                        latitude=float(payload.get("latitude", 13.0)),
                        longitude=float(payload.get("longitude", 80.0)),
                        speed_limit=float(payload.get("speed_limit", 50.0)),
                        signal_status=payload.get("signal_status", "GREEN"),
                    )

                # Detected object
                obj_data = payload.get("detected_object", {})
                detected_obj = DetectedObject(
                    object_id=obj_data.get("object_id", "OBJ-1"),
                    vehicle_number=obj_data.get("vehicle_number"),
                    vehicle_type=obj_data.get("vehicle_type", "Car"),
                    speed_kmh=float(obj_data.get("speed_kmh", 40.0)),
                    bbox=obj_data.get("bbox", [200, 200, 200, 150]),
                    has_helmet=obj_data.get("has_helmet"),
                    seatbelt_fastened=obj_data.get("seatbelt_fastened"),
                    is_wrong_way=bool(obj_data.get("is_wrong_way", False)),
                    is_parked=bool(obj_data.get("is_parked", False)),
                    parked_duration_sec=float(obj_data.get("parked_duration_sec", 0.0)),
                )

                # Run violation detection
                violations = self.detector.analyze_event(camera, detected_obj)

                # Send response to edge client
                response = {
                    "status": "PROCESSED",
                    "violations_detected": len(violations),
                    "violation_ids": [v.violation_id for v in violations],
                }
                sock.sendall((json.dumps(response) + "\n").encode("utf-8"))

                # Broadcast live alerts to dashboard listeners
                for vio in violations:
                    alert_payload = vio.to_dict()
                    for cb in self.alert_callbacks:
                        try:
                            cb(alert_payload)
                        except Exception as e:
                            print(f"[Alert Callback Error]: {e}")

            elif msg_type == "PING":
                sock.sendall((json.dumps({"status": "PONG"}) + "\n").encode("utf-8"))

        except Exception as e:
            err_resp = {"status": "ERROR", "message": str(e)}
            try:
                sock.sendall((json.dumps(err_resp) + "\n").encode("utf-8"))
            except Exception:
                pass
