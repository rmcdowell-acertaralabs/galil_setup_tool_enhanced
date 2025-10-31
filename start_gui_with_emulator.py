#!/usr/bin/env python3
"""
Launcher script that starts both the emulator server and the GUI application.
Run this script to start everything with the emulator already running.
"""

import subprocess
import sys
import time
import socket
import threading

def check_port_open(host, port, timeout=1):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def start_emulator_server():
    """Start the emulator server in a background process"""
    print("[Launcher] Starting DMC-4143 Emulator Server...")
    try:
        # Start emulator server
        emulator_process = subprocess.Popen(
            [sys.executable, "dmc4143_emulator.py", "--server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        # Wait for server to be ready
        max_wait = 5
        wait_time = 0
        while wait_time < max_wait:
            if check_port_open("127.0.0.1", 2323, timeout=0.5):
                print("[Launcher] ✓ Emulator server is ready on port 2323")
                return emulator_process
            time.sleep(0.5)
            wait_time += 0.5
        
        print("[Launcher] ⚠ Emulator server may not be ready (port check timed out)")
        return emulator_process
    except Exception as e:
        print(f"[Launcher] ✗ Failed to start emulator server: {e}")
        return None

def start_gui():
    """Start the GUI application"""
    print("[Launcher] Starting Galil Setup Tool GUI...")
    try:
        # Start GUI (this will block until GUI closes)
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        print("\n[Launcher] GUI closed by user")
    except Exception as e:
        print(f"[Launcher] ✗ Failed to start GUI: {e}")

def main():
    """Main launcher function"""
    print("=" * 60)
    print("Galil Setup Tool - Emulator Mode Launcher")
    print("=" * 60)
    
    # Check if emulator is already running
    if check_port_open("127.0.0.1", 2323, timeout=0.5):
        print("[Launcher] Emulator server is already running")
        emulator_process = None
    else:
        # Start emulator server
        emulator_process = start_emulator_server()
        if not emulator_process:
            print("[Launcher] ✗ Could not start emulator server")
            print("[Launcher] Starting GUI anyway (you can connect manually)")
    
    # Start GUI
    try:
        start_gui()
    finally:
        # Cleanup: optionally stop emulator when GUI closes
        # (Uncomment if you want to stop emulator when GUI closes)
        # if emulator_process:
        #     print("[Launcher] Stopping emulator server...")
        #     emulator_process.terminate()
        #     emulator_process.wait(timeout=2)
        pass
    
    print("[Launcher] Exiting...")

if __name__ == "__main__":
    main()

