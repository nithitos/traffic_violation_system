"""
Evidence Generator - Generates annotated violation snapshots with metadata watermark
"""
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from ..config import EVIDENCE_DIR, SIGNAL_RED

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class EvidenceMaker:
    """Generates official watermarked evidence snapshots for traffic violations."""

    @staticmethod
    def generate_evidence_snapshot(
        violation_id: str,
        violation_type: str,
        vehicle_number: str,
        vehicle_type: str,
        speed: float,
        speed_limit: float,
        location: str,
        camera_id: str,
        signal_status: str,
        timestamp_str: Optional[str] = None,
    ) -> str:
        """Draw and persist violation evidence image."""
        timestamp = timestamp_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"violation_{violation_id}.png"
        filepath = EVIDENCE_DIR / filename

        if not PIL_AVAILABLE:
            # Fallback descriptor file
            txt_path = filepath.with_suffix(".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"EVIDENCE REPORT: {violation_id}\n")
                f.write(f"Offense: {violation_type}\n")
                f.write(f"Vehicle: {vehicle_number} ({vehicle_type})\n")
                f.write(f"Speed: {speed} km/h (Limit: {speed_limit} km/h)\n")
                f.write(f"Location: {location} [Camera: {camera_id}]\n")
                f.write(f"Signal: {signal_status} | Timestamp: {timestamp}\n")
            return str(txt_path)

        # Image Dimensions
        w, h = 800, 520
        img = Image.new("RGB", (w, h), color=(30, 39, 46))
        draw = ImageDraw.Draw(img)

        # Draw Road Simulation
        draw.rectangle([0, 90, w, h - 50], fill=(44, 62, 80))
        # Center Line
        for y in range(100, h - 50, 45):
            draw.line([(w // 2, y), (w // 2, y + 25)], fill=(241, 196, 15), width=4)

        # Stop line
        draw.line([(0, 380), (w, 380)], fill=(236, 240, 241), width=6)

        # Draw Traffic Signal on Right
        sig_x, sig_y = w - 85, 105
        draw.rectangle([sig_x, sig_y, sig_x + 55, sig_y + 120], fill=(20, 20, 20), outline=(189, 195, 199), width=2)
        # Red light highlighted if signal is RED
        red_c = (231, 76, 60) if signal_status == "RED" else (80, 20, 20)
        yel_c = (241, 196, 15) if signal_status == "YELLOW" else (80, 70, 15)
        grn_c = (46, 204, 113) if signal_status == "GREEN" else (20, 70, 30)
        draw.ellipse([sig_x + 15, sig_y + 10, sig_x + 40, sig_y + 35], fill=red_c)
        draw.ellipse([sig_x + 15, sig_y + 48, sig_x + 40, sig_y + 73], fill=yel_c)
        draw.ellipse([sig_x + 15, sig_y + 85, sig_x + 40, sig_y + 110], fill=grn_c)

        # Draw Target Vehicle with RED Bounding Box
        vx, vy, vw, vh = 280, 240, 240, 160
        draw.rectangle([vx, vy, vx + vw, vy + vh], outline=(231, 76, 60), width=4)
        draw.rectangle([vx + 10, vy + 10, vx + vw - 10, vy + vh - 10], fill=(52, 73, 94))

        # License Plate tag on vehicle
        draw.rectangle([vx + 25, vy + 110, vx + vw - 25, vy + 145], fill=(241, 196, 15), outline=(0, 0, 0), width=2)
        draw.text((vx + 45, vy + 120), vehicle_number, fill=(0, 0, 0))

        # Red Banner for Violation
        draw.rectangle([0, 0, w, 80], fill=(192, 57, 43))
        draw.text((20, 12), "EVIDENCE SNAPSHOT - TRAFFIC VIOLATION DETECTED", fill=(255, 255, 255))
        draw.text((20, 45), f"Offense: {violation_type} | ID: {violation_id}", fill=(241, 196, 15))

        # Bottom Metadata Watermark
        draw.rectangle([0, h - 50, w, h], fill=(20, 20, 20))
        meta_str = f"Loc: {location} | Cam: {camera_id} | Speed: {speed} km/h (Limit: {speed_limit} km/h) | {timestamp}"
        draw.text((20, h - 35), meta_str, fill=(236, 240, 241))

        img.save(str(filepath), "PNG")
        return str(filepath)
