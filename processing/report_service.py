"""
Reporting & Analytics Engine (Module 4)
Uses Pandas / NumPy for statistical aggregations, trend analytics, CSV export,
and generates printable E-Challan receipts with embedded evidence.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..config import DB_PATH, REPORTS_DIR, EVIDENCE_DIR
from ..database.db_manager import DatabaseManager

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class ReportService:
    """Provides statistical aggregations, CSV exports, and printable receipts."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    # -------------------------------------------------------------
    # PANDAS / NUMPY STATISTICAL ANALYTICS
    # -------------------------------------------------------------
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Aggregate high-level metrics across all violations and challans."""
        conn = self.db.get_connection()
        
        # Total recorded violations
        cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(fine_amount), 0) FROM violations")
        tot_vios, tot_fines = cur.fetchone()

        # Challan breakdown
        cur = conn.execute(
            """
            SELECT 
                COUNT(*) AS total_challans,
                SUM(CASE WHEN payment_status = 'PAID' THEN 1 ELSE 0 END) AS paid_challans,
                SUM(CASE WHEN payment_status = 'PENDING' THEN 1 ELSE 0 END) AS pending_challans,
                COALESCE(SUM(CASE WHEN payment_status = 'PAID' THEN amount ELSE 0 END), 0) AS revenue_collected,
                COALESCE(SUM(CASE WHEN payment_status = 'PENDING' THEN amount ELSE 0 END), 0) AS revenue_pending
            FROM challans
            """
        )
        ch_row = cur.fetchone()

        # Grouping by Violation Type using Pandas if available
        breakdown = self._get_violation_breakdown()
        peak_hours = self._get_peak_violation_hours()

        return {
            "total_violations": tot_vios,
            "total_fines_imposed": tot_fines,
            "total_challans": ch_row["total_challans"] or 0,
            "paid_challans": ch_row["paid_challans"] or 0,
            "pending_challans": ch_row["pending_challans"] or 0,
            "revenue_collected": ch_row["revenue_collected"] or 0.0,
            "revenue_pending": ch_row["revenue_pending"] or 0.0,
            "violation_type_breakdown": breakdown,
            "peak_hours": peak_hours,
        }

    def _get_violation_breakdown(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if PANDAS_AVAILABLE:
            df = pd.read_sql_query("SELECT violation_type, fine_amount FROM violations", conn)
            if df.empty:
                return []
            grouped = df.groupby("violation_type").agg(
                count=("fine_amount", "count"),
                total_fines=("fine_amount", "sum")
            ).reset_index()
            return grouped.to_dict(orient="records")
        else:
            cur = conn.execute(
                "SELECT violation_type, COUNT(*) as count, SUM(fine_amount) as total_fines FROM violations GROUP BY violation_type"
            )
            return [dict(row) for row in cur.fetchall()]

    def _get_peak_violation_hours(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if PANDAS_AVAILABLE:
            df = pd.read_sql_query("SELECT timestamp FROM violations", conn)
            if df.empty:
                return []
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
            hour_counts = df["hour"].value_counts().sort_index().reset_index()
            hour_counts.columns = ["hour", "violation_count"]
            return hour_counts.to_dict(orient="records")
        else:
            cur = conn.execute(
                "SELECT strftime('%H', timestamp) as hour, COUNT(*) as violation_count FROM violations GROUP BY hour ORDER BY hour"
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------
    # CSV EXPORT
    # -------------------------------------------------------------
    def export_violations_csv(self, filename: Optional[str] = None) -> str:
        """Export all recorded violations to a CSV file."""
        fname = filename or f"violations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out_path = REPORTS_DIR / fname
        conn = self.db.get_connection()

        if PANDAS_AVAILABLE:
            df = pd.read_sql_query("SELECT * FROM violations ORDER BY timestamp DESC", conn)
            df.to_csv(out_path, index=False)
        else:
            cur = conn.execute("SELECT * FROM violations ORDER BY timestamp DESC")
            rows = [dict(r) for r in cur.fetchall()]
            if rows:
                import csv
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                out_path.touch()
        return str(out_path)

    def export_challans_csv(self, filename: Optional[str] = None) -> str:
        """Export all E-Challan records to CSV."""
        fname = filename or f"challans_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out_path = REPORTS_DIR / fname
        conn = self.db.get_connection()

        if PANDAS_AVAILABLE:
            df = pd.read_sql_query("SELECT * FROM challans ORDER BY issue_date DESC", conn)
            df.to_csv(out_path, index=False)
        else:
            cur = conn.execute("SELECT * FROM challans ORDER BY issue_date DESC")
            rows = [dict(r) for r in cur.fetchall()]
            if rows:
                import csv
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                out_path.touch()
        return str(out_path)

    # -------------------------------------------------------------
    # PRINTABLE E-CHALLAN RECEIPT (HTML / PDF)
    # -------------------------------------------------------------
    def generate_printable_receipt(self, challan_id: str) -> str:
        """
        Generate a professional printable HTML receipt for an E-Challan,
        featuring official header, vehicle & driver info, offense details,
        embedded evidence image, and payment instructions.
        """
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            SELECT c.*, v.violation_type, v.location, v.speed_detected, v.speed_limit,
                   v.evidence_image, v.timestamp AS violation_time,
                   d.name AS driver_name, d.phone AS driver_phone, d.license_number,
                   d.address AS driver_address, veh.make_model, veh.vehicle_type
            FROM challans c
            JOIN violations v ON c.violation_id = v.violation_id
            LEFT JOIN drivers d ON c.driver_id = d.driver_id
            LEFT JOIN vehicles veh ON c.vehicle_number = veh.vehicle_number
            WHERE c.challan_id = ?
            """,
            (challan_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Challan ID '{challan_id}' not found.")

        data = dict(row)
        filename = f"receipt_{challan_id}.html"
        out_path = REPORTS_DIR / filename

        evidence_src = data.get("evidence_image") or ""
        # Format evidence path for file URL
        if evidence_src and os.path.exists(evidence_src):
            evidence_tag = f'<img src="file:///{os.path.abspath(evidence_src).replace(os.sep, "/")}" style="max-width: 100%; height: auto; border: 2px solid #333; border-radius: 4px;" alt="Violation Evidence" />'
        else:
            evidence_tag = '<p style="color: #7f8c8d; font-style: italic;">[Evidence Snapshot on File in System]</p>'

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>E-Challan Receipt - {data['challan_id']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 30px;
            background-color: #f8f9fa;
            color: #2c3e50;
        }}
        .receipt-card {{
            max-width: 760px;
            margin: auto;
            background: #ffffff;
            border: 1px solid #dcdde1;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #2f3640;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            color: #2f3640;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .header h3 {{
            margin: 5px 0 0 0;
            font-size: 14px;
            color: #718093;
            font-weight: 500;
        }}
        .badge-status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
            background-color: {'#2ed573' if data['payment_status'] == 'PAID' else '#ff4757'};
            color: white;
            float: right;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: bold;
            color: #2f3640;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 20px;
            margin-bottom: 8px;
            border-bottom: 1px solid #f1f2f6;
            padding-bottom: 4px;
        }}
        table.info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 15px;
        }}
        table.info-table td {{
            padding: 8px;
            border-bottom: 1px solid #f1f2f6;
        }}
        table.info-table td.label {{
            font-weight: 600;
            color: #718093;
            width: 35%;
        }}
        table.info-table td.val {{
            color: #2f3640;
            font-weight: 500;
        }}
        .fine-total-box {{
            background-color: #f1f2f6;
            border-radius: 6px;
            padding: 16px;
            text-align: right;
            margin: 20px 0;
        }}
        .fine-total-box .amount {{
            font-size: 26px;
            font-weight: bold;
            color: #c0392b;
        }}
        .evidence-box {{
            text-align: center;
            margin: 20px 0;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
        }}
        .footer {{
            text-align: center;
            font-size: 11px;
            color: #a4b0be;
            margin-top: 25px;
            border-top: 1px solid #f1f2f6;
            padding-top: 10px;
        }}
        @media print {{
            body {{ background-color: #fff; margin: 0; }}
            .receipt-card {{ box-shadow: none; border: none; padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="receipt-card">
        <div class="header">
            <span class="badge-status">{data['payment_status']}</span>
            <h1>Traffic Enforcement Department</h1>
            <h3>Official Electronic Traffic Violation Notice (E-Challan)</h3>
        </div>

        <div class="section-title">Notice & Offender Details</div>
        <table class="info-table">
            <tr>
                <td class="label">Challan Number:</td>
                <td class="val"><strong>{data['challan_id']}</strong></td>
            </tr>
            <tr>
                <td class="label">Violation Reference ID:</td>
                <td class="val">{data['violation_id']}</td>
            </tr>
            <tr>
                <td class="label">Vehicle Registration No:</td>
                <td class="val"><strong>{data['vehicle_number']}</strong> ({data.get('make_model') or 'Vehicle'})</td>
            </tr>
            <tr>
                <td class="label">Registered Owner / Driver:</td>
                <td class="val">{data.get('driver_name') or 'N/A'} (License: {data.get('license_number') or 'N/A'})</td>
            </tr>
            <tr>
                <td class="label">Contact Phone:</td>
                <td class="val">{data.get('driver_phone') or 'N/A'}</td>
            </tr>
        </table>

        <div class="section-title">Violation Details & Location</div>
        <table class="info-table">
            <tr>
                <td class="label">Offense Committed:</td>
                <td class="val"><strong style="color: #c0392b;">{data['violation_type'].replace('_', ' ')}</strong></td>
            </tr>
            <tr>
                <td class="label">Location / Junction:</td>
                <td class="val">{data['location']}</td>
            </tr>
            <tr>
                <td class="label">Detected Speed:</td>
                <td class="val">{data.get('speed_detected', 0)} km/h (Permitted Limit: {data.get('speed_limit', 50)} km/h)</td>
            </tr>
            <tr>
                <td class="label">Date & Time of Offense:</td>
                <td class="val">{data.get('violation_time') or data['issue_date']}</td>
            </tr>
            <tr>
                <td class="label">Payment Due Date:</td>
                <td class="val"><strong>{data['due_date']}</strong></td>
            </tr>
        </table>

        <div class="fine-total-box">
            <div style="font-size: 13px; color: #718093; text-transform: uppercase;">Total Penalty Payable</div>
            <div class="amount">INR {data['amount']:,.2f}</div>
        </div>

        <div class="section-title">Photographic Evidence</div>
        <div class="evidence-box">
            {evidence_tag}
        </div>

        <div class="footer">
            Generated by Traffic Violation and Accident Alert Intelligent System. For inquiries or online settlement, visit the Traffic Police Portal.
        </div>
    </div>
</body>
</html>
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(out_path)
