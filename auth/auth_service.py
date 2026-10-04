"""
Authentication Service & Role-Based Access Control (RBAC) - Module 2
"""
import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Set, List
from .exceptions import (
    AuthError,
    InvalidCredentialsError,
    UserNotFoundError,
    AccountInactiveError,
    UnauthorizedActionError,
)
from ..database.db_manager import DatabaseManager


# Role Definitions
ROLE_ADMIN = "ADMIN"
ROLE_TRAFFIC_OFFICER = "TRAFFIC_OFFICER"
ROLE_CONTROL_ROOM_OPERATOR = "CONTROL_ROOM_OPERATOR"

# Granular Permissions
PERM_VIEW_LIVE_MONITOR = "view_live_monitor"
PERM_TRIGGER_ALERT = "trigger_alert"
PERM_REVIEW_VIOLATIONS = "review_violations"
PERM_APPROVE_CHALLAN = "approve_challan"
PERM_VIEW_REPORTS = "view_reports"
PERM_EXPORT_REPORTS = "export_reports"
PERM_MANAGE_USERS = "manage_users"
PERM_MANAGE_CAMERAS = "manage_cameras"
PERM_CONFIG_FINES = "config_fines"

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_ADMIN: {
        PERM_VIEW_LIVE_MONITOR,
        PERM_TRIGGER_ALERT,
        PERM_REVIEW_VIOLATIONS,
        PERM_APPROVE_CHALLAN,
        PERM_VIEW_REPORTS,
        PERM_EXPORT_REPORTS,
        PERM_MANAGE_USERS,
        PERM_MANAGE_CAMERAS,
        PERM_CONFIG_FINES,
    },
    ROLE_TRAFFIC_OFFICER: {
        PERM_VIEW_LIVE_MONITOR,
        PERM_TRIGGER_ALERT,
        PERM_REVIEW_VIOLATIONS,
        PERM_APPROVE_CHALLAN,
        PERM_VIEW_REPORTS,
        PERM_EXPORT_REPORTS,
    },
    ROLE_CONTROL_ROOM_OPERATOR: {
        PERM_VIEW_LIVE_MONITOR,
        PERM_TRIGGER_ALERT,
        PERM_REVIEW_VIOLATIONS,
    },
}


@dataclass
class UserSession:
    user_id: int
    username: str
    role: str
    full_name: str
    email: str
    logged_in_at: str

    def has_permission(self, permission: str) -> bool:
        allowed = ROLE_PERMISSIONS.get(self.role, set())
        return permission in allowed

    def require_permission(self, permission: str) -> None:
        if not self.has_permission(permission):
            raise UnauthorizedActionError(
                f"User '{self.username}' with role '{self.role}' lacks permission: '{permission}'"
            )

    @property
    def display_role(self) -> str:
        roles_map = {
            ROLE_ADMIN: "Project Administrator",
            ROLE_TRAFFIC_OFFICER: "Traffic Officer",
            ROLE_CONTROL_ROOM_OPERATOR: "Control Room Operator",
        }
        return roles_map.get(self.role, self.role)


class AuthService:
    """Manages authentication, salted SHA-256 password verification, and RBAC."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        if not salt:
            salt = os.urandom(16).hex()
        hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
        return hashed, salt

    def register_user(
        self,
        username: str,
        password: str,
        role: str,
        full_name: str,
        email: str = "",
    ) -> int:
        """Register a new system user with hashed credentials."""
        username_clean = username.strip().lower()
        if not username_clean or len(username_clean) < 3:
            raise AuthError("Username must have at least 3 characters.")
        if not password or len(password) < 6:
            raise AuthError("Password must have at least 6 characters.")
        if role not in ROLE_PERMISSIONS:
            raise AuthError(f"Invalid role '{role}'. Allowed: {', '.join(ROLE_PERMISSIONS.keys())}")

        hashed_pwd, salt = self.hash_password(password)
        conn = self.db.get_connection()
        try:
            with conn:
                cur = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, salt, role, full_name, email, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
                    """,
                    (username_clean, hashed_pwd, salt, role, full_name.strip(), email.strip()),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            raise AuthError(f"Username '{username_clean}' is already registered.")

    def login(self, username: str, password: str) -> UserSession:
        """Authenticate user and return an active UserSession with RBAC permissions."""
        username_clean = username.strip().lower()
        conn = self.db.get_connection()
        cur = conn.execute("SELECT * FROM users WHERE username = ?", (username_clean,))
        row = cur.fetchone()

        if not row:
            raise UserNotFoundError(f"User '{username_clean}' not found.")

        user_data = dict(row)
        if not user_data.get("is_active"):
            raise AccountInactiveError("This account is currently disabled. Contact administrator.")

        # Verify password hash with salt
        stored_hash = user_data["password_hash"]
        salt = user_data["salt"]
        computed_hash, _ = self.hash_password(password, salt)

        if computed_hash != stored_hash:
            raise InvalidCredentialsError("Incorrect password. Please try again.")

        return UserSession(
            user_id=user_data["id"],
            username=user_data["username"],
            role=user_data["role"],
            full_name=user_data["full_name"],
            email=user_data.get("email", ""),
            logged_in_at=datetime.now().isoformat(),
        )

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users without password hashes."""
        conn = self.db.get_connection()
        cur = conn.execute("SELECT id, username, role, full_name, email, is_active, created_at FROM users ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]
