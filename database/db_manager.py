"""
Database Manager - SQLite Storage and CRUD Operations
"""
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..config import DB_PATH
from ..models.driver import Driver
from ..models.vehicle import Vehicle
from ..models.camera import TrafficCamera
from ..models.telemetry import GPSData, SensorData


class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._local = threading.local()
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection with dictionary row access."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), timeout=20.0)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA foreign_keys = ON")
        return self._local.conn

    def init_database(self) -> None:
        """Create all required tables if they don't exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # 1. Users Table (for Module 2 Authentication & RBAC)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            # 2. Drivers Table (Module 1 Inputs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drivers (
                    driver_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    license_number TEXT UNIQUE NOT NULL,
                    license_category TEXT DEFAULT 'LMV',
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # 3. Vehicles Table (Module 1 Inputs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicles (
                    vehicle_number TEXT PRIMARY KEY,
                    vehicle_type TEXT NOT NULL,
                    driver_id TEXT NOT NULL,
                    make_model TEXT,
                    color TEXT,
                    registration_date TEXT,
                    FOREIGN KEY (driver_id) REFERENCES drivers (driver_id) ON DELETE CASCADE
                )
            """)

            # 4. Traffic Cameras Table (Module 1 Inputs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    camera_id TEXT PRIMARY KEY,
                    junction_name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed_limit REAL DEFAULT 50.0,
                    signal_status TEXT DEFAULT 'GREEN',
                    is_active INTEGER DEFAULT 1,
                    zone_type TEXT DEFAULT 'Standard'
                )
            """)

            # 5. GPS Telemetry Logs (Module 1 Inputs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gps_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_number TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed_kmh REAL DEFAULT 0.0,
                    heading_deg REAL DEFAULT 0.0,
                    altitude_m REAL DEFAULT 0.0,
                    location_name TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (vehicle_number) REFERENCES vehicles (vehicle_number)
                )
            """)

            # 6. Accident & Telemetry Sensor Logs (Module 1 Inputs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_number TEXT NOT NULL,
                    accel_x_g REAL DEFAULT 0.0,
                    accel_y_g REAL DEFAULT 0.0,
                    accel_z_g REAL DEFAULT 1.0,
                    total_g_force REAL DEFAULT 1.0,
                    tilt_pitch_deg REAL DEFAULT 0.0,
                    tilt_roll_deg REAL DEFAULT 0.0,
                    airbag_deployed INTEGER DEFAULT 0,
                    seatbelt_buckled INTEGER DEFAULT 1,
                    helmet_worn INTEGER,
                    engine_running INTEGER DEFAULT 1,
                    impact_severity TEXT NOT NULL,
                    vehicle_status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (vehicle_number) REFERENCES vehicles (vehicle_number)
                )
            """)

            # 7. Violations Table (Ready for Module 3 & 4)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    violation_id TEXT PRIMARY KEY,
                    vehicle_number TEXT NOT NULL,
                    driver_id TEXT,
                    violation_type TEXT NOT NULL,
                    fine_amount REAL NOT NULL,
                    camera_id TEXT,
                    location TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    speed_detected REAL,
                    speed_limit REAL,
                    timestamp TEXT NOT NULL,
                    evidence_image TEXT,
                    status TEXT DEFAULT 'RECORDED',
                    FOREIGN KEY (vehicle_number) REFERENCES vehicles (vehicle_number)
                )
            """)

            # 8. E-Challans Table (Ready for Module 4)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challans (
                    challan_id TEXT PRIMARY KEY,
                    violation_id TEXT UNIQUE NOT NULL,
                    vehicle_number TEXT NOT NULL,
                    driver_id TEXT,
                    amount REAL NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    payment_status TEXT DEFAULT 'PENDING',
                    payment_date TEXT,
                    payment_reference TEXT,
                    FOREIGN KEY (violation_id) REFERENCES violations (violation_id)
                )
            """)

            conn.commit()

    # --- DRIVER OPERATIONS ---
    def insert_driver(self, driver: Driver) -> bool:
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO drivers (driver_id, name, license_number, license_category, phone, email, address, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        driver.driver_id,
                        driver.name,
                        driver.license_number,
                        driver.license_category,
                        driver.phone,
                        driver.email,
                        driver.address,
                        driver.created_at,
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_driver(self, driver_id: str) -> Optional[Driver]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM drivers WHERE driver_id = ?", (driver_id.upper(),))
        row = cur.fetchone()
        return Driver.from_dict(dict(row)) if row else None

    def get_driver_by_license(self, license_number: str) -> Optional[Driver]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM drivers WHERE license_number = ?", (license_number.upper(),))
        row = cur.fetchone()
        return Driver.from_dict(dict(row)) if row else None

    def get_all_drivers(self) -> List[Driver]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM drivers ORDER BY name ASC")
        return [Driver.from_dict(dict(row)) for row in cur.fetchall()]

    # --- VEHICLE OPERATIONS ---
    def insert_vehicle(self, vehicle: Vehicle) -> bool:
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO vehicles (vehicle_number, vehicle_type, driver_id, make_model, color, registration_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vehicle.vehicle_number,
                        vehicle.vehicle_type,
                        vehicle.driver_id,
                        vehicle.make_model,
                        vehicle.color,
                        vehicle.registration_date,
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_vehicle(self, vehicle_number: str) -> Optional[Vehicle]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM vehicles WHERE vehicle_number = ?", (vehicle_number.upper(),))
        row = cur.fetchone()
        return Vehicle.from_dict(dict(row)) if row else None

    def get_vehicle_with_driver(self, vehicle_number: str) -> Optional[Dict[str, Any]]:
        """Join vehicle with registered driver details."""
        conn = self.get_connection()
        cur = conn.execute(
            """
            SELECT v.*, d.name AS driver_name, d.license_number, d.phone AS driver_phone, d.email AS driver_email
            FROM vehicles v
            LEFT JOIN drivers d ON v.driver_id = d.driver_id
            WHERE v.vehicle_number = ?
            """,
            (vehicle_number.upper(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_vehicles(self) -> List[Vehicle]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM vehicles ORDER BY vehicle_number ASC")
        return [Vehicle.from_dict(dict(row)) for row in cur.fetchall()]

    # --- CAMERA OPERATIONS ---
    def insert_camera(self, camera: TrafficCamera) -> bool:
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO cameras (camera_id, junction_name, latitude, longitude, speed_limit, signal_status, is_active, zone_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        camera.camera_id,
                        camera.junction_name,
                        camera.latitude,
                        camera.longitude,
                        camera.speed_limit,
                        camera.signal_status,
                        1 if camera.is_active else 0,
                        camera.zone_type,
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def update_camera_signal(self, camera_id: str, new_status: str) -> bool:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                "UPDATE cameras SET signal_status = ? WHERE camera_id = ?",
                (new_status.upper(), camera_id.upper()),
            )
            return cur.rowcount > 0

    def get_camera(self, camera_id: str) -> Optional[TrafficCamera]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM cameras WHERE camera_id = ?", (camera_id.upper(),))
        row = cur.fetchone()
        return TrafficCamera.from_dict(dict(row)) if row else None

    def get_all_cameras(self) -> List[TrafficCamera]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM cameras ORDER BY camera_id ASC")
        return [TrafficCamera.from_dict(dict(row)) for row in cur.fetchall()]

    # --- GPS & SENSOR TELEMETRY LOGS ---
    def insert_gps_data(self, gps: GPSData) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO gps_logs (vehicle_number, latitude, longitude, speed_kmh, heading_deg, altitude_m, location_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gps.vehicle_number,
                    gps.latitude,
                    gps.longitude,
                    gps.speed_kmh,
                    gps.heading_deg,
                    gps.altitude_m,
                    gps.location_name,
                    gps.timestamp,
                ),
            )
            return cur.lastrowid

    def insert_sensor_data(self, sensor: SensorData) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO sensor_logs (
                    vehicle_number, accel_x_g, accel_y_g, accel_z_g, total_g_force,
                    tilt_pitch_deg, tilt_roll_deg, airbag_deployed, seatbelt_buckled,
                    helmet_worn, engine_running, impact_severity, vehicle_status, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sensor.vehicle_number,
                    sensor.accel_x_g,
                    sensor.accel_y_g,
                    sensor.accel_z_g,
                    sensor.total_g_force,
                    sensor.tilt_pitch_deg,
                    sensor.tilt_roll_deg,
                    1 if sensor.airbag_deployed else 0,
                    1 if sensor.seatbelt_buckled else 0,
                    1 if sensor.helmet_worn else (0 if sensor.helmet_worn is False else None),
                    1 if sensor.engine_running else 0,
                    sensor.impact_severity.value,
                    sensor.vehicle_status.value,
                    sensor.timestamp,
                ),
            )
            return cur.lastrowid

    def get_recent_gps_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM gps_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

    def get_recent_sensor_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cur = conn.execute("SELECT * FROM sensor_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

    def get_accident_sensor_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Filter sensor events where severe impact, airbag, or rollover occurred."""
        conn = self.get_connection()
        cur = conn.execute(
            """
            SELECT s.*, v.vehicle_type, d.name AS driver_name, d.phone AS emergency_phone
            FROM sensor_logs s
            LEFT JOIN vehicles v ON s.vehicle_number = v.vehicle_number
            LEFT JOIN drivers d ON v.driver_id = d.driver_id
            WHERE s.impact_severity IN ('POTENTIAL_COLLISION', 'CRITICAL_ACCIDENT')
               OR s.airbag_deployed = 1
               OR s.vehicle_status IN ('CRASHED', 'TILTED')
            ORDER BY s.id DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]
