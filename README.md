# Intelligent Traffic Violation & Accident Alert System

A Python-based intelligent system for real-time traffic monitoring, violation detection, and automated enforcement.

Based on the project roadmap and architecture diagram, this repository contains the complete implementation of the first **4 core modules**:

1. **Module 1: Inputs & Data Management** (Drivers, Vehicles, Traffic Cameras, GPS & Accident Sensor Telemetry)
2. **Module 2: User Authentication & Role-Based Access Control (RBAC)** (Admin, Traffic Officer, Control Room Operator)
3. **Module 3: Traffic Monitoring & Violation Detection Engine** (Red Light, Speeding, Wrong-Way, Helmet/Seatbelt, Illegal Parking & Socket Streaming)
4. **Module 4: Violation Processing & Reports** (E-Challans, Fine Matrix, Pandas Analytics, CSV & Printable Receipts)
5. **Integrated Tkinter Desktop Application** (Modern graphical control center with live simulation canvas)

---

## 🛠️ Python Tech Stack Mapping

| Tech Stack Element | Implementation in Project |
| :--- | :--- |
| **Tkinter GUI** | Desktop Control Center with Live Canvas, Real-Time Alerts, E-Challan Manager, and Reports (`gui/`) |
| **Socket Programming** | TCP Client-Server architecture (`127.0.0.1:9999`) streaming real-time telemetry from edge cameras (`networking/`) |
| **Functional Programming** | Filter pipelines (`filter`), transforms (`map`), lambdas, and aggregations (`reduce`) (`detection/functional_ops.py`) |
| **Pandas / NumPy** | Statistical aggregations, violation distributions, peak hours, and CSV exports (`processing/report_service.py`) |
| **Multithreading / Concurrency** | Daemon socket server and non-blocking Tkinter animation loop (`threading`) |
| **Database** | SQLite engine with foreign keys, relational queries, and thread-local connections (`database/db_manager.py`) |

---

## 📂 Project Directory Structure

```
traffic_violation_system/
├── config.py                 # System thresholds, paths, fine matrix, socket port
├── main.py                   # Main launcher for Tkinter desktop application
├── test_all.py               # Master test runner executing all 4 module suites
├── test_module1.py           # Module 1 tests (Data collection, validation, sensor math)
├── test_module2.py           # Module 2 tests (Authentication, password hashing, RBAC)
├── test_module3.py           # Module 3 tests (5 violation rules, evidence, socket broadcast)
├── test_module4.py           # Module 4 tests (E-Challans, settlement, Pandas reports, receipts)
│
├── auth/                     # MODULE 2: Authentication & RBAC
│   ├── auth_service.py       # Salted SHA-256 hashing, UserSession, permissions
│   └── exceptions.py         # Auth exception hierarchy
│
├── database/                 # DATABASE LAYER
│   ├── db_manager.py         # SQLite connection manager, schemas, CRUD
│   └── seed_data.py          # Preloaded drivers, vehicles, cameras, system roles
│
├── vision/                   # COMPUTER VISION & ANPR (Option 3 AI Upgrade)
│   ├── video_processor.py    # Vehicle tracking, speed calculation, virtual lines
│   ├── plate_reader.py       # Morphological plate localization & character OCR
│   └── sample_video_generator.py # Generates surveillance test video (.mp4)
│
├── detection/                # MODULE 3: Violation Detection
│   ├── detector.py           # Rule engine for 5 violation offenses
│   ├── evidence_maker.py     # Image generator stamping official red warning banner
│   ├── functional_ops.py     # Functional programming pipelines (filter, map, lambda)
│   └── violation_types.py    # Enums and ViolationEvent dataclass
│
├── inputs/                   # MODULE 1: Inputs & Data Collection
│   ├── data_collector.py     # Unified collector for Drivers, Vehicles, Cameras, GPS, Sensors
│   ├── sensor_simulator.py   # Telemetry generator (cruise, harsh braking, crash, rollover)
│   ├── camera_simulator.py   # Synthetic video frames and junction snapshots
│   └── csv_loader.py         # Bulk import from CSV/JSON
│
├── networking/               # REAL-TIME SOCKET STREAMING
│   ├── socket_server.py      # TCP server receiving telemetry & pushing live alerts
│   └── camera_client.py      # Edge camera client transmitting event packets
│
├── processing/               # MODULE 4: Violation Processing & Reports
│   ├── challan_service.py    # Automated E-Challan generation & payment settlement
│   └── report_service.py     # Pandas analytics, CSV exports, printable HTML receipts
│
├── gui/                      # INTEGRATED TKINTER DESKTOP APPLICATION
│   ├── app.py                # View coordinator (Login -> Dashboard) & socket daemon
│   ├── login_window.py       # Authentication dialog with quick demo buttons
│   └── dashboard.py          # Control center: Live Canvas, Alerts, Challans, Reports
│
├── data/                     # SQLite database file (traffic_system.db)
├── evidence/                 # Saved violation evidence snapshots (.png)
└── reports/                  # Generated CSV exports and printable HTML receipts
```

---

## 🚀 How to Run

### 1. Launch the Web Dashboard in Your Browser (Recommended)
Open a terminal in `traffic_violation_system` and run:
```bash
python run_web.py
```
This starts the local web server and automatically opens **`http://127.0.0.1:5000`** in your default web browser!

### 2. Launch the Tkinter Desktop Application
If you prefer the native desktop GUI window:
```bash
python main.py
```

### 2. Demo User Credentials (Role-Based Access)
The login screen features quick 1-click buttons, or you can sign in manually:

| Role | Username | Password | Privileges |
| :--- | :--- | :--- | :--- |
| **Project Administrator** | `admin` | `admin123` | Full access (Manage users, view feeds, approve challans, export reports) |
| **Traffic Officer** | `officer1` | `officer123` | Monitor feeds, review violations, approve E-Challans, print receipts |
| **Control Room Operator**| `operator1` | `operator123` | Monitor live junction feeds, trigger alerts (cannot issue fines) |

---

## 🧪 Running Automated Tests

You can run individual module tests or the master test suite:

```bash
# Run all 4 modules test suite:
python test_all.py

# Or test individual modules:
python test_module1.py    # Inputs & Data Collection
python test_module2.py    # Authentication & RBAC
python test_module3.py    # Violation Detection & Socket Streaming
python test_module4.py    # E-Challan Processing & Reports
```

---

## 📋 Features Implemented in Modules 1 - 4

### Module 1: Inputs & Data Collection
- **Driver Profiles**: Driver ID, Full Name, License Number, Category (LMV/MCWG/HMV), Phone, Email.
- **Vehicle Registry**: Vehicle Number, Type (Car/Bike/Truck/Bus/Auto), Make/Model, Color, Owner ID.
- **Traffic Cameras**: Junction coordinates, speed limits, active traffic signal states (RED, YELLOW, GREEN).
- **GPS Telemetry**: Real-time coordinates, speed (km/h), heading, and altitude tracking.
- **Accident Sensors**: 3-axis accelerometer G-force vector calculation, tilt angle (rollover detection), airbag status, and impact severity classification (`NORMAL`, `HARSH_BRAKING`, `CRITICAL_ACCIDENT`).

### Module 2: User Authentication & RBAC
- Salted SHA-256 password hashing.
- Role-based authorization (`ADMIN`, `TRAFFIC_OFFICER`, `CONTROL_ROOM_OPERATOR`).
- Exception handling for wrong password, missing account, and unauthorized action attempts.

### Module 3: Traffic Monitoring & Violation Detection
- **5 Automated Offense Detectors**:
  1. **Red Signal Violation**: Moving vehicle crossing stop-line on RED signal.
  2. **Speed Violation**: Exceeding junction limit with tiered penalty multiplier for extreme speed.
  3. **Wrong-Side Driving**: Opposite lane flow vector detection.
  4. **No Helmet / No Seatbelt**: Category-aware safety gear checks (Helmet for 2-wheelers, Seatbelt for cars).
  5. **Illegal Parking**: Dwell time detection in designated No-Parking zones.
- **Evidence Maker**: Generates official annotated snapshot with license plate tag, metadata banner, and red violation border.
- **Socket Client-Server**: Non-blocking TCP socket server streaming live telemetry to dashboards.

### Module 4: Violation Processing & Reports
- **Automated E-Challans**: Unique ID generation (`ECH-YYYYMMDD-XXXX`), due dates (+15 days), fine matrix.
- **Payment Reconciliation**: Settle challans with transaction references (UPI/Netbanking).
- **Pandas / NumPy Analytics**: High-level KPIs, offense distribution breakdown, peak hours analysis.
- **Exports**: 1-click CSV exports for Violations and Challans.
- **Printable Receipts**: Styled official HTML/PDF receipts with embedded photographic evidence snapshots.


## ☁️ Deploy to Railway

This project includes Railway deployment configuration.

### 1. Push to GitHub

From the project root:

```bash
git init
git add .
git commit -m "Prepare project for Railway deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

### 2. Deploy on Railway

1. Create a new Railway project.
2. Choose **Deploy from GitHub Repo**.
3. Select this repository.
4. Railway will detect the Python project and use:
   `python -m traffic_violation_system.railway_start`
5. After deployment, open the generated Railway domain.

Railway provides the `PORT` environment variable automatically. The production server binds to `0.0.0.0`.

### Important: SQLite persistence

The app currently uses SQLite at `data/traffic_system.db`. Railway containers have ephemeral storage, so database changes can be lost when the service is redeployed/restarted. For a real production deployment, attach a Railway Volume or migrate the database to PostgreSQL.

### Important: AI video processing

The service starts the sample video processor when the web service starts. The sample video is included in the repository. YOLOv8 is installed when using the supplied `requirements.txt`; the first model load may download `yolov8n.pt`.
