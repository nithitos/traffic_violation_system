"""
Login Window - Tkinter Authentication Dialog (Module 2)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from ..auth.auth_service import AuthService, UserSession
from ..auth.exceptions import AuthError, InvalidCredentialsError, UserNotFoundError


class LoginWindow:
    """Modern Login UI with quick-login demo options and role-based validation."""

    def __init__(self, root: tk.Tk, auth_service: AuthService, on_login_success: Callable[[UserSession], None]):
        self.root = root
        self.auth = auth_service
        self.on_success = on_login_success

        self.root.title("Traffic Violation & Accident Alert System - Secure Login")
        self.root.geometry("460x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e272e")

        self._build_ui()

    def _build_ui(self) -> None:
        # Header Container
        hdr_frame = tk.Frame(self.root, bg="#0be881", height=90)
        hdr_frame.pack(fill="x")
        hdr_frame.pack_propagate(False)

        lbl_title = tk.Label(
            hdr_frame,
            text="TRAFFIC ENFORCEMENT",
            font=("Segoe UI", 16, "bold"),
            bg="#0be881",
            fg="#1e272e",
        )
        lbl_title.pack(pady=(16, 2))

        lbl_sub = tk.Label(
            hdr_frame,
            text="Intelligent Monitoring & Alert System",
            font=("Segoe UI", 9),
            bg="#0be881",
            fg="#2f3542",
        )
        lbl_sub.pack()

        # Main Card Body
        card = tk.Frame(self.root, bg="#2f3542", padx=25, pady=25)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_signin = tk.Label(
            card,
            text="Sign In to Control Center",
            font=("Segoe UI", 13, "bold"),
            bg="#2f3542",
            fg="#f1f2f6",
        )
        lbl_signin.pack(anchor="w", pady=(0, 15))

        # Username Field
        lbl_u = tk.Label(card, text="Username:", font=("Segoe UI", 10), bg="#2f3542", fg="#ced6e0")
        lbl_u.pack(anchor="w")
        self.ent_user = tk.Entry(
            card,
            font=("Segoe UI", 11),
            bg="#1e272e",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            bd=5,
        )
        self.ent_user.pack(fill="x", pady=(4, 12))
        self.ent_user.insert(0, "admin")

        # Password Field
        lbl_p = tk.Label(card, text="Password:", font=("Segoe UI", 10), bg="#2f3542", fg="#ced6e0")
        lbl_p.pack(anchor="w")
        self.ent_pass = tk.Entry(
            card,
            font=("Segoe UI", 11),
            show="*",
            bg="#1e272e",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            bd=5,
        )
        self.ent_pass.pack(fill="x", pady=(4, 18))
        self.ent_pass.insert(0, "admin123")
        self.ent_pass.bind("<Return>", lambda e: self._handle_login())

        # Sign In Button
        btn_login = tk.Button(
            card,
            text="AUTHENTICATE & ENTER",
            font=("Segoe UI", 11, "bold"),
            bg="#0be881",
            fg="#1e272e",
            activebackground="#05c46b",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._handle_login,
        )
        btn_login.pack(fill="x", pady=(0, 16), ipady=5)

        # Quick Login Section for Testing Roles
        sep = tk.Label(card, text="─── Quick Demo Logins ───", font=("Segoe UI", 8), bg="#2f3542", fg="#747d8c")
        sep.pack(pady=(0, 8))

        quick_frame = tk.Frame(card, bg="#2f3542")
        quick_frame.pack(fill="x")

        roles_data = [
            ("Admin", "admin", "admin123", "#ff4757"),
            ("Officer", "officer1", "officer123", "#1e90ff"),
            ("Operator", "operator1", "operator123", "#ffa502"),
        ]
        for name, u, p, col in roles_data:
            b = tk.Button(
                quick_frame,
                text=name,
                font=("Segoe UI", 9, "bold"),
                bg=col,
                fg="#ffffff",
                relief="flat",
                cursor="hand2",
                command=lambda usr=u, pwd=p: self._fill_and_login(usr, pwd),
            )
            b.pack(side="left", expand=True, fill="x", padx=2, ipady=3)

    def _fill_and_login(self, username: str, password: str) -> None:
        self.ent_user.delete(0, tk.END)
        self.ent_user.insert(0, username)
        self.ent_pass.delete(0, tk.END)
        self.ent_pass.insert(0, password)
        self._handle_login()

    def _handle_login(self) -> None:
        u = self.ent_user.get().strip()
        p = self.ent_pass.get()
        if not u or not p:
            messagebox.showwarning("Missing Fields", "Please enter both username and password.")
            return

        try:
            session = self.auth.login(u, p)
            self.on_success(session)
        except (InvalidCredentialsError, UserNotFoundError) as e:
            messagebox.showerror("Authentication Failed", str(e))
        except AuthError as e:
            messagebox.showerror("Access Error", str(e))
        except Exception as e:
            messagebox.showerror("System Error", f"Unexpected error: {e}")
