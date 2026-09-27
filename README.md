# Accurator AI & Edge Module Telemetry System

A full-stack industrial IoT telemetry, automatic calibration, and sensor health monitoring platform. Connects directly to physical hardware (Arduino Uno / FTDI USB Serial), visualizes real-time high-definition waveforms with micro-scale dynamic zoom, computes individual sensor performance metrics, and synchronizes calibrated data with the Accurator AI FastAPI backend and Supabase Cloud.

---

## System Architecture
┌──────────────────────────┐
│  Arduino Uno Hardware    │  (Pins A0 / D2, FTDI USB Serial)
│  (edge_module_firmware)  │  Packet: [LIVE TX] ID: 1 | RawH: 72.10 | CalH: 73.60 | LDR: 94 | Status: ONLINE
└────────────┬─────────────┘
             │  USB Serial @ 9600 Baud (COM11)
             ▼
┌──────────────────────────┐
│  Node.js Serial Gateway  │  (server.js - Port 3000)
│  (Express + Socket.IO)   │  • Reads COM11 with ReadlineParser
└────────────┬─────────────┘  • Emits 'sensor-data' to web clients
             │
             ├─────────────────────────────────────────┐
             ▼                                         ▼
┌──────────────────────────┐               ┌──────────────────────────┐
│  Live Web Dashboard UI   │               │   FastAPI AI Backend     │
│   (public/index.html)    │               │    (backend/main.py)     │
│  • Chart.js Sharp Peaks  │               │ • Automatic Calibration  │
│  • Dynamic Micro-Zoom    │               │ • Gaussian Z-Score       │
│  • Sensor Performances   │               │ • Drift & Anomaly Score  │
│  • Live Serial Log       │               └─────────────┬────────────┘
└──────────────────────────]                             │
                                                         ▼
                                           ┌──────────────────────────┐
                                           │    Supabase Cloud DB     │
                                           │   (PostgreSQL Table)     │
                                           └──────────────────────────┘

## Hardware Specification & Serial Protocol
- Microcontroller: Arduino Uno (detected on COM11)
- Baud Rate: 9600
- Packet Structure:
  [LIVE TX] ID: <PacketID> | RawH: <Raw_Humidity> | CalH: <Cal_Humidity> | LDR: <Light_ADC> | Status: ONLINE\r\n

---

## Getting Started
1. Run everything with one click:
   Double-click `start.bat` in the project root.
2. Access the Live Dashboard:
   http://localhost:3000
3. Access the FastAPI Backend:
   http://127.0.0.1:8000
