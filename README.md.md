# Accuratur AI — Industrial IoT Edge Telemetry & Machine Learning Anomaly Detection Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-4.7%2B-black.svg)](https://socket.io/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4%2B-orange.svg)](https://scikit-learn.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4%2B-FF6384.svg)](https://www.chartjs.org/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4%2B-38B2AC.svg)](https://tailwindcss.com/)

A full-stack industrial IoT telemetry, mathematical calibration transfer, Random Forest predictive maintenance, and transient anomaly filtering platform. Accuratur AI connects directly to physical microcontrollers (Arduino Uno / FTDI USB Serial) at 4 Hz, delivers high-definition telemetry waveforms with sharp vertices and dynamic micro-zoom (0.01 resolution), and runs a 4-class Random Forest model that isolates transient anomaly fluctuations (optical flashes on photoresistors, thermal drafts, ADC noise) from genuine hardware degradation.

---

## Key Features

1. **Physical Hardware Connectivity & Serial Gateway**
   - Direct USB FTDI / CH340 serial communication (`COM11` @ 9600 baud, 8-N-1).
   - Resilient Node.js gateway with automated reconnection, non-blocking packet parsing, and real-time Socket.IO broadcasting.

2. **Interactive Sensor Selector Bar & Dedicated Hub**
   - Decluttered user interface with 7 individual interactive sensor buttons:
     - `H01` (Live Capacitive Humidity — DHT22)
     - `LDR` (Live Optical Photoresistor — Pin A0)
     - `T01` (Primary Temperature — RTD Class-A)
     - `T02` (Secondary Temperature — RTD Class-B)
     - `H02` (Secondary Humidity — SHT31)
     - `C01` (Primary CO₂ Gas — NDIR Chamber)
     - `C02` (Secondary CO₂ Gas — NDIR Chamber)
   - Clicking any sensor button reactively shifts the entire hub to that sensor across **4 core quadrants**:
     - **Live Telemetry & Dynamics**: Raw ADC / engineering value, Calibrated Output, Instantaneous Delta ($\Delta$), and Noise Jitter ($\sigma$).
     - **Calibration Model & Metrology**: Regression Transfer equation ($Cal = m \cdot Raw + b$), Learned Gain, Learned Offset, and Bayesian Fusion Weight.
     - **Lifecycle & MTBF Tracker**: Commissioning Date (**Today / Day 1** for H01 & LDR), Days Active, Theoretical Lifespan (hrs/years), Remaining Service Days, and Calibration Audit Countdown.
     - **Accuracy & Precision Metrology**: Calibration Accuracy %, Repeatability Precision %, and Gaussian Health %.

3. **4-Class Random Forest Machine Learning Model**
   - Trained on `temperature_ldr_sensor_anomaly_dataset.csv` (2,800 records across 7 sensors).
   - Reaches **99.29% test accuracy** and **100% precision & recall** for anomaly detection.
   - **Transient Anomaly Fluctuation Filtration**: When a sudden non-degradation spike occurs (e.g. flashlight beam on LDR or thermal breath puff on temperature probe), the system classifies the event as `TRANSIENT_ANOMALY`, designates the action as **`ignore`**, keeps failure risk low ($4.2\%$), and displays an **`⚡ ANOMALY (IGNORED)`** indicator to prevent false alarms.

4. **High-Definition Waveform Engine**
   - **Sharp Peaks Mode (`tension: 0`)**: Straight linear vectors with miter vertex joins for acute, angular peak rendering.
   - **Dynamic Micro-Scale Zoom**: Dynamic auto-clamping with $\pm 0.04$ padding, allowing sub-decimal variations ($0.02 - 0.05$) to expand across the full 380px chart height.
   - **Digital Step & Smooth Modes**: Toggle square pulse response or cubic Bézier curves on demand.

5. **Direct Dataset Distribution**
   - Host and distribute `temperature_ldr_sensor_anomaly_dataset.csv` directly through the web UI and REST endpoint (`/api/dataset/temperature_ldr_sensor_anomaly_dataset.csv`).

---

## System Architecture

```text
┌─────────────────────────────────┐
│     Arduino Uno Hardware        │  (Pins A0, D2 / FTDI USB Serial)
│   (edge_module_firmware.ino)    │  Packet: [LIVE TX] ID: 1 | RawH: 52.40 | CalH: 51.88 | LDR: 120 | Status: ONLINE
└────────────────┬────────────────┘
                 │ USB Serial @ 9600 Baud (COM11)
                 ▼
┌─────────────────────────────────┐
│     Node.js Gateway Server      │  (server.js - Port 3000)
│     (Express + Socket.IO)       │  • SerialPort auto-reconnect & packet stream
└────────────────┬────────────────┘  • Serves Public Dashboard & Dataset Download
                 │
                 ├──────────────────────────────────────────────┐
                 ▼                                              ▼
┌─────────────────────────────────┐            ┌──────────────────────────────────┐
│   Live Web Dashboard UI         │            │      FastAPI AI Backend          │
│    (public/index.html)          │            │      (backend/main.py)           │
│  • Interactive Sensor Selector  │            │  • Regression Transfer Model     │
│  • Dedicated 4-Quadrant Hub     │            │  • 4-Class Random Forest Model   │
│  • Chart.js Sharp Peak Waveform │            │    (healthy/warning/unhealthy/   │
│  • AI Prognostics & Anomaly Sim │            │     anomaly)                     │
└─────────────────────────────────┘            └────────────────┬─────────────────┘
                                                                │
                                                                ▼
                                               ┌──────────────────────────────────┐
                                               │      Supabase Cloud DB           │
                                               │      (PostgreSQL Storage)        │
                                               └──────────────────────────────────┘
```

---

## Repository Structure

```text
HackDays/
├── .gitignore                                 # Git rules (excludes virtualenvs, node_modules, .env)
├── README.md                                  # Complete documentation & developer guide
├── package.json                               # Node.js dependencies (Express, Socket.IO, SerialPort)
├── package-lock.json                          # Pinned npm dependencies
├── server.js                                  # Node.js gateway (SerialPort, Socket.IO, Dataset download)
├── start.bat                                  # Windows double-click service launcher
├── calibration_slope_dataset.csv              # Initial regression slope training dataset
├── sensor_calibration_data.csv                # Baseline multi-sensor empirical dataset
├── temperature_ldr_sensor_anomaly_dataset.csv # 4-class multi-sensor anomaly dataset (2,800 rows)
├── arduino/
│   └── edge_module_firmware.ino               # Arduino Uno C++ sketch streaming real-time telemetry
├── backend/
│   ├── .env.example                           # Supabase environment variable template
│   ├── calibration.py                         # Baseline Gaussian metrics and regression calibration
│   ├── calibration_slope_dataset.csv          # Backend mirror of calibration dataset
│   ├── dashboard.py                           # Streamlit alternative monitoring view
│   ├── generate_anomaly_dataset.py            # Synthetic dataset generator for transient anomalies
│   ├── main.py                                # FastAPI application (endpoints, inference, download)
│   ├── ml_service.py                          # SensorFailurePredictor Random Forest inference service
│   ├── requirements.txt                       # Python dependencies (scikit-learn, fastapi, pandas, etc.)
│   ├── schemas.py                             # Pydantic schemas for REST API validation
│   ├── supabase_client.py                     # Supabase client wrapper
│   ├── temperature_ldr_sensor_anomaly_dataset.csv # Backend mirror of anomaly dataset
│   ├── train_ml_model.py                      # 4-class Random Forest training & evaluation pipeline
│   ├── models/
│   │   ├── calibration_rf_model.joblib        # Serialized trained scikit-learn pipeline
│   │   └── model_metadata.json                # Model accuracy, F1-score, and feature importances
│   └── static/
│       └── index.html                         # FastAPI standalone static UI
└── public/
    └── index.html                             # Main production dashboard with single hub & selector
```

---

## Machine Learning & Anomaly Detection Pipeline

### 1. Dataset: `temperature_ldr_sensor_anomaly_dataset.csv`
- **Total Records**: 2,800 rows (400 per sensor)
- **Sensor Types**: Temperature (`T01`, `T02`), Light (`LDR`), Humidity (`H01`, `H02`), CO₂ (`C01`, `C02`)
- **Classes**:
  - `healthy` (1,780 samples / 63.6%): Nominal operation within tolerance.
  - `warning` (420 samples / 15.0%): Incipient progressive calibration slope divergence ($\approx 7 - 12\%$).
  - `unhealthy` (420 samples / 15.0%): Severe slope divergence / hardware failure ($> 18\%$).
  - `anomaly` (180 samples / 6.4%): Transient non-degradation fluctuations (momentary optical flashes, thermal drafts, ADC spikes).

### 2. Feature Engineering
- `raw_value`: Uncorrected sensor measurement.
- `slope` ($m$): Empirical response slope from regression model.
- `intercept` ($b$): Baseline offset.
- `slope_deviation`: Absolute departure from ideal slope ($|m - 1.0|$).
- `relative_error_pct`: Relative departure against reference standard ($\frac{|\text{raw} - \text{ref}|}{\text{ref}} \times 100$).
- `rolling_slope_mean`: Rolling 5-sample mean of slope.
- `rolling_slope_std`: Rolling 5-sample volatility of slope ($\sigma$).
- `rolling_drift_mean`: Rolling 5-sample mean of drift magnitude.
- `slope_rate_of_change`: Instantaneous rate of change of slope ($\Delta m$).
- `spike_ratio`: Ratio of current drift to background rolling drift ($\frac{\text{drift}}{\text{rolling\_drift\_mean} + 10^{-3}}$).

### 3. Model Performance (Random Forest Classifier)

```text
5-Fold CV Macro F1: 0.9915 (+/- 0.0039)
Test Accuracy:      99.29%
Test Macro F1:      99.25%

Classification Report:
               precision    recall  f1-score   support
     anomaly       1.00      1.00      1.00        36
     healthy       0.99      1.00      0.99       356
   unhealthy       1.00      1.00      1.00        84
     warning       1.00      0.95      0.98        84
```

### 4. Anomaly vs. Failure Decision Matrix

| Condition | Slope Deviation ($|m-1|$) | Drift Magnitude | Spike Ratio | Risk Level | Action | System Response |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`healthy`** | $< 0.02$ | Low | $\approx 1.0$ | `LOW_RISK` | `monitor` | Normal operation ($< 20\%$ risk) |
| **`warning`** | $0.05 - 0.12$ | Persistent moderate | $\approx 1.0$ | `EARLY_DRIFT_WARNING` | `schedule_inspection` | Early warning alert ($20 - 74\%$ risk) |
| **`unhealthy`** | $> 0.18$ | Persistent severe | $\approx 1.0$ | `CRITICAL_FAILURE_IMMINENT` | `replace_sensor` | Critical failure alarm ($\ge 75\%$ risk) |
| **`anomaly`** | $< 0.03$ (Nominal) | Sudden spike | $> 3.0$ | `TRANSIENT_ANOMALY` | `ignore` | **Filtered out / Ignored** ($4.2\%$ risk) |

---

## API Documentation

### 1. Download Dataset
- **Endpoint**: `GET /api/dataset/temperature_ldr_sensor_anomaly_dataset.csv`
- **Description**: Downloads the 435 KB CSV dataset containing 2,800 labeled rows.
- **Response**: `text/csv` attachment.

### 2. Predict Failure & Anomaly
- **Endpoint**: `POST /api/ml/predict-failure` (via Node proxy) or `POST /predict-failure` (FastAPI)
- **Request Body**:
  ```json
  {
    "sensor_id": "LDR",
    "raw_value": 880.0,
    "gain": 1.000,
    "offset": 0.0,
    "sensor_type": "Light_LDR"
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "prediction": {
      "sensor_id": "LDR",
      "raw_value": 880.0,
      "calibrated_value": 880.0,
      "slope": 1.0,
      "slope_deviation": 0.0,
      "ml_prediction": {
        "predicted_condition": "anomaly",
        "is_anomaly": true,
        "action": "ignore",
        "failure_risk_pct": 4.2,
        "risk_level": "TRANSIENT_ANOMALY",
        "class_probabilities": {
          "anomaly": 0.9563,
          "healthy": 0.0353,
          "unhealthy": 0.0,
          "warning": 0.0084
        },
        "pattern_title": "Transient Anomaly Fluctuation (Ignored)",
        "recommendation": "Transient anomaly fluctuation identified and ignored. Normal operation."
      }
    }
  }
  ```

### 3. Model Metadata & Performance
- **Endpoint**: `GET /api/ml/model-info`
- **Response**: Returns algorithm name, feature importances, cross-validation metrics, and confusion matrix.

### 4. Serial Port Telemetry Status
- **Endpoint**: `GET /api/serial/status`
- **Response**:
  ```json
  {
    "connected": true,
    "port": "COM11",
    "secondsSinceLastPacket": 0.4,
    "packetCount": 4210
  }
  ```

---

## Quickstart & Installation

### 1. Prerequisites
- **Node.js**: v18.0.0 or higher
- **Python**: v3.10 or higher
- **Arduino IDE**: (Optional, to upload firmware to Arduino Uno)

### 2. Backend Setup (FastAPI & ML)
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate anomaly dataset and train Random Forest model
python generate_anomaly_dataset.py
python train_ml_model.py

# 5. Configure environment variables
copy .env.example .env

# 6. Start the FastAPI server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Node.js Gateway Setup
```bash
# 1. Navigate to root directory
cd ..

# 2. Install Node.js dependencies
npm install

# 3. Start the gateway server
node server.js
```

### 4. Access the Platform
- **Dashboard UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Direct Dataset Download**: [http://localhost:3000/api/dataset/temperature_ldr_sensor_anomaly_dataset.csv](http://localhost:3000/api/dataset/temperature_ldr_sensor_anomaly_dataset.csv)

---

## Arduino Hardware Setup

1. Open `arduino/edge_module_firmware.ino` in the Arduino IDE.
2. Connect an Arduino Uno with:
   - **DHT22 Humidity / Temperature**: Data Pin -> `D2`
   - **LDR Photocell**: Signal Pin -> `A0` (with 10k$\Omega$ pull-down resistor to GND)
3. Select Board: **Arduino Uno**, Port: **COM11** (or your platform's serial port).
4. Upload the sketch. The microcontroller will begin streaming 4 Hz packets.

---

## License & Attribution
Developed for HackDays 2026. Built with high-performance linear regression, Random Forest machine learning, and reactive real-time edge telemetry.
