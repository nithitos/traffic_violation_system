"""
Authentication and RBAC Package for Traffic Violation & Alert System
"""
from .auth_service import (
    AuthService,
    UserSession,
    ROLE_ADMIN,
    ROLE_TRAFFIC_OFFICER,
    ROLE_CONTROL_ROOM_OPERATOR,
    PERM_VIEW_LIVE_MONITOR,
    PERM_TRIGGER_ALERT,
    PERM_REVIEW_VIOLATIONS,
    PERM_APPROVE_CHALLAN,
    PERM_VIEW_REPORTS,
    PERM_EXPORT_REPORTS,
    PERM_MANAGE_USERS,
    PERM_MANAGE_CAMERAS,
    PERM_CONFIG_FINES,
)
from .exceptions import (
    AuthError,
    InvalidCredentialsError,
    UserNotFoundError,
    AccountInactiveError,
    UnauthorizedActionError,
)

__all__ = [
    "AuthService",
    "UserSession",
    "ROLE_ADMIN",
    "ROLE_TRAFFIC_OFFICER",
    "ROLE_CONTROL_ROOM_OPERATOR",
    "PERM_VIEW_LIVE_MONITOR",
    "PERM_TRIGGER_ALERT",
    "PERM_REVIEW_VIOLATIONS",
    "PERM_APPROVE_CHALLAN",
    "PERM_VIEW_REPORTS",
    "PERM_EXPORT_REPORTS",
    "PERM_MANAGE_USERS",
    "PERM_MANAGE_CAMERAS",
    "PERM_CONFIG_FINES",
    "AuthError",
    "InvalidCredentialsError",
    "UserNotFoundError",
    "AccountInactiveError",
    "UnauthorizedActionError",
]
