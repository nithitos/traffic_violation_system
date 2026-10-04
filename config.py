"""
Traffic Violation & Accident Alert System - System Configuration
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EVIDENCE_DIR = BASE_DIR / "evidence"
REPORTS_DIR = BASE_DIR / "reports"
DB_PATH = DATA_DIR / "traffic_system.db"

# Ensure essential directories exist
for directory in [DATA_DIR, EVIDENCE_DIR, REPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Networking / Socket Configuration
SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 9999
BUFFER_SIZE = 4096

# Sensor & Telemetry Thresholds
SPEED_LIMIT_DEFAULT_KMH = 50.0
IMPACT_THRESHOLD_NORMAL_G = 1.2    # Normal driving vibration < 1.2G
IMPACT_THRESHOLD_WARNING_G = 2.5   # Harsh brake / minor bump > 2.5G
IMPACT_THRESHOLD_COLLISION_G = 5.0 # Serious collision > 5.0G
TILT_THRESHOLD_ROLLOVER_DEG = 45.0 # Vehicle tilt > 45 deg indicates rollover

# Traffic Signal States
SIGNAL_RED = "RED"
SIGNAL_YELLOW = "YELLOW"
SIGNAL_GREEN = "GREEN"

# Vehicle Categories
VEHICLE_TYPES = ["Car", "Motorcycle", "Truck", "Bus", "Auto Rickshaw"]

# Standard Fine Matrix (in INR)
FINE_RATES = {
    "RED_SIGNAL": 1000,
    "OVER_SPEEDING": 2000,
    "WRONG_SIDE": 1500,
    "NO_HELMET": 1000,
    "NO_SEATBELT": 1000,
    "ILLEGAL_PARKING": 500,
    "HARSH_DRIVING": 1500,
}
