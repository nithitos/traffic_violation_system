"""
Complete Verification Suite for Modules 1 to 4
Runs automated unit and integration tests across all implemented subsystems.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.test_module1 import run_all_tests as test_m1
from traffic_violation_system.test_module2 import run_all_tests as test_m2
from traffic_violation_system.test_module3 import run_all_tests as test_m3
from traffic_violation_system.test_module4 import run_all_tests as test_m4


def main():
    print("\n" + "#" * 75)
    print("  RUNNING FULL TEST SUITE FOR MODULES 1, 2, 3, AND 4")
    print("#" * 75)

    try:
        test_m1()
        test_m2()
        test_m3()
        test_m4()
        print("\n" + "#" * 75)
        print("  ALL 4 MODULES VERIFIED 100% SUCCESSFULLY!")
        print("#" * 75 + "\n")
    except Exception as e:
        print(f"\n[FATAL TEST FAILURE]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
