"""
Web Server & REST API Automated Test
Verifies all web endpoints and simulator integration.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path
from threading import Thread

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.web.server import TrafficAPIHandler, ThreadingHTTPServer


def run_web_tests(port: int = 5055):
    print("=" * 70)
    print("TRAFFIC SYSTEM: WEB & REST API VERIFICATION SUITE")
    print("=" * 70)

    # 1. Start Server in daemon thread
    TrafficAPIHandler.initialize_services()
    server = ThreadingHTTPServer(("127.0.0.1", port), TrafficAPIHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)
    base_url = f"http://127.0.0.1:{port}"
    print(f"\n[STEP 1] Web Server started at {base_url}")

    # Helper
    def get_json(endpoint):
        req = urllib.request.urlopen(f"{base_url}{endpoint}")
        assert req.status == 200, f"Expected 200 from {endpoint}, got {req.status}"
        return json.loads(req.read().decode("utf-8"))

    def post_json(endpoint, payload):
        req = urllib.request.Request(
            f"{base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        assert resp.status == 200, f"Expected 200 from {endpoint}, got {resp.status}"
        return json.loads(resp.read().decode("utf-8"))

    # 2. Test GET /
    print("\n[STEP 2] Testing Dashboard HTML Root (GET /)...")
    html_resp = urllib.request.urlopen(f"{base_url}/")
    assert html_resp.status == 200
    html_text = html_resp.read().decode("utf-8")
    assert "<title>" in html_text
    print("  [OK] Dashboard HTML delivered successfully.")

    # 3. Test GET /api/status
    print("\n[STEP 3] Testing System Status (GET /api/status)...")
    status_data = get_json("/api/status")
    assert status_data["status"] == "ONLINE"
    assert len(status_data["cameras"]) > 0
    print(f"  [OK] Status Online, Signal: {status_data['current_signal']}, Active Cameras: {len(status_data['cameras'])}")

    # 4. Test POST /api/violations/trigger
    print("\n[STEP 4] Testing Simulated Violation Trigger (POST /api/violations/trigger)...")
    trig_resp = post_json("/api/violations/trigger", {
        "camera_id": "CAM-CHN-01",
        "scenario": "RED_SIGNAL",
    })
    assert trig_resp["violations_detected"] >= 1
    new_vio = trig_resp["violations"][0]
    print(f"  [OK] Triggered Violation: {new_vio['violation_id']} ({new_vio['violation_type']}) | Fine: INR {new_vio['fine_amount']}")

    # 5. Test POST /api/challans/generate
    print("\n[STEP 5] Testing E-Challan Issuance (POST /api/challans/generate)...")
    ch_resp = post_json("/api/challans/generate", {"violation_id": new_vio["violation_id"]})
    assert ch_resp["success"] is True
    print(f"  [OK] E-Challan Dispatched: {ch_resp['challan']['challan_id']} | Amount: INR {ch_resp['challan']['amount']}")

    # 6. Test GET /api/analytics
    print("\n[STEP 6] Testing Analytics API (GET /api/analytics)...")
    stats = get_json("/api/analytics")
    assert stats["total_violations"] > 0
    print(f"  [OK] Total Violations: {stats['total_violations']} | Fines: INR {stats['total_fines_imposed']:,.0f}")

    # 7. Test GET /api/vehicles
    print("\n[STEP 7] Testing Registered Vehicles (GET /api/vehicles)...")
    vehs = get_json("/api/vehicles")
    assert len(vehs) > 0
    print(f"  [OK] Retrieved {len(vehs)} registered vehicles with linked driver details.")

    # 8. Test Video AI Stream & ANPR Endpoints
    print("\n[STEP 8] Testing AI Video & ANPR Endpoints (GET /api/video/stats & POST /api/video/source)...")
    v_stats = get_json("/api/video/stats")
    assert "tracked_vehicles" in v_stats
    assert "model" in v_stats
    print(f"  [OK] Video AI Engine: {v_stats['model']} | Active Tracks: {v_stats['tracked_vehicles']}")

    src_resp = post_json("/api/video/source", {"source": "sample"})
    assert src_resp["success"] is True
    print(f"  [OK] Video Source Switcher verified: {src_resp['source']}")

    # 9. Shutdown test server
    server.shutdown()
    print("\n" + "=" * 70)
    print("WEB DASHBOARD, REST API & AI VIDEO STREAM VERIFIED 100% SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_web_tests(5055)
