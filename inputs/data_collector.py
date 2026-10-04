"""
Data Collector - Central Ingestion and Collection Engine for Module 1
Handles ingestion and validation for Drivers, Vehicles, Cameras, GPS, and Sensor telemetry.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from ..database.db_manager import DatabaseManager
from ..models.driver import Driver
from ..models.vehicle import Vehicle
from ..models.camera import TrafficCamera
from ..models.telemetry import GPSData, SensorData, ImpactSeverity, VehicleStatus


class DataCollector:
    """Unified collection service for all input data streams."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    # -------------------------------------------------------------
    # 1. DRIVER DATA COLLECTION
    # -------------------------------------------------------------
    def collect_driver(self, driver_input: Union[Driver, Dict[str, Any]]) -> Driver:
        """Collect, validate, and store driver details."""
        if isinstance(driver_input, dict):
            driver = Driver.from_dict(driver_input)
        elif isinstance(driver_input, Driver):
            driver = driver_input
        else:
            raise TypeError("Expected Driver instance or dictionary.")

        driver.validate()
        existing = self.db.get_driver(driver.driver_id)
        if existing:
            # Update existing driver
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE drivers 
                    SET name = ?, license_number = ?, license_category = ?, phone = ?, email = ?, address = ?
                    WHERE driver_id = ?
                    """,
                    (
                        driver.name,
                        driver.license_number,
                        driver.license_category,
                        driver.phone,
                        driver.email,
                        driver.address,
                        driver.driver_id,
                    ),
                )
        else:
            self.db.insert_driver(driver)
        return driver

    # -------------------------------------------------------------
    # 2. VEHICLE DATA COLLECTION
    # -------------------------------------------------------------
    def collect_vehicle(self, vehicle_input: Union[Vehicle, Dict[str, Any]]) -> Vehicle:
        """Collect, validate, and store vehicle details linked to driver."""
        if isinstance(vehicle_input, dict):
            vehicle = Vehicle.from_dict(vehicle_input)
        elif isinstance(vehicle_input, Vehicle):
            vehicle = vehicle_input
        else:
            raise TypeError("Expected Vehicle instance or dictionary.")

        vehicle.validate()
        # Verify driver exists
        driver = self.db.get_driver(vehicle.driver_id)
        if not driver:
            raise ValueError(f"Registered Driver ID '{vehicle.driver_id}' not found in database.")

        existing = self.db.get_vehicle(vehicle.vehicle_number)
        if existing:
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE vehicles
                    SET vehicle_type = ?, driver_id = ?, make_model = ?, color = ?
                    WHERE vehicle_number = ?
                    """,
                    (
                        vehicle.vehicle_type,
                        vehicle.driver_id,
                        vehicle.make_model,
                        vehicle.color,
                        vehicle.vehicle_number,
                    ),
                )
        else:
            self.db.insert_vehicle(vehicle)
        return vehicle

    # -------------------------------------------------------------
    # 3. TRAFFIC CAMERA & SIGNAL DATA COLLECTION
    # -------------------------------------------------------------
    def collect_camera(self, camera_input: Union[TrafficCamera, Dict[str, Any]]) -> TrafficCamera:
        """Register or update a traffic monitoring camera junction."""
        if isinstance(camera_input, dict):
            camera = TrafficCamera.from_dict(camera_input)
        elif isinstance(camera_input, TrafficCamera):
            camera = camera_input
        else:
            raise TypeError("Expected TrafficCamera instance or dictionary.")

        existing = self.db.get_camera(camera.camera_id)
        if existing:
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE cameras
                    SET junction_name = ?, latitude = ?, longitude = ?, speed_limit = ?, signal_status = ?, is_active = ?, zone_type = ?
                    WHERE camera_id = ?
                    """,
                    (
                        camera.junction_name,
                        camera.latitude,
                        camera.longitude,
                        camera.speed_limit,
                        camera.signal_status,
                        1 if camera.is_active else 0,
                        camera.zone_type,
                        camera.camera_id,
                    ),
                )
        else:
            self.db.insert_camera(camera)
        return camera

    def update_signal_status(self, camera_id: str, signal_status: str) -> bool:
        """Update live traffic signal light status for a specific camera junction."""
        return self.db.update_camera_signal(camera_id, signal_status)

    # -------------------------------------------------------------
    # 4. GPS TELEMETRY DATA COLLECTION
    # -------------------------------------------------------------
    def collect_gps(self, gps_input: Union[GPSData, Dict[str, Any]]) -> int:
        """Collect and store GPS coordinate packet."""
        if isinstance(gps_input, dict):
            gps = GPSData.from_dict(gps_input)
        elif isinstance(gps_input, GPSData):
            gps = gps_input
        else:
            raise TypeError("Expected GPSData instance or dictionary.")

        return self.db.insert_gps_data(gps)

    def batch_collect_gps(self, gps_list: List[Union[GPSData, Dict[str, Any]]]) -> int:
        """Bulk ingest GPS telemetry stream."""
        count = 0
        for item in gps_list:
            self.collect_gps(item)
            count += 1
        return count

    # -------------------------------------------------------------
    # 5. ACCIDENT SENSOR DATA COLLECTION
    # -------------------------------------------------------------
    def collect_sensor(self, sensor_input: Union[SensorData, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect accident sensor packet (G-Force, Tilt, Airbag, Seatbelt, Status).
        Returns the processed reading with calculated impact severity.
        """
        if isinstance(sensor_input, dict):
            sensor = SensorData.from_dict(sensor_input)
        elif isinstance(sensor_input, SensorData):
            sensor = sensor_input
        else:
            raise TypeError("Expected SensorData instance or dictionary.")

        log_id = self.db.insert_sensor_data(sensor)
        result = sensor.to_dict()
        result["log_id"] = log_id
        return result

    def batch_collect_sensors(self, sensor_list: List[Union[SensorData, Dict[str, Any]]]) -> int:
        """Bulk ingest sensor telemetry stream."""
        count = 0
        for item in sensor_list:
            self.collect_sensor(item)
            count += 1
        return count

    # -------------------------------------------------------------
    # QUERY & RETRIEVAL HELPERS
    # -------------------------------------------------------------
    def get_vehicle_summary(self, vehicle_number: str) -> Optional[Dict[str, Any]]:
        """Fetch combined vehicle, owner driver, and latest telemetry."""
        data = self.db.get_vehicle_with_driver(vehicle_number)
        if not data:
            return None

        # Fetch latest GPS
        conn = self.db.get_connection()
        cur = conn.execute(
            "SELECT * FROM gps_logs WHERE vehicle_number = ? ORDER BY id DESC LIMIT 1",
            (vehicle_number.upper(),),
        )
        latest_gps = cur.fetchone()

        # Fetch latest Sensor reading
        cur = conn.execute(
            "SELECT * FROM sensor_logs WHERE vehicle_number = ? ORDER BY id DESC LIMIT 1",
            (vehicle_number.upper(),),
        )
        latest_sensor = cur.fetchone()

        data["latest_gps"] = dict(latest_gps) if latest_gps else None
        data["latest_sensor"] = dict(latest_sensor) if latest_sensor else None
        return data

    def get_all_registered_vehicles(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            SELECT v.vehicle_number, v.vehicle_type, v.make_model, v.color, v.registration_date,
                   d.driver_id, d.name AS driver_name, d.phone AS driver_phone, d.license_number
            FROM vehicles v
            LEFT JOIN drivers d ON v.driver_id = d.driver_id
            ORDER BY v.vehicle_number ASC
            """
        )
        return [dict(r) for r in cur.fetchall()]

    def get_all_junction_cameras(self) -> List[TrafficCamera]:
        return self.db.get_all_cameras()
