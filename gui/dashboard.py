"""
Main Dashboard Window - Tkinter Comprehensive UI (Modules 1 - 4)
Integrates Live Monitoring, Real-time Socket Alerts, E-Challan Management,
and Pandas-driven Reports.
"""
import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..auth.auth_service import UserSession, PERM_APPROVE_CHALLAN, PERM_EXPORT_REPORTS
from ..database.db_manager import DatabaseManager
from ..detection.detector import ViolationDetector
from ..detection.violation_types import ViolationType
from ..inputs.data_collector import DataCollector
from ..inputs.sensor_simulator import SensorSimulator, TrafficSignalSimulator
from ..models.camera import TrafficCamera, DetectedObject
from ..networking.socket_server import TrafficSocketServer
from ..networking.camera_client import CameraSocketClient
from ..processing.challan_service import ChallanService
from ..processing.report_service import ReportService


class MainDashboard:
    """Central Control Room GUI connecting all 4 modules."""

    def __init__(
        self,
        root: tk.Tk,
        session: UserSession,
        socket_server: TrafficSocketServer,
        db_manager: Optional[DatabaseManager] = None,
        on_logout: Optional[callable] = None,
    ):
        self.root = root
        self.session = session
        self.socket_server = socket_server
        self.on_logout = on_logout
        self.db = db_manager or DatabaseManager()

        self.collector = DataCollector(self.db)
        self.detector = ViolationDetector(self.db)
        self.challan_svc = ChallanService(self.db)
        self.report_svc = ReportService(self.db)

        # Active state
        self.active_camera: Optional[TrafficCamera] = None
        self.cameras = self.db.get_all_cameras()
        if self.cameras:
            self.active_camera = self.cameras[0]

        self.signal_sim = TrafficSignalSimulator()
        self.sensor_sim = SensorSimulator("TN-07-AB-1234")
        self.is_monitoring_active = True

        # Configure Root Window
        self.root.title(f"Traffic Violation & Alert System - [{self.session.display_role}]")
        self.root.geometry("1180x760")
        self.root.minsize(1050, 680)
        self.root.configure(bg="#1e272e")

        # Live alert queue
        self.recent_alerts: List[Dict[str, Any]] = []

        # Hook socket server alerts into GUI
        self.socket_server.register_alert_callback(self._on_live_socket_alert)

        self._init_styles()
        self._build_topbar()
        self._build_main_layout()

        # Start background timer for signal and live canvas updates
        self._start_live_loop()

    def _init_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2f3542", foreground="#f1f2f6", fieldbackground="#2f3542", rowheight=28)
        style.configure("Treeview.Heading", background="#1e272e", foreground="#0be881", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#0be881")], foreground=[("selected", "#1e272e")])

    def _build_topbar(self) -> None:
        top = tk.Frame(self.root, bg="#2f3542", height=60)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        # Title
        lbl_brand = tk.Label(
            top,
            text="🚦 TRAFFIC VIOLATION & ALERT SYSTEM",
            font=("Segoe UI", 14, "bold"),
            bg="#2f3542",
            fg="#0be881",
        )
        lbl_brand.pack(side="left", padx=20)

        # User Info Badge
        user_info = tk.Frame(top, bg="#2f3542")
        user_info.pack(side="right", padx=15)

        lbl_user = tk.Label(
            user_info,
            text=f"👤 {self.session.full_name} ({self.session.display_role})",
            font=("Segoe UI", 10, "bold"),
            bg="#2f3542",
            fg="#f1f2f6",
        )
        lbl_user.pack(side="left", padx=10)

        # Socket status
        lbl_sock = tk.Label(
            user_info,
            text="● Socket Active :9999",
            font=("Segoe UI", 9, "bold"),
            bg="#2f3542",
            fg="#0be881",
        )
        lbl_sock.pack(side="left", padx=10)

        btn_out = tk.Button(
            user_info,
            text="Sign Out",
            font=("Segoe UI", 9, "bold"),
            bg="#ff4757",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._handle_logout,
        )
        btn_out.pack(side="left", padx=5)

    def _build_main_layout(self) -> None:
        self.body_frame = tk.Frame(self.root, bg="#1e272e")
        self.body_frame.pack(fill="both", expand=True)

        # Left Navigation Sidebar
        self.sidebar = tk.Frame(self.body_frame, bg="#2f3542", width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Content Container (Swappable views)
        self.content_container = tk.Frame(self.body_frame, bg="#1e272e")
        self.content_container.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("live", "📡 Live Monitor", self._show_live_monitor),
            ("alerts", "🚨 Real-Time Alerts", self._show_alerts_view),
            ("challans", "📋 E-Challan Manager", self._show_challans_view),
            ("reports", "📊 Reports & Analytics", self._show_reports_view),
            ("registry", "🚗 Vehicles & Drivers", self._show_registry_view),
        ]

        for key, text, cmd in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=text,
                font=("Segoe UI", 11, "bold"),
                bg="#2f3542",
                fg="#f1f2f6",
                activebackground="#0be881",
                activeforeground="#1e272e",
                anchor="w",
                padx=20,
                pady=12,
                relief="flat",
                cursor="hand2",
                command=lambda k=key, c=cmd: self._set_active_view(k, c),
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[key] = btn

        # Default View: Live Monitor
        self._set_active_view("live", self._show_live_monitor)

    def _set_active_view(self, key: str, cmd: callable) -> None:
        for k, b in self.nav_buttons.items():
            if k == key:
                b.configure(bg="#0be881", fg="#1e272e")
            else:
                b.configure(bg="#2f3542", fg="#f1f2f6")

        # Clear existing view
        for child in self.content_container.winfo_children():
            child.destroy()

        cmd()

    # -------------------------------------------------------------
    # VIEW 1: LIVE MONITORING & CAMERA CANVAS (Module 1 & 3)
    # -------------------------------------------------------------
    def _show_live_monitor(self) -> None:
        # Header
        hdr = tk.Frame(self.content_container, bg="#1e272e")
        hdr.pack(fill="x", pady=(0, 10))

        tk.Label(
            hdr,
            text="Live Traffic Monitor & Junction Feed",
            font=("Segoe UI", 15, "bold"),
            bg="#1e272e",
            fg="#f1f2f6",
        ).pack(side="left")

        # Junction selector
        cam_names = [f"{c.camera_id}: {c.junction_name}" for c in self.cameras]
        self.cam_combo = ttk.Combobox(hdr, values=cam_names, state="readonly", width=38)
        if cam_names:
            self.cam_combo.current(0)
        self.cam_combo.pack(side="right")
        self.cam_combo.bind("<<ComboboxSelected>>", self._on_camera_selected)

        # Split pane: Left Canvas, Right Controls
        main_pane = tk.Frame(self.content_container, bg="#1e272e")
        main_pane.pack(fill="both", expand=True)

        # Traffic Animation Canvas
        canvas_box = tk.Frame(main_pane, bg="#2f3542", bd=1, relief="solid")
        canvas_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.canvas = tk.Canvas(canvas_box, bg="#353b48", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.car_y = 360  # Initial vehicle position on canvas

        # Right Control & Telemetry Panel
        ctrl_panel = tk.Frame(main_pane, bg="#2f3542", width=310, padx=15, pady=15)
        ctrl_panel.pack(side="right", fill="y")
        ctrl_panel.pack_propagate(False)

        tk.Label(
            ctrl_panel,
            text="Junction Controls",
            font=("Segoe UI", 12, "bold"),
            bg="#2f3542",
            fg="#0be881",
        ).pack(anchor="w", pady=(0, 8))

        # Signal Light Toggle
        sig_frame = tk.Frame(ctrl_panel, bg="#2f3542")
        sig_frame.pack(fill="x", pady=(0, 12))
        tk.Label(sig_frame, text="Signal:", font=("Segoe UI", 10), bg="#2f3542", fg="#ced6e0").pack(side="left")
        
        self.lbl_curr_sig = tk.Label(
            sig_frame,
            text="GREEN",
            font=("Segoe UI", 10, "bold"),
            bg="#0be881",
            fg="#1e272e",
            padx=10,
        )
        self.lbl_curr_sig.pack(side="left", padx=8)

        btn_toggle_sig = tk.Button(
            sig_frame,
            text="Switch RED",
            font=("Segoe UI", 8, "bold"),
            bg="#ff4757",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._manual_switch_signal,
        )
        btn_toggle_sig.pack(side="right")

        # Violation Simulators
        tk.Label(
            ctrl_panel,
            text="Trigger Live Violation Test",
            font=("Segoe UI", 11, "bold"),
            bg="#2f3542",
            fg="#f1f2f6",
        ).pack(anchor="w", pady=(10, 6))

        v_buttons = [
            ("🔴 Red Signal Jump", lambda: self._trigger_simulated_violation("RED_SIGNAL"), "#ff4757"),
            ("⚡ Speed Violation (85 km/h)", lambda: self._trigger_simulated_violation("OVER_SPEEDING"), "#e67e22"),
            ("⛔ Wrong Side Driving", lambda: self._trigger_simulated_violation("WRONG_SIDE"), "#9b59b6"),
            ("🛵 No Helmet (Motorcycle)", lambda: self._trigger_simulated_violation("NO_HELMET"), "#3498db"),
            ("🚷 No Seatbelt (Car)", lambda: self._trigger_simulated_violation("NO_SEATBELT"), "#1abc9c"),
            ("🅿️ Illegal Parking Zone", lambda: self._trigger_simulated_violation("ILLEGAL_PARKING"), "#f39c12"),
        ]

        for text, cmd, col in v_buttons:
            b = tk.Button(
                ctrl_panel,
                text=text,
                font=("Segoe UI", 9, "bold"),
                bg=col,
                fg="#ffffff",
                anchor="w",
                padx=10,
                pady=4,
                relief="flat",
                cursor="hand2",
                command=cmd,
            )
            b.pack(fill="x", pady=3)

        # Telemetry Box
        tk.Label(
            ctrl_panel,
            text="Telemetry Ingestion Feed",
            font=("Segoe UI", 10, "bold"),
            bg="#2f3542",
            fg="#ced6e0",
        ).pack(anchor="w", pady=(15, 4))

        self.lbl_telemetry = tk.Label(
            ctrl_panel,
            text="Lat: 13.0522, Lon: 80.2503\nSpeed: 44.5 km/h | Normal Cruise\nAirbag: INTACT | Tilt: 1.2°",
            font=("Consolas", 8),
            bg="#1e272e",
            fg="#0be881",
            justify="left",
            padx=8,
            pady=8,
        )
        self.lbl_telemetry.pack(fill="x")

    def _on_camera_selected(self, event) -> None:
        idx = self.cam_combo.current()
        if 0 <= idx < len(self.cameras):
            self.active_camera = self.cameras[idx]

    def _manual_switch_signal(self) -> None:
        if not self.active_camera:
            return
        curr = self.active_camera.signal_status
        new_s = "RED" if curr != "RED" else "GREEN"
        self.active_camera.update_signal(new_s)
        self.signal_sim.force_state(new_s)
        self.lbl_curr_sig.configure(
            text=new_s,
            bg="#ff4757" if new_s == "RED" else "#0be881",
            fg="#ffffff" if new_s == "RED" else "#1e272e",
        )

    def _trigger_simulated_violation(self, scenario: str) -> None:
        cam_id = self.active_camera.camera_id if self.active_camera else "CAM-CHN-01"
        try:
            client = CameraSocketClient()
            resp = client.trigger_sample_violation(
                camera_id=cam_id,
                violation_scenario=scenario,
            )
            client.close()
            messagebox.showinfo("Socket Telemetry Transmitted", f"Scenario: {scenario}\nServer Response: {resp}")
        except Exception as e:
            messagebox.showerror("Socket Error", f"Failed to send telemetry: {e}")

    # -------------------------------------------------------------
    # VIEW 2: REAL-TIME ALERTS & REVIEW (Module 3)
    # -------------------------------------------------------------
    def _show_alerts_view(self) -> None:
        tk.Label(
            self.content_container,
            text="Real-Time Traffic Violation Alerts",
            font=("Segoe UI", 15, "bold"),
            bg="#1e272e",
            fg="#f1f2f6",
        ).pack(anchor="w", pady=(0, 10))

        # Action Toolbar
        tb = tk.Frame(self.content_container, bg="#1e272e")
        tb.pack(fill="x", pady=(0, 8))

        btn_refresh = tk.Button(
            tb,
            text="🔄 Refresh Alerts",
            font=("Segoe UI", 9, "bold"),
            bg="#2f3542",
            fg="#f1f2f6",
            relief="flat",
            cursor="hand2",
            command=self._load_alerts_data,
        )
        btn_refresh.pack(side="left", padx=(0, 8))

        if self.session.has_permission(PERM_APPROVE_CHALLAN):
            btn_gen_ch = tk.Button(
                tb,
                text="⚡ Approve & Issue E-Challan",
                font=("Segoe UI", 9, "bold"),
                bg="#0be881",
                fg="#1e272e",
                relief="flat",
                cursor="hand2",
                command=self._issue_selected_challan,
            )
            btn_gen_ch.pack(side="left")

        # Treeview for Alerts
        cols = ("id", "type", "vehicle", "driver", "location", "fine", "status", "time")
        self.alert_tree = ttk.Treeview(self.content_container, columns=cols, show="headings", height=14)
        self.alert_tree.pack(fill="both", expand=True)

        self.alert_tree.heading("id", text="Violation ID")
        self.alert_tree.heading("type", text="Offense")
        self.alert_tree.heading("vehicle", text="Vehicle No")
        self.alert_tree.heading("driver", text="Registered Owner")
        self.alert_tree.heading("location", text="Location")
        self.alert_tree.heading("fine", text="Fine (INR)")
        self.alert_tree.heading("status", text="Status")
        self.alert_tree.heading("time", text="Timestamp")

        self.alert_tree.column("id", width=140)
        self.alert_tree.column("type", width=160)
        self.alert_tree.column("vehicle", width=110)
        self.alert_tree.column("driver", width=130)
        self.alert_tree.column("location", width=170)
        self.alert_tree.column("fine", width=80)
        self.alert_tree.column("status", width=110)
        self.alert_tree.column("time", width=140)

        self._load_alerts_data()

    def _load_alerts_data(self) -> None:
        if not hasattr(self, "alert_tree"):
            return
        for r in self.alert_tree.get_children():
            self.alert_tree.delete(r)

        vios = self.detector.get_recent_violations(limit=100)
        for v in vios:
            veh_info = self.db.get_vehicle_with_driver(v["vehicle_number"])
            drv_name = veh_info["driver_name"] if veh_info else "Unregistered"
            self.alert_tree.insert(
                "",
                "end",
                iid=v["violation_id"],
                values=(
                    v["violation_id"],
                    v["violation_type"].replace("_", " "),
                    v["vehicle_number"],
                    drv_name,
                    v["location"],
                    f"INR {v['fine_amount']:,.0f}",
                    v["status"],
                    v["timestamp"],
                ),
            )

    def _issue_selected_challan(self) -> None:
        sel = self.alert_tree.selection()
        if not sel:
            messagebox.showwarning("Select Record", "Please select a recorded violation from the list.")
            return

        vio_id = sel[0]
        try:
            ch = self.challan_svc.generate_challan_from_violation(vio_id)
            messagebox.showinfo("E-Challan Issued", f"Successfully created E-Challan:\nID: {ch['challan_id']}\nAmount: INR {ch['amount']}\nDue Date: {ch['due_date']}")
            self._load_alerts_data()
        except Exception as e:
            messagebox.showerror("Error Issuing Challan", str(e))

    # -------------------------------------------------------------
    # VIEW 3: E-CHALLAN MANAGEMENT (Module 4)
    # -------------------------------------------------------------
    def _show_challans_view(self) -> None:
        tk.Label(
            self.content_container,
            text="E-Challan Enforcement & Settlement Center",
            font=("Segoe UI", 15, "bold"),
            bg="#1e272e",
            fg="#f1f2f6",
        ).pack(anchor="w", pady=(0, 10))

        # Toolbar
        tb = tk.Frame(self.content_container, bg="#1e272e")
        tb.pack(fill="x", pady=(0, 8))

        btn_mark_paid = tk.Button(
            tb,
            text="💳 Mark Selected as PAID",
            font=("Segoe UI", 9, "bold"),
            bg="#0be881",
            fg="#1e272e",
            relief="flat",
            cursor="hand2",
            command=self._mark_selected_paid,
        )
        btn_mark_paid.pack(side="left", padx=(0, 8))

        btn_print = tk.Button(
            tb,
            text="📄 View / Print Official Receipt",
            font=("Segoe UI", 9, "bold"),
            bg="#3498db",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._open_receipt_html,
        )
        btn_print.pack(side="left", padx=(0, 8))

        btn_refresh = tk.Button(
            tb,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg="#2f3542",
            fg="#f1f2f6",
            relief="flat",
            cursor="hand2",
            command=self._load_challans_data,
        )
        btn_refresh.pack(side="left")

        # Challan Table
        cols = ("ch_id", "veh", "driver", "offense", "amount", "status", "due", "issued")
        self.ch_tree = ttk.Treeview(self.content_container, columns=cols, show="headings", height=14)
        self.ch_tree.pack(fill="both", expand=True)

        self.ch_tree.heading("ch_id", text="Challan ID")
        self.ch_tree.heading("veh", text="Vehicle No")
        self.ch_tree.heading("driver", text="Driver")
        self.ch_tree.heading("offense", text="Offense")
        self.ch_tree.heading("amount", text="Fine Amount")
        self.ch_tree.heading("status", text="Payment Status")
        self.ch_tree.heading("due", text="Due Date")
        self.ch_tree.heading("issued", text="Issued Date")

        self.ch_tree.column("ch_id", width=140)
        self.ch_tree.column("veh", width=110)
        self.ch_tree.column("driver", width=130)
        self.ch_tree.column("offense", width=150)
        self.ch_tree.column("amount", width=90)
        self.ch_tree.column("status", width=100)
        self.ch_tree.column("due", width=100)
        self.ch_tree.column("issued", width=130)

        self._load_challans_data()

    def _load_challans_data(self) -> None:
        if not hasattr(self, "ch_tree"):
            return
        for r in self.ch_tree.get_children():
            self.ch_tree.delete(r)

        items = self.challan_svc.get_all_challans()
        for ch in items:
            self.ch_tree.insert(
                "",
                "end",
                iid=ch["challan_id"],
                values=(
                    ch["challan_id"],
                    ch["vehicle_number"],
                    ch.get("driver_name") or "Unregistered",
                    (ch.get("violation_type") or "").replace("_", " "),
                    f"INR {ch['amount']:,.0f}",
                    ch["payment_status"],
                    ch["due_date"],
                    ch["issue_date"].split()[0] if " " in ch["issue_date"] else ch["issue_date"],
                ),
            )

    def _mark_selected_paid(self) -> None:
        sel = self.ch_tree.selection()
        if not sel:
            messagebox.showwarning("Select Record", "Please select a challan to mark as paid.")
            return

        ch_id = sel[0]
        self.challan_svc.mark_challan_paid(ch_id)
        messagebox.showinfo("Payment Recorded", f"Challan {ch_id} is now marked as PAID.")
        self._load_challans_data()

    def _open_receipt_html(self) -> None:
        sel = self.ch_tree.selection()
        if not sel:
            messagebox.showwarning("Select Record", "Please select a challan to generate receipt.")
            return

        ch_id = sel[0]
        try:
            path = self.report_svc.generate_printable_receipt(ch_id)
            webbrowser.open(f"file:///{os.path.abspath(path)}")
        except Exception as e:
            messagebox.showerror("Receipt Error", str(e))

    # -------------------------------------------------------------
    # VIEW 4: REPORTS & ANALYTICS (Module 4)
    # -------------------------------------------------------------
    def _show_reports_view(self) -> None:
        tk.Label(
            self.content_container,
            text="Analytics, Statistics & Reporting Center",
            font=("Segoe UI", 15, "bold"),
            bg="#1e272e",
            fg="#f1f2f6",
        ).pack(anchor="w", pady=(0, 10))

        # Metrics Row
        stats = self.report_svc.get_summary_statistics()

        metric_frame = tk.Frame(self.content_container, bg="#1e272e")
        metric_frame.pack(fill="x", pady=(0, 15))

        kpis = [
            ("TOTAL VIOLATIONS", str(stats["total_violations"]), "#0be881"),
            ("TOTAL FINES", f"INR {stats['total_fines_imposed']:,.0f}", "#e67e22"),
            ("PAID CHALLANS", str(stats["paid_challans"]), "#3498db"),
            ("PENDING CHALLANS", str(stats["pending_challans"]), "#ff4757"),
            ("REVENUE COLLECTED", f"INR {stats['revenue_collected']:,.0f}", "#2ed573"),
        ]

        for label, val, color in kpis:
            card = tk.Frame(metric_frame, bg="#2f3542", padx=12, pady=10)
            card.pack(side="left", expand=True, fill="both", padx=4)
            tk.Label(card, text=label, font=("Segoe UI", 8, "bold"), bg="#2f3542", fg="#ced6e0").pack()
            tk.Label(card, text=val, font=("Segoe UI", 13, "bold"), bg="#2f3542", fg=color).pack(pady=(4, 0))

        # Export Buttons
        if self.session.has_permission(PERM_EXPORT_REPORTS):
            exp_frame = tk.Frame(self.content_container, bg="#1e272e")
            exp_frame.pack(fill="x", pady=(0, 12))

            btn_exp_vio = tk.Button(
                exp_frame,
                text="📥 Export Violations to CSV",
                font=("Segoe UI", 9, "bold"),
                bg="#2ed573",
                fg="#1e272e",
                relief="flat",
                cursor="hand2",
                command=self._export_violations,
            )
            btn_exp_vio.pack(side="left", padx=(0, 10))

            btn_exp_ch = tk.Button(
                exp_frame,
                text="📥 Export E-Challans to CSV",
                font=("Segoe UI", 9, "bold"),
                bg="#3498db",
                fg="#ffffff",
                relief="flat",
                cursor="hand2",
                command=self._export_challans,
            )
            btn_exp_ch.pack(side="left")

        # Breakdown Table
        tk.Label(
            self.content_container,
            text="Breakdown by Violation Category:",
            font=("Segoe UI", 11, "bold"),
            bg="#1e272e",
            fg="#ced6e0",
        ).pack(anchor="w", pady=(5, 4))

        cols = ("type", "count", "fines")
        tree_breakdown = ttk.Treeview(self.content_container, columns=cols, show="headings", height=6)
        tree_breakdown.pack(fill="x", pady=(0, 10))
        tree_breakdown.heading("type", text="Violation Category")
        tree_breakdown.heading("count", text="Total Incidents")
        tree_breakdown.heading("fines", text="Cumulative Fines")

        for item in stats["violation_type_breakdown"]:
            tree_breakdown.insert(
                "",
                "end",
                values=(
                    item["violation_type"].replace("_", " "),
                    item["count"],
                    f"INR {item['total_fines']:,.0f}",
                ),
            )

    def _export_violations(self) -> None:
        path = self.report_svc.export_violations_csv()
        messagebox.showinfo("Export Complete", f"Violations exported successfully:\n{path}")

    def _export_challans(self) -> None:
        path = self.report_svc.export_challans_csv()
        messagebox.showinfo("Export Complete", f"Challans exported successfully:\n{path}")

    # -------------------------------------------------------------
    # VIEW 5: VEHICLE & DRIVER REGISTRY (Module 1)
    # -------------------------------------------------------------
    def _show_registry_view(self) -> None:
        tk.Label(
            self.content_container,
            text="Vehicle and Registered Driver Database",
            font=("Segoe UI", 15, "bold"),
            bg="#1e272e",
            fg="#f1f2f6",
        ).pack(anchor="w", pady=(0, 10))

        cols = ("veh", "type", "model", "color", "driver", "phone", "license")
        tree = ttk.Treeview(self.content_container, columns=cols, show="headings", height=14)
        tree.pack(fill="both", expand=True)

        tree.heading("veh", text="Vehicle No")
        tree.heading("type", text="Type")
        tree.heading("model", text="Make & Model")
        tree.heading("color", text="Color")
        tree.heading("driver", text="Registered Owner")
        tree.heading("phone", text="Phone")
        tree.heading("license", text="License Number")

        for v in self.collector.get_all_registered_vehicles():
            tree.insert(
                "",
                "end",
                values=(
                    v["vehicle_number"],
                    v["vehicle_type"],
                    v.get("make_model", ""),
                    v.get("color", ""),
                    v.get("driver_name", "N/A"),
                    v.get("driver_phone", "N/A"),
                    v.get("license_number", "N/A"),
                ),
            )

    # -------------------------------------------------------------
    # ANIMATION LOOP & LIVE UPDATES
    # -------------------------------------------------------------
    def _start_live_loop(self) -> None:
        if not self.is_monitoring_active:
            return

        # 1. Update Signal light cycle
        sig = self.signal_sim.tick()
        if self.active_camera:
            self.active_camera.update_signal(sig)
        if hasattr(self, "lbl_curr_sig"):
            self.lbl_curr_sig.configure(
                text=sig,
                bg="#ff4757" if sig == "RED" else ("#f1c40f" if sig == "YELLOW" else "#0be881"),
                fg="#ffffff" if sig == "RED" else "#1e272e",
            )

        # 2. Animate Vehicle on Canvas
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self._render_canvas_frame(sig)

        # 3. Schedule next loop iteration (~100ms)
        self.root.after(100, self._start_live_loop)

    def _render_canvas_frame(self, signal_status: str) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        self.canvas.delete("all")

        # Draw Road
        road_w = min(400, w - 80)
        rx1 = (w - road_w) // 2
        rx2 = rx1 + road_w
        self.canvas.create_rectangle(rx1, 0, rx2, h, fill="#2c3e50", outline="")

        # Dashed Center Lane
        mid_x = w // 2
        for y in range(0, h, 30):
            self.canvas.create_line(mid_x, y, mid_x, y + 16, fill="#f1c40f", width=3)

        # Stop Line
        stop_y = h // 2
        self.canvas.create_line(rx1, stop_y, rx2, stop_y, fill="#ffffff", width=4)

        # Traffic Signal Box
        sig_x = rx2 + 20
        sig_y = stop_y - 60
        self.canvas.create_rectangle(sig_x, sig_y, sig_x + 30, sig_y + 80, fill="#1e272e", outline="#ffffff")
        self.canvas.create_oval(sig_x + 6, sig_y + 6, sig_x + 24, sig_y + 24, fill="#ff4757" if signal_status == "RED" else "#4a151b")
        self.canvas.create_oval(sig_x + 6, sig_y + 30, sig_x + 24, sig_y + 48, fill="#f1c40f" if signal_status == "YELLOW" else "#534510")
        self.canvas.create_oval(sig_x + 6, sig_y + 54, sig_x + 24, sig_y + 72, fill="#0be881" if signal_status == "GREEN" else "#0c3b24")

        # Vehicle Movement
        # If signal is RED, car stops before line unless speeding
        if signal_status == "RED" and stop_y < self.car_y < stop_y + 30:
            speed_px = 0  # Stop
        else:
            speed_px = 4

        self.car_y -= speed_px
        if self.car_y < -40:
            self.car_y = h + 20

        # Draw Moving Vehicle
        car_w, car_h = 36, 60
        cx = mid_x - car_w // 2 - 30
        self.canvas.create_rectangle(cx, self.car_y, cx + car_w, self.car_y + car_h, fill="#3498db", outline="#ffffff", width=1)
        self.canvas.create_rectangle(cx + 4, self.car_y + 12, cx + car_w - 4, self.car_y + 24, fill="#1e272e")  # Windshield

    def _on_live_socket_alert(self, payload: Dict[str, Any]) -> None:
        """Callback invoked when socket server catches a real-time violation."""
        self.recent_alerts.append(payload)
        # Schedule GUI update on the main Tkinter thread
        self.root.after(0, self._handle_socket_alert_gui, payload)

    def _handle_socket_alert_gui(self, payload: Dict[str, Any]) -> None:
        if hasattr(self, "alert_tree"):
            self._load_alerts_data()

    def _handle_logout(self) -> None:
        self.is_monitoring_active = False
        if self.on_logout:
            self.on_logout()
