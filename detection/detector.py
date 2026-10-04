"""
Traffic Monitoring & Violation Detection Engine (Module 3)
Detects Red Signal Violation, Speed Violation, Wrong Side Driving,
No Helmet / Seatbelt, and Illegal Parking.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..config import FINE_RATES, SIGNAL_RED
from ..database.db_manager import DatabaseManager
from ..models.camera import TrafficCamera, DetectedObject
from .violation_types import ViolationType, ViolationEvent
from .evidence_maker import EvidenceMaker
from .functional_ops import calculate_speed_overshoot, calculate_fine_multiplier


class ViolationDetector:
    """Core rule engine to detect traffic violations and record evidence."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def analyze_event(
        self,
        camera: TrafficCamera,
        detected_object: DetectedObject,
        timestamp: Optional[str] = None,
    ) -> List[ViolationEvent]:
        """
        Evaluate a detected vehicle against all 5 traffic violation rules.
        Returns a list of all detected ViolationEvent instances.
        """
        time_str = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        violations: List[ViolationEvent] = []

        # Lookup vehicle & driver details from Database (Vehicle Identification)
        plate = (detected_object.vehicle_number or "UNREGISTERED").upper()
        veh_info = self.db.get_vehicle_with_driver(plate)
        driver_id = veh_info["driver_id"] if veh_info else None
        driver_name = veh_info["driver_name"] if veh_info else "Unregistered Owner"
        vehicle_type = veh_info["vehicle_type"] if veh_info else detected_object.vehicle_type

        # -------------------------------------------------------------
        # Rule 1: Red Signal Violation
        # -------------------------------------------------------------
        if camera.signal_status == SIGNAL_RED and detected_object.speed_kmh > 5.0 and not detected_object.is_parked:
            vio = self._create_violation(
                violation_type=ViolationType.RED_SIGNAL,
                plate=plate,
                driver_id=driver_id,
                driver_name=driver_name,
                vehicle_type=vehicle_type,
                camera=camera,
                speed=detected_object.speed_kmh,
                time_str=time_str,
                base_fine=FINE_RATES.get("RED_SIGNAL", 1000),
            )
            violations.append(vio)

        # -------------------------------------------------------------
        # Rule 2: Speed Violation
        # -------------------------------------------------------------
        if detected_object.speed_kmh > camera.speed_limit:
            excess = calculate_speed_overshoot(detected_object.speed_kmh, camera.speed_limit)
            multiplier = calculate_fine_multiplier(excess)
            fine = FINE_RATES.get("OVER_SPEEDING", 2000) * multiplier
            vio = self._create_violation(
                violation_type=ViolationType.OVER_SPEEDING,
                plate=plate,
                driver_id=driver_id,
                driver_name=driver_name,
                vehicle_type=vehicle_type,
                camera=camera,
                speed=detected_object.speed_kmh,
                time_str=time_str,
                base_fine=fine,
            )
            violations.append(vio)

        # -------------------------------------------------------------
        # Rule 3: Wrong Side Driving
        # -------------------------------------------------------------
        if detected_object.is_wrong_way:
            vio = self._create_violation(
                violation_type=ViolationType.WRONG_SIDE,
                plate=plate,
                driver_id=driver_id,
                driver_name=driver_name,
                vehicle_type=vehicle_type,
                camera=camera,
                speed=detected_object.speed_kmh,
                time_str=time_str,
                base_fine=FINE_RATES.get("WRONG_SIDE", 1500),
            )
            violations.append(vio)

        # -------------------------------------------------------------
        # Rule 4: No Helmet / No Seatbelt
        # -------------------------------------------------------------
        is_two_wheeler = vehicle_type.lower() in ["motorcycle", "bike", "scooter"]
        if is_two_wheeler and detected_object.has_helmet is False:
            vio = self._create_violation(
                violation_type=ViolationType.NO_HELMET,
                plate=plate,
                driver_id=driver_id,
                driver_name=driver_name,
                vehicle_type=vehicle_type,
                camera=camera,
                speed=detected_object.speed_kmh,
                time_str=time_str,
                base_fine=FINE_RATES.get("NO_HELMET", 1000),
            )
            violations.append(vio)
        elif not is_two_wheeler and detected_object.seatbelt_fastened is False:
            vio = self._create_violation(
                violation_type=ViolationType.NO_SEATBELT,
                plate=plate,
                driver_id=driver_id,
                driver_name=driver_name,
                vehicle_type=vehicle_type,
                camera=camera,
                speed=detected_object.speed_kmh,
                time_str=time_str,
                base_fine=FINE_RATES.get("NO_SEATBELT", 1000),
            )
            violations.append(vio)

        # -------------------------------------------------------------
        # Rule 5: Illegal Parking
        # -------------------------------------------------------------
        if detected_object.is_parked and (camera.zone_type == "No Parking" or detected_object.parked_duration_sec > 60.0):
            vio = self._create_violation(
                violation_type=ViolationType.ILLEGAL_PARKING,
                plate=plate,
                driver_id=driver_id,
                driver_name=driver_name,
                vehicle_type=vehicle_type,
                camera=camera,
                speed=0.0,
                time_str=time_str,
                base_fine=FINE_RATES.get("ILLEGAL_PARKING", 500),
            )
            violations.append(vio)

        return violations

    def _create_violation(
        self,
        violation_type: ViolationType,
        plate: str,
        driver_id: Optional[str],
        driver_name: Optional[str],
        vehicle_type: str,
        camera: TrafficCamera,
        speed: float,
        time_str: str,
        base_fine: float,
    ) -> ViolationEvent:
        """Create and persist a ViolationEvent with evidence image."""
        unique_id = f"VIO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Generate Evidence Snapshot Image
        evidence_path = EvidenceMaker.generate_evidence_snapshot(
            violation_id=unique_id,
            violation_type=violation_type.display_name,
            vehicle_number=plate,
            vehicle_type=vehicle_type,
            speed=speed,
            speed_limit=camera.speed_limit,
            location=camera.junction_name,
            camera_id=camera.camera_id,
            signal_status=camera.signal_status,
            timestamp_str=time_str,
        )

        event = ViolationEvent(
            violation_id=unique_id,
            vehicle_number=plate,
            driver_id=driver_id,
            driver_name=driver_name,
            violation_type=violation_type.value,
            fine_amount=base_fine,
            camera_id=camera.camera_id,
            location=camera.junction_name,
            latitude=camera.latitude,
            longitude=camera.longitude,
            speed_detected=speed,
            speed_limit=camera.speed_limit,
            timestamp=time_str,
            evidence_image_path=evidence_path,
            status="RECORDED",
        )

        # Persist to Database
        conn = self.db.get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO violations (
                    violation_id, vehicle_number, driver_id, violation_type, fine_amount,
                    camera_id, location, latitude, longitude, speed_detected, speed_limit,
                    timestamp, evidence_image, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.violation_id,
                    event.vehicle_number,
                    event.driver_id,
                    event.violation_type,
                    event.fine_amount,
                    event.camera_id,
                    event.location,
                    event.latitude,
                    event.longitude,
                    event.speed_detected,
                    event.speed_limit,
                    event.timestamp,
                    event.evidence_image_path,
                    event.status,
                ),
            )

        return event

    def get_recent_violations(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cur = conn.execute("SELECT * FROM violations ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]

    def get_violation_by_id(self, violation_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        cur = conn.execute("SELECT * FROM violations WHERE violation_id = ?", (violation_id,))
        row = cur.fetchone()
        return dict(row) if row else None
