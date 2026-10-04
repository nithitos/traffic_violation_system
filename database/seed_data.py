"""
Seed Database with Initial Realistic Data for Module 1
"""
import hashlib
import os
from .db_manager import DatabaseManager
from ..models.driver import Driver
from ..models.vehicle import Vehicle
from ..models.camera import TrafficCamera


def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return hashed, salt


def seed_database(db: DatabaseManager) -> None:
    """Populate database with sample Drivers, Vehicles, Cameras, and System Roles."""
    conn = db.get_connection()

    # 1. Seed Default Users (for RBAC authentication in Module 2)
    sample_users = [
        ("admin", "admin123", "ADMIN", "System Administrator", "admin@trafficops.gov"),
        ("officer1", "officer123", "TRAFFIC_OFFICER", "Officer Rajesh Kumar", "rajesh.kumar@trafficops.gov"),
        ("operator1", "operator123", "CONTROL_ROOM_OPERATOR", "Operator Priya Sharma", "priya.sharma@trafficops.gov"),
    ]
    with conn:
        for username, pwd, role, full_name, email in sample_users:
            h, s = hash_password(pwd)
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (username, password_hash, salt, role, full_name, email, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
                    """,
                    (username, h, s, role, full_name, email),
                )
            except Exception:
                pass

    # 2. Seed Sample Drivers
    sample_drivers = [
        Driver(
            driver_id="DRV-1001",
            name="Anand Venkataraman",
            license_number="DL-0420110012345",
            license_category="LMV",
            phone="+919840123456",
            email="anand.v@example.com",
            address="42 Anna Salai, Chennai, TN",
        ),
        Driver(
            driver_id="DRV-1002",
            name="Kavita Krishnan",
            license_number="TN-0720150098765",
            license_category="MCWG",
            phone="+919876543210",
            email="kavita.k@example.com",
            address="15 Gandhi Road, Adyar, Chennai, TN",
        ),
        Driver(
            driver_id="DRV-1003",
            name="Mohammed Imran",
            license_number="KA-0120180054321",
            license_category="LMV",
            phone="+919741234567",
            email="imran.m@example.com",
            address="88 Brigade Road, Bangalore, KA",
        ),
        Driver(
            driver_id="DRV-1004",
            name="Suresh Patel",
            license_number="GJ-0120160087654",
            license_category="HMV",
            phone="+919825123456",
            email="suresh.p@logistics.in",
            address="104 Transport Nagar, Ahmedabad, GJ",
        ),
        Driver(
            driver_id="DRV-1005",
            name="Deepa Murthy",
            license_number="TN-0920190011223",
            license_category="LMV",
            phone="+919940567890",
            email="deepa.m@example.com",
            address="12 Besant Nagar, Chennai, TN",
        ),
    ]
    for d in sample_drivers:
        db.insert_driver(d)

    # 3. Seed Sample Vehicles
    sample_vehicles = [
        Vehicle(
            vehicle_number="TN-07-AB-1234",
            vehicle_type="Car",
            driver_id="DRV-1001",
            make_model="Hyundai Creta",
            color="Polar White",
            registration_date="2022-03-15",
        ),
        Vehicle(
            vehicle_number="TN-09-CD-5678",
            vehicle_type="Motorcycle",
            driver_id="DRV-1002",
            make_model="Royal Enfield Classic 350",
            color="Stealth Black",
            registration_date="2021-08-10",
        ),
        Vehicle(
            vehicle_number="KA-01-EF-9012",
            vehicle_type="Car",
            driver_id="DRV-1003",
            make_model="Tata Nexon EV",
            color="Intense Teal",
            registration_date="2023-01-20",
        ),
        Vehicle(
            vehicle_number="GJ-01-GH-3456",
            vehicle_type="Truck",
            driver_id="DRV-1004",
            make_model="Tata Prima 4028",
            color="Yellow & Blue",
            registration_date="2020-05-12",
        ),
        Vehicle(
            vehicle_number="TN-22-JK-7890",
            vehicle_type="Auto Rickshaw",
            driver_id="DRV-1005",
            make_model="Bajaj Compact 4S",
            color="Yellow & Green",
            registration_date="2022-11-04",
        ),
        Vehicle(
            vehicle_number="TN-07-ZZ-9999",
            vehicle_type="Car",
            driver_id="DRV-1001",
            make_model="Maruti Suzuki Swift",
            color="Fire Red",
            registration_date="2023-06-18",
        ),
    ]
    for v in sample_vehicles:
        db.insert_vehicle(v)

    # 4. Seed Sample Traffic Cameras & Junctions
    sample_cameras = [
        TrafficCamera(
            camera_id="CAM-CHN-01",
            junction_name="Anna Salai - Gemini Flyover Junction",
            latitude=13.0522,
            longitude=80.2503,
            speed_limit=50.0,
            signal_status="GREEN",
            zone_type="Standard",
        ),
        TrafficCamera(
            camera_id="CAM-CHN-02",
            junction_name="Guindy Kathipara Junction",
            latitude=13.0067,
            longitude=80.2025,
            speed_limit=60.0,
            signal_status="RED",
            zone_type="Highway",
        ),
        TrafficCamera(
            camera_id="CAM-CHN-03",
            junction_name="Adyar Signal - LB Road Crossing",
            latitude=13.0033,
            longitude=80.2550,
            speed_limit=40.0,
            signal_status="GREEN",
            zone_type="School Zone",
        ),
        TrafficCamera(
            camera_id="CAM-CHN-04",
            junction_name="OMR Sholinganallur Intersection",
            latitude=12.9010,
            longitude=80.2279,
            speed_limit=70.0,
            signal_status="YELLOW",
            zone_type="Highway",
        ),
        TrafficCamera(
            camera_id="CAM-CHN-05",
            junction_name="T. Nagar Panagal Park Commercial Zone",
            latitude=13.0405,
            longitude=80.2337,
            speed_limit=30.0,
            signal_status="RED",
            zone_type="No Parking",
        ),
    ]
    for c in sample_cameras:
        db.insert_camera(c)
