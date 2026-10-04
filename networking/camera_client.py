"""
Socket Programming: Edge Camera Simulator Client (Module 3)
Connects to the Central Traffic Monitoring Server and transmits live camera telemetry.
"""
import json
import socket
import time
from typing import Dict, Any, Optional
from ..config import SOCKET_HOST, SOCKET_PORT, BUFFER_SIZE


class CameraSocketClient:
    """Client representing a smart edge camera sending event packets to the central server."""

    def __init__(self, host: str = SOCKET_HOST, port: int = SOCKET_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to the central server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            return True
        except Exception:
            self.sock = None
            return False

    def close(self) -> None:
        """Close connection."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a single camera detection event packet and await server confirmation."""
        if not self.sock:
            if not self.connect():
                raise ConnectionError("Could not connect to central traffic socket server.")

        message = json.dumps(event_data) + "\n"
        self.sock.sendall(message.encode("utf-8"))

        # Read response
        response_data = b""
        while b"\n" not in response_data:
            chunk = self.sock.recv(BUFFER_SIZE)
            if not chunk:
                break
            response_data += chunk

        if not response_data:
            return {"status": "NO_RESPONSE"}

        line = response_data.decode("utf-8").strip().split("\n")[0]
        return json.loads(line)

    def trigger_sample_violation(
        self,
        camera_id: str = "CAM-CHN-01",
        vehicle_number: str = "TN-07-AB-1234",
        violation_scenario: str = "RED_SIGNAL",
    ) -> Dict[str, Any]:
        """Convenience method to trigger a specific violation scenario over socket."""
        signal = "GREEN"
        speed = 45.0
        wrong_way = False
        helmet = True
        seatbelt = True
        parked = False

        if violation_scenario == "RED_SIGNAL":
            signal = "RED"
            speed = 52.0
        elif violation_scenario == "OVER_SPEEDING":
            speed = 88.0
        elif violation_scenario == "WRONG_SIDE":
            wrong_way = True
        elif violation_scenario == "NO_HELMET":
            helmet = False
            vehicle_number = "TN-09-CD-5678"  # Motorcycle
        elif violation_scenario == "NO_SEATBELT":
            seatbelt = False
        elif violation_scenario == "ILLEGAL_PARKING":
            parked = True

        packet = {
            "type": "CAMERA_EVENT",
            "camera_id": camera_id,
            "signal_status": signal,
            "detected_object": {
                "object_id": "OBJ-LIVE-1",
                "vehicle_number": vehicle_number,
                "vehicle_type": "Motorcycle" if violation_scenario == "NO_HELMET" else "Car",
                "speed_kmh": speed,
                "bbox": [220, 240, 220, 150],
                "has_helmet": helmet,
                "seatbelt_fastened": seatbelt,
                "is_wrong_way": wrong_way,
                "is_parked": parked,
                "parked_duration_sec": 90.0 if parked else 0.0,
            },
        }
        return self.send_event(packet)
