"""
Sample Video Generator
Generates a realistic traffic surveillance .mp4 video with multiple vehicles,
lane movements, and an automated red-light violation scenario for testing.
"""
from pathlib import Path
import cv2
import numpy as np

from ..config import DATA_DIR


def generate_sample_traffic_video(output_path: Path = None, num_frames: int = 300) -> str:
    """
    Renders and saves a 30 FPS surveillance clip (10 seconds) demonstrating
    road traffic, car movements, signal changes, and a vehicle speeding through a red light.
    """
    out_file = output_path or (DATA_DIR / "sample_traffic.mp4")
    w, h = 720, 480
    fps = 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(out_file), fourcc, fps, (w, h))

    # Road coordinates
    road_left = 160
    road_right = 560
    center_x = (road_left + road_right) // 2
    stop_line_y = int(h * 0.55)

    # Vehicles in simulation
    vehicles = [
        {"id": 1, "type": "Car", "x": road_left + 40, "y": -80, "speed": 4, "color": (220, 100, 40), "plate": "TN07AB1234"},
        {"id": 2, "type": "Motorcycle", "x": center_x + 50, "y": -160, "speed": 5, "color": (50, 50, 240), "plate": "TN09CD5678"},
        {"id": 3, "type": "Truck", "x": road_left + 30, "y": -350, "speed": 3, "color": (40, 180, 220), "plate": "GJ01GH3456"},
        {"id": 4, "type": "Car", "x": center_x + 30, "y": -450, "speed": 8, "color": (180, 40, 200), "plate": "KA01EF9012"},  # Speeder
    ]

    for frame_idx in range(num_frames):
        # Frame canvas
        frame = np.full((h, w, 3), (35, 40, 45), dtype=np.uint8)

        # Traffic Signal timing: Green (0-120), Yellow (120-150), Red (150-300)
        if frame_idx < 120:
            signal = "GREEN"
        elif frame_idx < 150:
            signal = "YELLOW"
        else:
            signal = "RED"

        # Draw Asphalt Road
        cv2.rectangle(frame, (road_left, 0), (road_right, h), (48, 52, 58), -1)

        # Draw Center Yellow Dashed Line
        for y in range(0, h, 35):
            cv2.line(frame, (center_x, y), (center_x, y + 20), (0, 215, 255), 3)

        # Draw White Stop Line
        stop_col = (0, 0, 255) if signal == "RED" else (255, 255, 255)
        cv2.line(frame, (road_left, stop_line_y), (road_right, stop_line_y), stop_col, 5)

        # Draw Traffic Light Post (Top Right)
        sig_x, sig_y = road_right + 30, 40
        cv2.rectangle(frame, (sig_x, sig_y), (sig_x + 40, sig_y + 95), (20, 20, 20), -1)
        cv2.rectangle(frame, (sig_x, sig_y), (sig_x + 40, sig_y + 95), (100, 100, 100), 2)
        # Red
        r_col = (0, 0, 255) if signal == "RED" else (0, 0, 60)
        cv2.circle(frame, (sig_x + 20, sig_y + 20), 10, r_col, -1)
        # Yellow
        y_col = (0, 220, 255) if signal == "YELLOW" else (0, 70, 80)
        cv2.circle(frame, (sig_x + 20, sig_y + 48), 10, y_col, -1)
        # Green
        g_col = (0, 255, 0) if signal == "GREEN" else (0, 60, 0)
        cv2.circle(frame, (sig_x + 20, sig_y + 76), 10, g_col, -1)

        # Update and Draw Vehicles
        for v in vehicles:
            # Stop vehicle at red light unless it's the speeder/red-light runner (Vehicle #4)
            is_runner = (v["id"] == 4)
            if signal == "RED" and not is_runner and stop_line_y - 60 < v["y"] < stop_line_y:
                speed = 0  # Stopped at line
            else:
                speed = v["speed"]

            v["y"] += speed

            # Wrap around when off screen
            if v["y"] > h + 100:
                v["y"] = -100

            vy = v["y"]
            vx = v["x"]

            # Draw vehicle body
            if v["type"] == "Car":
                vw, vh = 50, 85
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), v["color"], -1)
                # Roof / windshield
                cv2.rectangle(frame, (vx + 6, vy + 20), (vx + vw - 6, vy + 45), (20, 20, 20), -1)
                # Headlights
                cv2.circle(frame, (vx + 10, vy + vh - 5), 4, (0, 255, 255), -1)
                cv2.circle(frame, (vx + vw - 10, vy + vh - 5), 4, (0, 255, 255), -1)
            elif v["type"] == "Motorcycle":
                vw, vh = 24, 60
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), v["color"], -1)
                cv2.circle(frame, (vx + vw // 2, vy + 25), 8, (20, 20, 20), -1)  # Helmet
            elif v["type"] == "Truck":
                vw, vh = 65, 120
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), v["color"], -1)
                cv2.rectangle(frame, (vx + 5, vy + vh - 35), (vx + vw - 5, vy + vh - 5), (30, 30, 30), -1)

            # Draw Plate Text on rear bumper
            cv2.rectangle(frame, (vx + 4, vy + 6), (vx + vw - 4, vy + 20), (255, 255, 255), -1)
            cv2.putText(frame, v["plate"][:6], (vx + 6, vy + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1)

        out.write(frame)

    out.release()
    print(f"Sample traffic video generated at: {out_file}")
    return str(out_file)


if __name__ == "__main__":
    generate_sample_traffic_video()
