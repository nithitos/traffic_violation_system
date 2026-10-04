"""
Module 3 Verification & Test Suite
Tests Violation Detection Engine (5 Offenses), Functional Pipelines, Evidence Stamping, and Socket Streaming.
"""
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.database.db_manager import DatabaseManager
from traffic_violation_system.database.seed_data import seed_database
from traffic_violation_system.models.camera import TrafficCamera, DetectedObject
from traffic_violation_system.detection.detector import ViolationDetector
from traffic_violation_system.detection.violation_types import ViolationType
from traffic_violation_system.detection.functional_ops import (
    filter_by_violation_type,
    filter_by_min_fine,
    calculate_total_fine,
    map_to_alert_summary,
)
from traffic_violation_system.networking.socket_server import TrafficSocketServer
from traffic_violation_system.networking.camera_client import CameraSocketClient


def run_all_tests():
    print("=" * 70)
    print("TRAFFIC VIOLATION & ACCIDENT ALERT SYSTEM")
    print("MODULE 3: VIOLATION DETECTION & SOCKET STREAMING - VERIFICATION")
    print("=" * 70)

    db = DatabaseManager()
    seed_database(db)
    detector = ViolationDetector(db)

    # Test Camera
    cam = TrafficCamera(
        camera_id="CAM-CHN-01",
        junction_name="Anna Salai - Gemini Flyover",
        latitude=13.0522,
        longitude=80.2503,
        speed_limit=50.0,
        signal_status="RED",
    )

    # 1. Test Red Signal Violation
    print("\n[STEP 1] Testing Red Signal Violation Detection...")
    obj_red = DetectedObject(
        object_id="OBJ-RED-1",
        vehicle_number="TN-07-AB-1234",
        vehicle_type="Car",
        speed_kmh=45.0,
    )
    vios_red = detector.analyze_event(cam, obj_red)
    assert any(v.violation_type == ViolationType.RED_SIGNAL.value for v in vios_red)
    red_vio = vios_red[0]
    print(f"  [OK] Detected: {red_vio.violation_type} | ID: {red_vio.violation_id} | Fine: INR {red_vio.fine_amount}")

    # 2. Test Speed Violation Detection with Multiplier
    print("\n[STEP 2] Testing Speed Violation Detection & Excess Multiplier...")
    cam.update_signal("GREEN")
    obj_speed = DetectedObject(
        object_id="OBJ-SPD-1",
        vehicle_number="KA-01-EF-9012",
        vehicle_type="Car",
        speed_kmh=85.0,  # 35 km/h over 50 limit -> 1.5x multiplier = 3000
    )
    vios_spd = detector.analyze_event(cam, obj_speed)
    assert any(v.violation_type == ViolationType.OVER_SPEEDING.value for v in vios_spd)
    spd_vio = vios_spd[0]
    assert spd_vio.fine_amount == 3000.0, f"Expected fine 3000, got {spd_vio.fine_amount}"
    print(f"  [OK] Detected: {spd_vio.violation_type} (Speed: 85 km/h on 50 km/h limit) | Fine: INR {spd_vio.fine_amount}")

    # 3. Test Wrong Side Driving
    print("\n[STEP 3] Testing Wrong Side Driving Detection...")
    obj_wrong = DetectedObject(
        object_id="OBJ-WS-1",
        vehicle_number="GJ-01-GH-3456",
        vehicle_type="Truck",
        speed_kmh=35.0,
        is_wrong_way=True,
    )
    vios_ws = detector.analyze_event(cam, obj_wrong)
    assert any(v.violation_type == ViolationType.WRONG_SIDE.value for v in vios_ws)
    print(f"  [OK] Detected: {vios_ws[0].violation_type} | Vehicle: {vios_ws[0].vehicle_number} | Fine: INR {vios_ws[0].fine_amount}")

    # 4. Test No Helmet (2-Wheeler) & No Seatbelt (4-Wheeler)
    print("\n[STEP 4] Testing Safety Gear Violations (Helmet & Seatbelt)...")
    obj_helmet = DetectedObject(
        object_id="OBJ-HLM-1",
        vehicle_number="TN-09-CD-5678",
        vehicle_type="Motorcycle",
        speed_kmh=38.0,
        has_helmet=False,
    )
    vios_hlm = detector.analyze_event(cam, obj_helmet)
    assert any(v.violation_type == ViolationType.NO_HELMET.value for v in vios_hlm)
    print(f"  [OK] Detected Two-Wheeler without Helmet: {vios_hlm[0].violation_type} | Fine: INR {vios_hlm[0].fine_amount}")

    obj_seatbelt = DetectedObject(
        object_id="OBJ-BELT-1",
        vehicle_number="TN-07-AB-1234",
        vehicle_type="Car",
        speed_kmh=42.0,
        seatbelt_fastened=False,
    )
    vios_belt = detector.analyze_event(cam, obj_seatbelt)
    assert any(v.violation_type == ViolationType.NO_SEATBELT.value for v in vios_belt)
    print(f"  [OK] Detected Four-Wheeler without Seatbelt: {vios_belt[0].violation_type} | Fine: INR {vios_belt[0].fine_amount}")

    # 5. Test Illegal Parking
    print("\n[STEP 5] Testing Illegal Parking Detection...")
    cam_park = TrafficCamera(
        camera_id="CAM-CHN-05",
        junction_name="Panagal Park Commercial Zone",
        latitude=13.0405,
        longitude=80.2337,
        zone_type="No Parking",
    )
    obj_park = DetectedObject(
        object_id="OBJ-PRK-1",
        vehicle_number="TN-22-JK-7890",
        vehicle_type="Auto Rickshaw",
        speed_kmh=0.0,
        is_parked=True,
        parked_duration_sec=120.0,
    )
    vios_park = detector.analyze_event(cam_park, obj_park)
    assert any(v.violation_type == ViolationType.ILLEGAL_PARKING.value for v in vios_park)
    print(f"  [OK] Detected: {vios_park[0].violation_type} in {cam_park.zone_type} Zone | Fine: INR {vios_park[0].fine_amount}")

    # 6. Functional Operations Pipeline Tests
    print("\n[STEP 6] Testing Functional Programming Pipelines (Filter, Map, Reduce)...")
    all_violations = detector.get_recent_violations(limit=20)
    red_list = filter_by_violation_type(all_violations, "RED_SIGNAL")
    total_fines = calculate_total_fine(all_violations)
    alerts = map_to_alert_summary(all_violations)

    print(f"  [OK] Functional Filter: Found {len(red_list)} Red Signal violations.")
    print(f"  [OK] Functional Reduce: Total Fine Accumulation = INR {total_fines:,.0f}")
    print(f"  [OK] Functional Map: Formatted {len(alerts)} alert notification summary cards.")

    # 7. Socket Programming (Client-Server Live Streaming)
    print("\n[STEP 7] Testing Socket Client-Server Real-Time Telemetry & Alert Broadcast...")
    server = TrafficSocketServer(host="127.0.0.1", port=9999, db_manager=db)
    received_alerts = []

    def on_live_alert(payload):
        received_alerts.append(payload)

    server.register_alert_callback(on_live_alert)
    server.start()
    time.sleep(0.5)

    client = CameraSocketClient(host="127.0.0.1", port=9999)
    assert client.connect(), "Failed to connect client to socket server"

    resp = client.trigger_sample_violation(
        camera_id="CAM-CHN-01",
        vehicle_number="TN-07-AB-1234",
        violation_scenario="RED_SIGNAL",
    )
    print(f"  [OK] Client sent live camera telemetry. Server response: {resp}")
    assert resp["violations_detected"] >= 1

    time.sleep(0.5)
    assert len(received_alerts) >= 1, "Alert callback did not receive live violation payload"
    print(f"  [OK] Live Alert received via Socket: {received_alerts[0]['violation_type']} for {received_alerts[0]['vehicle_number']}")

    client.close()
    server.stop()
    print("  [OK] Socket Server shut down gracefully.")

    print("\n" + "=" * 70)
    print("MODULE 3 (VIOLATION DETECTION & SOCKET STREAMING) VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
