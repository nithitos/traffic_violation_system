"""
Driver / User Data Model
"""
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Driver:
    driver_id: str
    name: str
    license_number: str
    license_category: str = "LMV"  # LMV (Light Motor Vehicle), MCWG (Motorcycle With Gear), HMV, etc.
    phone: str = ""
    email: str = ""
    address: str = ""
    created_at: str = ""

    def __post_init__(self):
        self.driver_id = self.driver_id.strip().upper()
        self.name = self.name.strip()
        self.license_number = self.license_number.strip().upper()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.validate()

    def validate(self) -> None:
        if not self.driver_id:
            raise ValueError("Driver ID cannot be empty.")
        if not self.name or len(self.name) < 2:
            raise ValueError("Driver Name must have at least 2 characters.")
        if not self.license_number or len(self.license_number) < 5:
            raise ValueError("Valid License Number is required.")
        if self.phone and not re.match(r"^\+?[0-9]{7,15}$", self.phone.replace(" ", "").replace("-", "")):
            raise ValueError(f"Invalid phone number format: {self.phone}")
        if self.email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", self.email):
            raise ValueError(f"Invalid email address format: {self.email}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Driver":
        return cls(
            driver_id=data["driver_id"],
            name=data["name"],
            license_number=data["license_number"],
            license_category=data.get("license_category", "LMV"),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            created_at=data.get("created_at", ""),
        )
