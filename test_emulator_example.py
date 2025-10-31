"""
Example script showing how to use the DMC-4143 emulator

This demonstrates both TCP server mode and Python mock mode.
"""

import time
import sys

# Example 1: Python Mock Mode (direct import)
print("=" * 60)
print("Example 1: Python Mock Mode (Direct Import)")
print("=" * 60)

from dmc4143_emulator import FakeGclib

# Replace gclib with emulator
sys.modules['gclib'] = FakeGclib

# Now import gclib - it will use the emulator
import gclib

# Use it just like real gclib
g = gclib.py()
g.GOpen("127.0.0.1 -s ALL")  # Mock mode - connection string is ignored

print("Enabling servo on axis A...")
g.GCommand("SHA")

print("Setting speed and acceleration...")
g.GCommand("SPA=100000")
g.GCommand("ACA=500000")
g.GCommand("DCA=500000")

print("Moving to position 1000...")
g.GCommand("PA A=1000")
g.GCommand("BGA")

# Wait a bit for motion to simulate
time.sleep(0.1)

# Check position
pos = g.GCommand("TPA")
print(f"Current position: {pos}")

# Check busy status
busy = g.GCommand("MG _BGA")
print(f"Busy status: {busy}")

# Check torque status
torque = g.GCommand("MG _TSA")
print(f"Torque status: {torque}")

g.GClose()
print("Mock mode test complete!\n")

# Example 2: Using the helper module
print("=" * 60)
print("Example 2: Using Helper Module")
print("=" * 60)

# Reset sys.modules to test helper
if 'gclib' in sys.modules:
    del sys.modules['gclib']

from galil_emulator_helper import enable_emulator, patch_gclib

# Enable emulator
patch_gclib()

# Now import will use emulator
import gclib

g = gclib.py()
g.GOpen("127.0.0.1 -s ALL")

print("Testing jog...")
g.GCommand("SHA")
g.GCommand("JGA=5000")
g.GCommand("BGA")

time.sleep(0.1)

pos = g.GCommand("TPA")
print(f"Position after jog: {pos}")

g.GCommand("STA")  # Stop
g.GClose()

print("Helper module test complete!\n")

# Example 3: TCP Server Mode (uncomment to test)
print("=" * 60)
print("Example 3: TCP Server Mode")
print("=" * 60)
print("To test TCP server mode:")
print("1. Run: python dmc4143_emulator.py --server")
print("2. In another terminal, run this script")
print("3. Connect to 127.0.0.1:2323")
print("\nOr use the helper:")
print("from galil_emulator_helper import start_emulator_server")
print("server = start_emulator_server()")
print("Then connect your application to 127.0.0.1:2323")

print("\n" + "=" * 60)
print("All examples complete!")
print("=" * 60)

