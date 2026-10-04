"""
Authentication & Authorization Custom Exceptions (Module 2)
"""

class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when username or password does not match."""
    pass


class UserNotFoundError(AuthError):
    """Raised when user account is not found."""
    pass


class AccountInactiveError(AuthError):
    """Raised when account has been deactivated."""
    pass


class UnauthorizedActionError(AuthError):
    """Raised when user role lacks required permission."""
    pass
