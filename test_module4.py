"""
Module 4 Verification & Test Suite
Tests E-Challan Generation, Fine Collection, Pandas Analytics, CSV Export, and Printable Receipts.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.database.db_manager import DatabaseManager
from traffic_violation_system.database.seed_data import seed_database
from traffic_violation_system.detection.detector import ViolationDetector
from traffic_violation_system.models.camera import TrafficCamera, DetectedObject
from traffic_violation_system.processing.challan_service import ChallanService
from traffic_violation_system.processing.report_service import ReportService


def run_all_tests():
    print("=" * 70)
    print("TRAFFIC VIOLATION & ACCIDENT ALERT SYSTEM")
    print("MODULE 4: VIOLATION PROCESSING & REPORTS - VERIFICATION SUITE")
    print("=" * 70)

    db = DatabaseManager()
    seed_database(db)
    detector = ViolationDetector(db)
    challan_svc = ChallanService(db)
    report_svc = ReportService(db)

    # 1. Setup sample violation
    cam = TrafficCamera(
        camera_id="CAM-CHN-01",
        junction_name="Anna Salai Junction",
        latitude=13.0522,
        longitude=80.2503,
        speed_limit=50.0,
        signal_status="RED",
    )
    obj = DetectedObject(
        object_id="OBJ-MOD4-1",
        vehicle_number="TN-07-AB-1234",
        vehicle_type="Car",
        speed_kmh=64.0,
    )
    vios = detector.analyze_event(cam, obj)
    assert len(vios) >= 1, "Failed to create test violation"
    test_vio = vios[0]
    print(f"\n[STEP 1] Created Base Violation: {test_vio.violation_id} ({test_vio.violation_type})")

    # 2. Test E-Challan Generation
    print("\n[STEP 2] Testing Automated E-Challan Creation...")
    challan = challan_svc.generate_challan_from_violation(test_vio.violation_id, due_days=15)
    assert challan is not None
    assert challan["payment_status"] == "PENDING"
    assert challan["amount"] == test_vio.fine_amount
    print(f"  [OK] E-Challan Issued: {challan['challan_id']}")
    print(f"       Vehicle: {challan['vehicle_number']} | Amount: INR {challan['amount']} | Due: {challan['due_date']}")

    # Verify violation status updated
    updated_vio = detector.get_violation_by_id(test_vio.violation_id)
    assert updated_vio["status"] == "CHALLAN_ISSUED"
    print("  [OK] Violation status transitioned to 'CHALLAN_ISSUED'")

    # 3. Test Challan Retrieval with Driver Details
    print("\n[STEP 3] Testing Complete Challan Joined Query...")
    full_ch = challan_svc.get_challan_by_id(challan["challan_id"])
    assert full_ch["driver_name"] is not None
    print(f"  [OK] Joined Driver Name: {full_ch['driver_name']} | License: {full_ch['license_number']}")
    print(f"       Offense: {full_ch['violation_type']} | Location: {full_ch['location']}")

    # 4. Test Payment Settlement
    print("\n[STEP 4] Testing Challan Payment Reconciliation...")
    pay_success = challan_svc.mark_challan_paid(challan["challan_id"], "UPI-TEST-998877")
    assert pay_success is True
    paid_ch = challan_svc.get_challan_by_id(challan["challan_id"])
    assert paid_ch["payment_status"] == "PAID"
    print(f"  [OK] Payment registered for {paid_ch['challan_id']}: Status={paid_ch['payment_status']}, Ref={paid_ch['payment_reference']}")

    # 5. Test Summary Statistics & Analytics
    print("\n[STEP 5] Testing Statistical Aggregation & Metrics...")
    stats = report_svc.get_summary_statistics()
    print(f"  [OK] Total Violations: {stats['total_violations']}")
    print(f"  [OK] Total Fines Imposed: INR {stats['total_fines_imposed']:,.0f}")
    print(f"  [OK] Paid Challans: {stats['paid_challans']} | Pending: {stats['pending_challans']}")
    print(f"  [OK] Revenue Collected: INR {stats['revenue_collected']:,.0f}")
    print(f"  [OK] Breakdown categories: {len(stats['violation_type_breakdown'])} violation types identified")

    # 6. Test CSV Export
    print("\n[STEP 6] Testing Data Export to CSV...")
    vio_csv = report_svc.export_violations_csv()
    ch_csv = report_svc.export_challans_csv()
    assert os.path.exists(vio_csv)
    assert os.path.exists(ch_csv)
    print(f"  [OK] Violations exported to: {vio_csv}")
    print(f"  [OK] E-Challans exported to: {ch_csv}")

    # 7. Test Printable E-Challan Receipt Generation
    print("\n[STEP 7] Testing Printable Official Receipt Generation...")
    receipt_path = report_svc.generate_printable_receipt(challan["challan_id"])
    assert os.path.exists(receipt_path)
    print(f"  [OK] Printable receipt generated at: {receipt_path}")

    print("\n" + "=" * 70)
    print("MODULE 4 (VIOLATION PROCESSING & REPORTS) VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
