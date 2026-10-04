"""
Traffic Violation & Accident Alert System - Main Launcher
Modules 1 to 4 Integrated Desktop Application
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.gui.app import TrafficSystemApp


def main():
    print("=" * 65)
    print("🚦 TRAFFIC VIOLATION & ACCIDENT ALERT SYSTEM")
    print("   Starting Core Services & Tkinter Desktop Control Center...")
    print("=" * 65)
    app = TrafficSystemApp()
    app.run()


if __name__ == "__main__":
    main()
