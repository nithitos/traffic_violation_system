"""
Traffic Camera and Signal Data Model
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..config import SIGNAL_RED, SIGNAL_YELLOW, SIGNAL_GREEN, SPEED_LIMIT_DEFAULT_KMH


@dataclass
class TrafficCamera:
    camera_id: str
    junction_name: str
    latitude: float
    longitude: float
    speed_limit: float = SPEED_LIMIT_DEFAULT_KMH
    signal_status: str = SIGNAL_GREEN
    is_active: bool = True
    zone_type: str = "Standard"  # Standard, School Zone, Hospital Zone, Highway, No Parking

    def __post_init__(self):
        self.camera_id = self.camera_id.strip().upper()
        self.junction_name = self.junction_name.strip()
        self.signal_status = self.signal_status.strip().upper()
        if self.signal_status not in [SIGNAL_RED, SIGNAL_YELLOW, SIGNAL_GREEN]:
            raise ValueError(f"Invalid signal status: {self.signal_status}. Allowed: RED, YELLOW, GREEN")
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90. Got: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180. Got: {self.longitude}")

    def update_signal(self, new_status: str) -> None:
        status_norm = new_status.strip().upper()
        if status_norm not in [SIGNAL_RED, SIGNAL_YELLOW, SIGNAL_GREEN]:
            raise ValueError(f"Invalid signal status: {new_status}")
        self.signal_status = status_norm

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrafficCamera":
        return cls(
            camera_id=data["camera_id"],
            junction_name=data["junction_name"],
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            speed_limit=float(data.get("speed_limit", SPEED_LIMIT_DEFAULT_KMH)),
            signal_status=data.get("signal_status", SIGNAL_GREEN),
            is_active=bool(data.get("is_active", True)),
            zone_type=data.get("zone_type", "Standard"),
        )


@dataclass
class DetectedObject:
    """Represents a vehicle or person detected in a camera frame."""
    object_id: str
    vehicle_number: Optional[str]
    vehicle_type: str
    speed_kmh: float
    bbox: List[int] = field(default_factory=list)  # [x, y, width, height]
    has_helmet: Optional[bool] = None
    seatbelt_fastened: Optional[bool] = None
    is_wrong_way: bool = False
    is_parked: bool = False
    parked_duration_sec: float = 0.0


@dataclass
class CameraFrame:
    """Represents a live snapshot or video frame capture from a traffic camera."""
    frame_id: str
    camera_id: str
    timestamp: str
    signal_status: str
    detected_objects: List[DetectedObject] = field(default_factory=list)
    image_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "signal_status": self.signal_status,
            "detected_objects": [asdict(obj) for obj in self.detected_objects],
            "image_path": self.image_path,
        }
