"""
Application Coordinator - Manages Login & Dashboard Lifecycle
"""
import tkinter as tk
from ..auth.auth_service import AuthService, UserSession
from ..database.db_manager import DatabaseManager
from ..database.seed_data import seed_database
from ..networking.socket_server import TrafficSocketServer
from .login_window import LoginWindow
from .dashboard import MainDashboard


class TrafficSystemApp:
    """Manages window transitions, background socket server, and DB connection."""

    def __init__(self):
        self.root = tk.Tk()
        self.db = DatabaseManager()
        seed_database(self.db)

        self.auth_service = AuthService(self.db)

        # Start Background Socket Server
        self.socket_server = TrafficSocketServer(db_manager=self.db)
        self.socket_server.start()

        # Handle window close cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.current_session: UserSession = None
        self.show_login()

    def show_login(self) -> None:
        """Render the login window."""
        self._clear_root()
        self.root.geometry("460x540")
        LoginWindow(
            root=self.root,
            auth_service=self.auth_service,
            on_login_success=self.on_login_success,
        )

    def on_login_success(self, session: UserSession) -> None:
        """Called upon successful authentication."""
        self.current_session = session
        self._clear_root()
        self.dashboard = MainDashboard(
            root=self.root,
            session=session,
            socket_server=self.socket_server,
            db_manager=self.db,
            on_logout=self.show_login,
        )

    def _clear_root(self) -> None:
        for widget in self.root.winfo_children():
            widget.destroy()

    def on_close(self) -> None:
        """Gracefully stop socket server and destroy window."""
        try:
            self.socket_server.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
