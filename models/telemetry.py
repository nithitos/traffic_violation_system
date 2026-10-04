"""
GPS and Sensor Telemetry Data Models
"""
import math
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from ..config import (
    IMPACT_THRESHOLD_NORMAL_G,
    IMPACT_THRESHOLD_WARNING_G,
    IMPACT_THRESHOLD_COLLISION_G,
    TILT_THRESHOLD_ROLLOVER_DEG,
)


class ImpactSeverity(str, Enum):
    NORMAL = "NORMAL"
    MILD_VIBRATION = "MILD_VIBRATION"
    HARSH_BRAKING = "HARSH_BRAKING"
    POTENTIAL_COLLISION = "POTENTIAL_COLLISION"
    CRITICAL_ACCIDENT = "CRITICAL_ACCIDENT"


class VehicleStatus(str, Enum):
    MOVING = "MOVING"
    IDLE = "IDLE"
    STOPPED = "STOPPED"
    PARKED = "PARKED"
    CRASHED = "CRASHED"
    TILTED = "TILTED"


@dataclass
class GPSData:
    vehicle_number: str
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    heading_deg: float = 0.0  # 0 to 360 degrees
    altitude_m: float = 0.0
    location_name: str = ""
    timestamp: str = ""

    def __post_init__(self):
        self.vehicle_number = self.vehicle_number.strip().upper()
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude out of bounds [-90, 90]: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude out of bounds [-180, 180]: {self.longitude}")
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GPSData":
        return cls(
            vehicle_number=data["vehicle_number"],
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            speed_kmh=float(data.get("speed_kmh", 0.0)),
            heading_deg=float(data.get("heading_deg", 0.0)),
            altitude_m=float(data.get("altitude_m", 0.0)),
            location_name=data.get("location_name", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class SensorData:
    vehicle_number: str
    accel_x_g: float = 0.0  # Lateral acceleration in G
    accel_y_g: float = 0.0  # Longitudinal acceleration in G
    accel_z_g: float = 1.0  # Vertical acceleration in G (gravity ~ 1.0G)
    tilt_pitch_deg: float = 0.0  # Forward/backward inclination
    tilt_roll_deg: float = 0.0   # Sideways lean angle
    airbag_deployed: bool = False
    seatbelt_buckled: bool = True
    helmet_worn: Optional[bool] = None  # Relevant for 2-wheelers
    engine_running: bool = True
    timestamp: str = ""

    def __post_init__(self):
        self.vehicle_number = self.vehicle_number.strip().upper()
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def total_g_force(self) -> float:
        """Calculate resultant total G-force vector magnitude."""
        return math.sqrt(self.accel_x_g**2 + self.accel_y_g**2 + self.accel_z_g**2)

    @property
    def impact_severity(self) -> ImpactSeverity:
        """Classify impact severity according to sensor thresholds."""
        g = self.total_g_force
        if self.airbag_deployed or g >= IMPACT_THRESHOLD_COLLISION_G:
            return ImpactSeverity.CRITICAL_ACCIDENT
        elif g >= IMPACT_THRESHOLD_WARNING_G:
            return ImpactSeverity.POTENTIAL_COLLISION
        elif abs(self.accel_y_g) >= 1.5:
            return ImpactSeverity.HARSH_BRAKING
        elif g > IMPACT_THRESHOLD_NORMAL_G:
            return ImpactSeverity.MILD_VIBRATION
        return ImpactSeverity.NORMAL

    @property
    def vehicle_status(self) -> VehicleStatus:
        """Derive vehicle status from sensor readings."""
        if self.impact_severity == ImpactSeverity.CRITICAL_ACCIDENT:
            return VehicleStatus.CRASHED
        if abs(self.tilt_roll_deg) >= TILT_THRESHOLD_ROLLOVER_DEG or abs(self.tilt_pitch_deg) >= TILT_THRESHOLD_ROLLOVER_DEG:
            return VehicleStatus.TILTED
        if not self.engine_running:
            return VehicleStatus.STOPPED
        return VehicleStatus.MOVING

    def is_rollover(self) -> bool:
        return abs(self.tilt_roll_deg) >= TILT_THRESHOLD_ROLLOVER_DEG

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_g_force"] = round(self.total_g_force, 2)
        data["impact_severity"] = self.impact_severity.value
        data["vehicle_status"] = self.vehicle_status.value
        data["is_rollover"] = self.is_rollover()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SensorData":
        return cls(
            vehicle_number=data["vehicle_number"],
            accel_x_g=float(data.get("accel_x_g", 0.0)),
            accel_y_g=float(data.get("accel_y_g", 0.0)),
            accel_z_g=float(data.get("accel_z_g", 1.0)),
            tilt_pitch_deg=float(data.get("tilt_pitch_deg", 0.0)),
            tilt_roll_deg=float(data.get("tilt_roll_deg", 0.0)),
            airbag_deployed=bool(data.get("airbag_deployed", False)),
            seatbelt_buckled=bool(data.get("seatbelt_buckled", True)),
            helmet_worn=data.get("helmet_worn"),
            engine_running=bool(data.get("engine_running", True)),
            timestamp=data.get("timestamp", ""),
        )
