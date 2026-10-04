"""
CSV & JSON Ingestion Utility for Bulk Data Collection (Module 1)
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Union
from .data_collector import DataCollector
from ..models.driver import Driver
from ..models.vehicle import Vehicle
from ..models.camera import TrafficCamera


class CSVDataLoader:
    """Provides methods to bulk load data from CSV and JSON into the system."""

    def __init__(self, collector: DataCollector):
        self.collector = collector

    def load_drivers_from_csv(self, file_path: Union[str, Path]) -> int:
        """Load and register drivers from a CSV file."""
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                driver = Driver(
                    driver_id=row["driver_id"],
                    name=row["name"],
                    license_number=row["license_number"],
                    license_category=row.get("license_category", "LMV"),
                    phone=row.get("phone", ""),
                    email=row.get("email", ""),
                    address=row.get("address", ""),
                )
                self.collector.collect_driver(driver)
                count += 1
        return count

    def load_vehicles_from_csv(self, file_path: Union[str, Path]) -> int:
        """Load and register vehicles from a CSV file."""
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vehicle = Vehicle(
                    vehicle_number=row["vehicle_number"],
                    vehicle_type=row["vehicle_type"],
                    driver_id=row["driver_id"],
                    make_model=row.get("make_model", ""),
                    color=row.get("color", ""),
                    registration_date=row.get("registration_date", ""),
                )
                self.collector.collect_vehicle(vehicle)
                count += 1
        return count

    def load_cameras_from_json(self, file_path: Union[str, Path]) -> int:
        """Load traffic camera junctions from JSON file."""
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
            for item in items:
                cam = TrafficCamera.from_dict(item)
                self.collector.collect_camera(cam)
                count += 1
        return count
