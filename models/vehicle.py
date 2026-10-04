"""
Vehicle Data Model
"""
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from ..config import VEHICLE_TYPES


@dataclass
class Vehicle:
    vehicle_number: str
    vehicle_type: str
    driver_id: str
    make_model: str = ""
    color: str = ""
    registration_date: str = ""

    def __post_init__(self):
        # Normalize vehicle plate (remove excess spaces and convert to uppercase)
        self.vehicle_number = re.sub(r"\s+", "", self.vehicle_number).upper()
        self.vehicle_type = self.vehicle_type.strip().title()
        self.driver_id = self.driver_id.strip().upper()
        if not self.registration_date:
            self.registration_date = datetime.now().strftime("%Y-%m-%d")
        self.validate()

    def validate(self) -> None:
        if not self.vehicle_number or len(self.vehicle_number) < 5:
            raise ValueError("Invalid vehicle number format.")
        matched_type = next((vt for vt in VEHICLE_TYPES if vt.lower() == self.vehicle_type.lower()), None)
        if not matched_type:
            raise ValueError(f"Vehicle type '{self.vehicle_type}' is invalid. Allowed: {', '.join(VEHICLE_TYPES)}")
        self.vehicle_type = matched_type
        if not self.driver_id:
            raise ValueError("Vehicle must be registered to a Driver ID.")

    def is_two_wheeler(self) -> bool:
        return self.vehicle_type.lower() in ["motorcycle", "bike", "scooter"]

    def is_heavy_vehicle(self) -> bool:
        return self.vehicle_type.lower() in ["truck", "bus"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vehicle":
        return cls(
            vehicle_number=data["vehicle_number"],
            vehicle_type=data["vehicle_type"],
            driver_id=data["driver_id"],
            make_model=data.get("make_model", ""),
            color=data.get("color", ""),
            registration_date=data.get("registration_date", ""),
        )
