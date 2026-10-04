"""
Web Dashboard Launcher
Starts the multi-threaded web server and opens the browser to http://127.0.0.1:5000
"""
import io
import sys
import time
import webbrowser
from pathlib import Path
from threading import Thread

# Force UTF-8 output on Windows to prevent UnicodeEncodeError with emoji/special chars
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.web.server import TrafficAPIHandler, ThreadingHTTPServer


def main(port: int = 5000):
    print("=" * 70)
    print("🚦 INTELLIGENT TRAFFIC VIOLATION & ACCIDENT ALERT SYSTEM")
    print("   Starting Local Web Server & Control Center...")
    print("=" * 70)

    TrafficAPIHandler.initialize_services()
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, TrafficAPIHandler)

    url = f"http://127.0.0.1:{port}"
    print(f"\n  [OK] Server listening at: {url}")
    print("  [OK] Opening web dashboard in default browser...")

    # Open browser after a brief moment
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(url)

    Thread(target=open_browser, daemon=True).start()

    print("\n  Press CTRL+C to stop the web server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Shutting down web server...]")
        httpd.server_close()
        print("[Server stopped successfully]")


if __name__ == "__main__":
    main(5000)
