"""
Violation Types and Data Transfer Objects (Module 3)
"""
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any


class ViolationType(str, Enum):
    RED_SIGNAL = "RED_SIGNAL"
    OVER_SPEEDING = "OVER_SPEEDING"
    WRONG_SIDE = "WRONG_SIDE"
    NO_HELMET = "NO_HELMET"
    NO_SEATBELT = "NO_SEATBELT"
    ILLEGAL_PARKING = "ILLEGAL_PARKING"

    @property
    def display_name(self) -> str:
        names = {
            self.RED_SIGNAL: "Red Signal Violation",
            self.OVER_SPEEDING: "Speed Limit Violation",
            self.WRONG_SIDE: "Wrong Side Driving",
            self.NO_HELMET: "Riding Without Helmet",
            self.NO_SEATBELT: "Driving Without Seatbelt",
            self.ILLEGAL_PARKING: "Illegal Parking Violation",
        }
        return names.get(self, self.value)


@dataclass
class ViolationEvent:
    violation_id: str
    vehicle_number: str
    driver_id: Optional[str]
    driver_name: Optional[str]
    violation_type: str
    fine_amount: float
    camera_id: str
    location: str
    latitude: float
    longitude: float
    speed_detected: float
    speed_limit: float
    timestamp: str
    evidence_image_path: Optional[str] = None
    status: str = "RECORDED"  # RECORDED, CHALLAN_ISSUED, DISMISSED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ViolationEvent":
        return cls(
            violation_id=data["violation_id"],
            vehicle_number=data["vehicle_number"],
            driver_id=data.get("driver_id"),
            driver_name=data.get("driver_name"),
            violation_type=data["violation_type"],
            fine_amount=float(data["fine_amount"]),
            camera_id=data["camera_id"],
            location=data["location"],
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            speed_detected=float(data.get("speed_detected", 0.0)),
            speed_limit=float(data.get("speed_limit", 0.0)),
            timestamp=data["timestamp"],
            evidence_image_path=data.get("evidence_image_path"),
            status=data.get("status", "RECORDED"),
        )
