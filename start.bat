@echo off
title Accurator AI & Arduino Telemetry Launcher
echo ========================================================
echo  Starting Accurator AI Backend and Arduino Telemetry
echo ========================================================

REM 1. Start FastAPI Backend on port 8000
echo Starting FastAPI Backend at http://127.0.0.1:8000 ...
start "Accurator AI Backend" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM 2. Start Node.js Arduino Serial Telemetry Gateway on port 3000
echo Starting Node.js Telemetry Gateway at http://localhost:3000 ...
start "Arduino Telemetry Dashboard" cmd /k "cd /d ""%~dp0"" && ""C:\Program Files\nodejs\node.exe"" server.js"

echo.
echo Both servers started!
echo - Edge Module Telemetry Dashboard: http://localhost:3000
echo - Accurator AI Backend & API:      http://127.0.0.1:8000
echo - Swagger Docs:                    http://127.0.0.1:8000/docs
echo ========================================================
pause