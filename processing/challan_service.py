"""
E-Challan Processing Service (Module 4)
Handles automated E-Challan generation, fine calculation, payment reconciliation, and lifecycle.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..database.db_manager import DatabaseManager


class ChallanService:
    """Manages E-Challan creation, retrieval, and status updates."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def generate_challan_from_violation(self, violation_id: str, due_days: int = 15) -> Dict[str, Any]:
        """
        Convert a recorded violation into an official E-Challan.
        Updates violation status to 'CHALLAN_ISSUED'.
        """
        conn = self.db.get_connection()
        cur = conn.execute("SELECT * FROM violations WHERE violation_id = ?", (violation_id,))
        vio_row = cur.fetchone()
        if not vio_row:
            raise ValueError(f"Violation ID '{violation_id}' not found.")

        vio = dict(vio_row)

        # Check if already generated
        cur = conn.execute("SELECT * FROM challans WHERE violation_id = ?", (violation_id,))
        existing = cur.fetchone()
        if existing:
            return dict(existing)

        # Generate unique Challan ID: ECH-YYYYMMDD-XXXX
        today = datetime.now()
        due_date = (today + timedelta(days=due_days)).strftime("%Y-%m-%d")
        challan_id = f"ECH-{today.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        with conn:
            # 1. Insert into challans
            conn.execute(
                """
                INSERT INTO challans (
                    challan_id, violation_id, vehicle_number, driver_id, amount,
                    issue_date, due_date, payment_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """,
                (
                    challan_id,
                    violation_id,
                    vio["vehicle_number"],
                    vio["driver_id"],
                    vio["fine_amount"],
                    today.strftime("%Y-%m-%d %H:%M:%S"),
                    due_date,
                ),
            )

            # 2. Update violation status
            conn.execute(
                "UPDATE violations SET status = 'CHALLAN_ISSUED' WHERE violation_id = ?",
                (violation_id,),
            )

        return self.get_challan_by_id(challan_id)

    def mark_challan_paid(self, challan_id: str, payment_ref: Optional[str] = None) -> bool:
        """Mark an E-Challan as settled/paid with transaction reference."""
        conn = self.db.get_connection()
        ref = payment_ref or f"UPI-TXN-{uuid.uuid4().hex[:8].upper()}"
        pay_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with conn:
            cur = conn.execute(
                """
                UPDATE challans
                SET payment_status = 'PAID', payment_date = ?, payment_reference = ?
                WHERE challan_id = ?
                """,
                (pay_time, ref, challan_id),
            )
            return cur.rowcount > 0

    def get_challan_by_id(self, challan_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete challan record joined with driver and violation details."""
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            SELECT c.*, v.violation_type, v.location, v.speed_detected, v.speed_limit,
                   v.evidence_image, d.name AS driver_name, d.phone AS driver_phone,
                   d.license_number, d.email AS driver_email
            FROM challans c
            LEFT JOIN violations v ON c.violation_id = v.violation_id
            LEFT JOIN drivers d ON c.driver_id = d.driver_id
            WHERE c.challan_id = ?
            """,
            (challan_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_challans(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all challans, optionally filtered by payment_status."""
        conn = self.db.get_connection()
        query = """
            SELECT c.*, v.violation_type, v.location, d.name AS driver_name
            FROM challans c
            LEFT JOIN violations v ON c.violation_id = v.violation_id
            LEFT JOIN drivers d ON c.driver_id = d.driver_id
        """
        params = []
        if status:
            query += " WHERE c.payment_status = ?"
            params.append(status.upper())
        query += " ORDER BY c.issue_date DESC"

        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def get_challans_by_vehicle(self, vehicle_number: str) -> List[Dict[str, Any]]:
        """Fetch all challans issued to a specific vehicle number."""
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            SELECT c.*, v.violation_type, v.location
            FROM challans c
            LEFT JOIN violations v ON c.violation_id = v.violation_id
            WHERE c.vehicle_number = ?
            ORDER BY c.issue_date DESC
            """,
            (vehicle_number.upper(),),
        )
        return [dict(row) for row in cur.fetchall()]
