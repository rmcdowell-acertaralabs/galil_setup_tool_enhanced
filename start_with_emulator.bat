@echo off
REM Start Galil Setup Tool with Emulator
REM This script starts both the emulator server and the GUI application

echo Starting DMC-4143 Emulator Server...
start "Galil Emulator Server" /min python dmc4143_emulator.py --server

REM Wait a moment for the server to start
timeout /t 2 /nobreak >nul

echo Starting Galil Setup Tool GUI...
python main.py

REM When GUI closes, optionally stop the emulator server
REM (Uncomment the line below if you want to stop the server when GUI closes)
REM taskkill /FI "WINDOWTITLE eq Galil Emulator Server*" /F >nul 2>&1

