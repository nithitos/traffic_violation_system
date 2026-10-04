"""
Telemetry and Sensor Simulator
Generates realistic GPS movement, sensor readings (normal driving, sudden brake, crash, rollover),
and traffic signal transitions for live testing and monitoring.
"""
import random
import time
from datetime import datetime
from typing import Dict, Any, Generator, Tuple
from ..models.telemetry import GPSData, SensorData, ImpactSeverity, VehicleStatus
from ..config import SIGNAL_RED, SIGNAL_YELLOW, SIGNAL_GREEN


class SensorSimulator:
    """Simulates vehicle telemetry sensors and GPS coordinates."""

    def __init__(self, vehicle_number: str = "TN-07-AB-1234"):
        self.vehicle_number = vehicle_number
        # Base coordinate: Chennai City Center (Anna Salai)
        self.current_lat = 13.0522
        self.current_lon = 80.2503
        self.current_speed = 42.0
        self.heading = 90.0

    def generate_normal_telemetry(self) -> Tuple[GPSData, SensorData]:
        """Generate typical cruise-driving sensor telemetry."""
        # Subtle drift in coordinates
        self.current_lat += random.uniform(-0.0002, 0.0002)
        self.current_lon += random.uniform(-0.0002, 0.0002)
        self.current_speed = max(20.0, min(65.0, self.current_speed + random.uniform(-3, 3)))

        gps = GPSData(
            vehicle_number=self.vehicle_number,
            latitude=round(self.current_lat, 6),
            longitude=round(self.current_lon, 6),
            speed_kmh=round(self.current_speed, 1),
            heading_deg=round(self.heading, 1),
            altitude_m=14.5,
            location_name="Anna Salai, Arterial Road",
            timestamp=datetime.now().isoformat(),
        )

        sensor = SensorData(
            vehicle_number=self.vehicle_number,
            accel_x_g=round(random.uniform(-0.1, 0.1), 2),
            accel_y_g=round(random.uniform(-0.2, 0.2), 2),
            accel_z_g=round(1.0 + random.uniform(-0.05, 0.05), 2),
            tilt_pitch_deg=round(random.uniform(-1.0, 1.0), 1),
            tilt_roll_deg=round(random.uniform(-1.5, 1.5), 1),
            airbag_deployed=False,
            seatbelt_buckled=True,
            engine_running=True,
            timestamp=datetime.now().isoformat(),
        )
        return gps, sensor

    def generate_overspeeding_telemetry(self, speed_kmh: float = 88.5) -> Tuple[GPSData, SensorData]:
        """Generate excessive speed telemetry."""
        gps, sensor = self.generate_normal_telemetry()
        gps.speed_kmh = speed_kmh
        return gps, sensor

    def generate_harsh_braking_telemetry(self) -> Tuple[GPSData, SensorData]:
        """Generate high negative deceleration telemetry."""
        gps, sensor = self.generate_normal_telemetry()
        sensor.accel_y_g = -1.9  # Harsh deceleration
        gps.speed_kmh = max(5.0, gps.speed_kmh - 25.0)
        return gps, sensor

    def generate_collision_telemetry(self) -> Tuple[GPSData, SensorData]:
        """Generate high-G crash collision with deployed airbag."""
        gps, _ = self.generate_normal_telemetry()
        gps.speed_kmh = 0.0  # Instant halt

        sensor = SensorData(
            vehicle_number=self.vehicle_number,
            accel_x_g=round(random.uniform(2.5, 4.0), 2),
            accel_y_g=round(random.uniform(-7.5, -5.5), 2),  # Severe front impact
            accel_z_g=round(random.uniform(1.8, 3.2), 2),
            tilt_pitch_deg=-12.5,
            tilt_roll_deg=8.0,
            airbag_deployed=True,
            seatbelt_buckled=True,
            engine_running=False,
            timestamp=datetime.now().isoformat(),
        )
        return gps, sensor

    def generate_rollover_telemetry(self) -> Tuple[GPSData, SensorData]:
        """Generate vehicle rollover event (tilt angle > 45°)."""
        gps, _ = self.generate_normal_telemetry()
        gps.speed_kmh = 0.0

        sensor = SensorData(
            vehicle_number=self.vehicle_number,
            accel_x_g=3.8,
            accel_y_g=-2.2,
            accel_z_g=0.2,
            tilt_pitch_deg=18.0,
            tilt_roll_deg=68.5,  # Exceeds 45° threshold
            airbag_deployed=True,
            seatbelt_buckled=True,
            engine_running=False,
            timestamp=datetime.now().isoformat(),
        )
        return gps, sensor


class TrafficSignalSimulator:
    """Cycles traffic lights automatically (Green -> Yellow -> Red -> Green)."""

    def __init__(self, green_sec: int = 10, yellow_sec: int = 3, red_sec: int = 8):
        self.durations = {
            SIGNAL_GREEN: green_sec,
            SIGNAL_YELLOW: yellow_sec,
            SIGNAL_RED: red_sec,
        }
        self.current_state = SIGNAL_GREEN
        self.last_switch = time.time()

    def tick(self) -> str:
        """Check if signal needs to transition based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_switch
        if elapsed >= self.durations[self.current_state]:
            if self.current_state == SIGNAL_GREEN:
                self.current_state = SIGNAL_YELLOW
            elif self.current_state == SIGNAL_YELLOW:
                self.current_state = SIGNAL_RED
            else:
                self.current_state = SIGNAL_GREEN
            self.last_switch = now
        return self.current_state

    def force_state(self, state: str) -> None:
        if state in [SIGNAL_GREEN, SIGNAL_YELLOW, SIGNAL_RED]:
            self.current_state = state
            self.last_switch = time.time()
