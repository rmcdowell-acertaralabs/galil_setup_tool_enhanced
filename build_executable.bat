@echo off
echo ========================================
echo Building Galil Setup Tool Executable
echo ========================================
echo.

echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del "*.spec"

echo.
echo Building executable with PyInstaller...
pyinstaller --onefile --windowed --name "Galil_Setup_Tool" --add-data "gclib.dll;." --add-data "gclibo.dll;." --add-data "config.json;." --add-data "assets;assets" --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.messagebox --hidden-import tkinter.simpledialog --hidden-import serial --hidden-import serial.tools.list_ports --hidden-import ctypes --hidden-import platform --hidden-import subprocess --hidden-import re --hidden-import os --hidden-import time --hidden-import datetime --hidden-import json --hidden-import math --hidden-import threading --hidden-import typing main.py

echo.
echo Build completed!
echo.
echo Executable location: dist\Galil_Setup_Tool.exe
echo.
echo Files included in executable:
echo - All Python modules
echo - gclib.dll and gclibo.dll
echo - config.json
echo - assets folder
echo.
echo The executable is self-contained and can be run on any Windows machine.
echo.
pause
