"""
Data models for Traffic Violation & Accident Alert System
"""
from .driver import Driver
from .vehicle import Vehicle
from .camera import TrafficCamera, CameraFrame
from .telemetry import GPSData, SensorData, ImpactSeverity, VehicleStatus

__all__ = [
    "Driver",
    "Vehicle",
    "TrafficCamera",
    "CameraFrame",
    "GPSData",
    "SensorData",
    "ImpactSeverity",
    "VehicleStatus",
]
