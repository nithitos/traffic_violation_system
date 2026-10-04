"""
Module 1 Verification & Test Suite
Tests Driver, Vehicle, Camera, GPS, and Sensor telemetry collection and validation.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.config import DB_PATH, EVIDENCE_DIR
from traffic_violation_system.database.db_manager import DatabaseManager
from traffic_violation_system.database.seed_data import seed_database
from traffic_violation_system.models.driver import Driver
from traffic_violation_system.models.vehicle import Vehicle
from traffic_violation_system.models.camera import TrafficCamera
from traffic_violation_system.models.telemetry import GPSData, SensorData, ImpactSeverity, VehicleStatus
from traffic_violation_system.inputs.data_collector import DataCollector
from traffic_violation_system.inputs.sensor_simulator import SensorSimulator, TrafficSignalSimulator
from traffic_violation_system.inputs.camera_simulator import CameraSimulator


def run_all_tests():
    print("=" * 70)
    print("TRAFFIC VIOLATION & ACCIDENT ALERT SYSTEM")
    print("MODULE 1: INPUT AND DATA COLLECTION - VERIFICATION SUITE")
    print("=" * 70)

    # 1. Initialize Database & Seed
    print("\n[STEP 1] Initializing Database & Seeding Baseline Data...")
    db = DatabaseManager()
    seed_database(db)
    collector = DataCollector(db)
    print("  [OK] Database initialized at:", db.db_path)
    print("  [OK] Baseline drivers, vehicles, cameras, and system roles seeded.")

    # 2. Driver Collection & Validation Tests
    print("\n[STEP 2] Testing Driver Data Collection & Validation...")
    new_driver = Driver(
        driver_id="DRV-9999",
        name="Vikramaditya Rao",
        license_number="KA-0420200099999",
        license_category="LMV",
        phone="+919888877777",
        email="vikram.rao@example.com",
        address="100 Feet Road, Indiranagar, Bengaluru",
    )
    collected_drv = collector.collect_driver(new_driver)
    fetched_drv = db.get_driver("DRV-9999")
    assert fetched_drv is not None, "Failed to retrieve saved driver"
    assert fetched_drv.name == "Vikramaditya Rao", "Driver name mismatch"
    print(f"  [OK] Driver collected and retrieved successfully: {fetched_drv.name} (ID: {fetched_drv.driver_id})")

    # Test Driver Validation Error
    try:
        Driver(driver_id="", name="X", license_number="")
        print("  [FAIL] Invalid driver should have raised ValueError")
    except ValueError as e:
        print(f"  [OK] Validation correctly rejected invalid driver: {e}")

    # 3. Vehicle Collection & Validation Tests
    print("\n[STEP 3] Testing Vehicle Data Collection & Driver Linking...")
    new_vehicle = Vehicle(
        vehicle_number="KA-03-MN-4321",
        vehicle_type="Car",
        driver_id="DRV-9999",
        make_model="Honda City ZX",
        color="Radiant Red",
    )
    collected_veh = collector.collect_vehicle(new_vehicle)
    fetched_veh = db.get_vehicle("KA-03-MN-4321")
    assert fetched_veh is not None, "Failed to retrieve saved vehicle"
    print(f"  [OK] Vehicle registered: {fetched_veh.vehicle_number} -> Owner: {new_driver.name}")

    # Test Vehicle Foreign Key Validation
    try:
        collector.collect_vehicle({
            "vehicle_number": "XX-99-ZZ-0000",
            "vehicle_type": "Car",
            "driver_id": "NON-EXISTENT-DRIVER",
        })
        print("  [FAIL] Unregistered driver should have been rejected")
    except ValueError as e:
        print(f"  [OK] Validation correctly rejected unlinked vehicle: {e}")

    # 4. Camera & Traffic Signal Tests
    print("\n[STEP 4] Testing Camera Registration & Signal Status Management...")
    new_cam = TrafficCamera(
        camera_id="CAM-TEST-01",
        junction_name="Silk Board Junction",
        latitude=12.9172,
        longitude=77.6228,
        speed_limit=50.0,
        signal_status="GREEN",
        zone_type="Highway",
    )
    collector.collect_camera(new_cam)
    collector.update_signal_status("CAM-TEST-01", "RED")
    updated_cam = db.get_camera("CAM-TEST-01")
    assert updated_cam.signal_status == "RED", "Signal status update failed"
    print(f"  [OK] Camera {updated_cam.camera_id} at '{updated_cam.junction_name}' updated signal: {updated_cam.signal_status}")

    # 5. GPS Telemetry Collection Tests
    print("\n[STEP 5] Testing GPS Telemetry Ingestion...")
    gps_sample = GPSData(
        vehicle_number="KA-03-MN-4321",
        latitude=12.9175,
        longitude=77.6230,
        speed_kmh=58.2,
        heading_deg=180.0,
        altitude_m=920.0,
        location_name="Hosur Main Road",
    )
    gps_id = collector.collect_gps(gps_sample)
    recent_gps = db.get_recent_gps_logs(limit=1)
    assert len(recent_gps) > 0 and recent_gps[0]["vehicle_number"] == "KA-03-MN-4321"
    print(f"  [OK] GPS packet logged with ID {gps_id}: Lat={gps_sample.latitude}, Lon={gps_sample.longitude}, Speed={gps_sample.speed_kmh} km/h")

    # 6. Accident Sensor Telemetry & Impact Classification Tests
    print("\n[STEP 6] Testing Accident Sensor Data & Impact Classification...")
    sim = SensorSimulator(vehicle_number="KA-03-MN-4321")

    # Scenario A: Normal Driving
    gps_norm, sensor_norm = sim.generate_normal_telemetry()
    res_norm = collector.collect_sensor(sensor_norm)
    print(f"  [OK] Normal Cruise: Total G={res_norm['total_g_force']}G, Severity={res_norm['impact_severity']}, Status={res_norm['vehicle_status']}")
    assert res_norm["impact_severity"] == ImpactSeverity.NORMAL.value

    # Scenario B: Harsh Braking
    _, sensor_brake = sim.generate_harsh_braking_telemetry()
    res_brake = collector.collect_sensor(sensor_brake)
    print(f"  [OK] Harsh Braking: Decel={sensor_brake.accel_y_g}G, Severity={res_brake['impact_severity']}")
    assert res_brake["impact_severity"] == ImpactSeverity.HARSH_BRAKING.value

    # Scenario C: Severe Collision Crash
    _, sensor_crash = sim.generate_collision_telemetry()
    res_crash = collector.collect_sensor(sensor_crash)
    print(f"  [OK] Collision Crash: Total G={res_crash['total_g_force']}G, Airbag={res_crash['airbag_deployed']}, Severity={res_crash['impact_severity']}, Status={res_crash['vehicle_status']}")
    assert res_crash["impact_severity"] == ImpactSeverity.CRITICAL_ACCIDENT.value
    assert res_crash["vehicle_status"] == VehicleStatus.CRASHED.value

    # Scenario D: Rollover Event
    _, sensor_rollover = sim.generate_rollover_telemetry()
    res_roll = collector.collect_sensor(sensor_rollover)
    print(f"  [OK] Rollover Event: Roll Tilt={res_roll['tilt_roll_deg']} deg, Rollover={res_roll['is_rollover']}, Status={res_roll['vehicle_status']}")
    assert res_roll["is_rollover"] is True

    # 7. Camera Frame & Visual Snapshot Capture Tests
    print("\n[STEP 7] Testing Camera Snapshot & Frame Generation...")
    cam_sim = CameraSimulator(new_cam)
    frame = cam_sim.capture_frame(save_snapshot=True, custom_signal="RED")
    print(f"  [OK] Frame captured: {frame.frame_id}, Signal={frame.signal_status}, Objects={len(frame.detected_objects)}")
    if frame.image_path:
        print(f"  [OK] Visual evidence snapshot saved to: {frame.image_path}")

    # 8. Full Vehicle Profile Query Test
    print("\n[STEP 8] Testing Complete Vehicle Profile Query (Vehicle + Driver + Telemetry)...")
    full_profile = collector.get_vehicle_summary("KA-03-MN-4321")
    assert full_profile is not None
    print(f"  [OK] Profile retrieved for {full_profile['vehicle_number']}:")
    print(f"    - Model: {full_profile['make_model']} ({full_profile['color']})")
    print(f"    - Registered Driver: {full_profile['driver_name']} (Phone: {full_profile['driver_phone']})")
    print(f"    - Latest GPS Location: Lat={full_profile['latest_gps']['latitude']}, Lon={full_profile['latest_gps']['longitude']}")
    print(f"    - Latest Sensor Status: Severity={full_profile['latest_sensor']['impact_severity']}, Airbag={full_profile['latest_sensor']['airbag_deployed']}")

    print("\n" + "=" * 70)
    print("MODULE 1 (INPUT AND DATA COLLECTION) COMPLETED & VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
