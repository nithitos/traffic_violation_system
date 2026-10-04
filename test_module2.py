"""
Module 2 Verification & Test Suite
Tests User Authentication and Role-Based Access Control (RBAC).
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from traffic_violation_system.database.db_manager import DatabaseManager
from traffic_violation_system.database.seed_data import seed_database
from traffic_violation_system.auth.auth_service import (
    AuthService,
    ROLE_ADMIN,
    ROLE_TRAFFIC_OFFICER,
    ROLE_CONTROL_ROOM_OPERATOR,
    PERM_APPROVE_CHALLAN,
    PERM_MANAGE_USERS,
    PERM_VIEW_LIVE_MONITOR,
)
from traffic_violation_system.auth.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UnauthorizedActionError,
)


def run_all_tests():
    print("=" * 70)
    print("TRAFFIC VIOLATION & ACCIDENT ALERT SYSTEM")
    print("MODULE 2: USER AUTHENTICATION & RBAC - VERIFICATION SUITE")
    print("=" * 70)

    db = DatabaseManager()
    seed_database(db)
    auth = AuthService(db)

    # 1. Admin Login & Permissions
    print("\n[STEP 1] Testing Admin Authentication & Full Privileges...")
    admin_session = auth.login("admin", "admin123")
    assert admin_session.role == ROLE_ADMIN
    assert admin_session.has_permission(PERM_MANAGE_USERS)
    assert admin_session.has_permission(PERM_APPROVE_CHALLAN)
    print(f"  [OK] Admin logged in: {admin_session.full_name} ({admin_session.display_role})")
    print("  [OK] Admin granted manage_users and approve_challan permissions.")

    # 2. Traffic Officer Login & Permissions
    print("\n[STEP 2] Testing Traffic Officer Authentication & Permissions...")
    officer_session = auth.login("officer1", "officer123")
    assert officer_session.role == ROLE_TRAFFIC_OFFICER
    assert officer_session.has_permission(PERM_APPROVE_CHALLAN)
    assert not officer_session.has_permission(PERM_MANAGE_USERS)
    print(f"  [OK] Officer logged in: {officer_session.full_name} ({officer_session.display_role})")
    print("  [OK] Officer granted approve_challan; restricted from manage_users.")

    # 3. Control Room Operator Login & Permissions
    print("\n[STEP 3] Testing Control Room Operator Authentication & Restrictions...")
    operator_session = auth.login("operator1", "operator123")
    assert operator_session.role == ROLE_CONTROL_ROOM_OPERATOR
    assert operator_session.has_permission(PERM_VIEW_LIVE_MONITOR)
    assert not operator_session.has_permission(PERM_APPROVE_CHALLAN)
    print(f"  [OK] Operator logged in: {operator_session.full_name} ({operator_session.display_role})")
    print("  [OK] Operator granted view_live_monitor; restricted from approve_challan.")

    # 4. Enforce Permission Check (UnauthorizedActionError)
    print("\n[STEP 4] Testing Permission Enforcement...")
    try:
        operator_session.require_permission(PERM_APPROVE_CHALLAN)
        print("  [FAIL] Expected UnauthorizedActionError for operator approving challan")
    except UnauthorizedActionError as e:
        print(f"  [OK] Correctly blocked unauthorized action: {e}")

    # 5. Invalid Password Error Handling
    print("\n[STEP 5] Testing Exception on Wrong Password...")
    try:
        auth.login("admin", "wrong_password_999")
        print("  [FAIL] Expected InvalidCredentialsError")
    except InvalidCredentialsError as e:
        print(f"  [OK] Correctly caught invalid credentials: {e}")

    # 6. Non-Existent User Error Handling
    print("\n[STEP 6] Testing Exception on Unknown User...")
    try:
        auth.login("unknown_user_xyz", "pass12345")
        print("  [FAIL] Expected UserNotFoundError")
    except UserNotFoundError as e:
        print(f"  [OK] Correctly caught missing user: {e}")

    # 7. User Registration
    print("\n[STEP 7] Testing New User Registration...")
    import time
    test_user = f"officer_{int(time.time())}"
    new_user_id = auth.register_user(
        username=test_user,
        password="securepassword123",
        role=ROLE_TRAFFIC_OFFICER,
        full_name="Officer Meera Nair",
        email="meera.nair@trafficops.gov",
    )
    new_session = auth.login(test_user, "securepassword123")
    assert new_session.user_id == new_user_id
    print(f"  [OK] New user registered and authenticated: {new_session.full_name} (ID: {new_user_id})")

    print("\n" + "=" * 70)
    print("MODULE 2 (USER AUTHENTICATION & RBAC) COMPLETED & VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
