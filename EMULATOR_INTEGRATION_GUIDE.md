# DMC-4143 Emulator Integration Guide

This guide explains how to use the `dmc4143_emulator.py` to test your Galil Setup Tool without physical hardware.

## Overview

The emulator provides two usage modes:
1. **TCP Server Mode**: Runs as a standalone server that your application connects to via IP address
2. **Python Mock Mode**: Drop-in replacement for `gclib.py()` that you can import directly

## Method 1: TCP Server Mode (Recommended)

This mode works with your existing code with minimal changes - just point your connection to the emulator's IP.

### Step 1: Start the Emulator Server

Open a terminal and run:

```bash
python dmc4143_emulator.py --server
```

The server will start listening on `127.0.0.1:2323` by default. You'll see:
```
[DMC4143 Emulator] TCP server listening on 127.0.0.1:2323
```

### Step 2: Connect Your Application

In your Galil Setup Tool, connect to the emulator by entering:
- **IP Address**: `127.0.0.1:2323`
- Or modify your connection string to use port 2323

The emulator accepts the same connection format your code uses (`{address} -s ALL`).

### Step 3: Run Your Tests

All your existing tests should work:
- Motor setup and tuning
- Motion tests (`comprehensive_testing.py`)
- IO operations
- Encoder monitoring
- All command validation

The emulator maintains realistic axis state and simulates motion over time.

## Method 2: Python Mock Mode (For Unit Tests)

This mode lets you replace `gclib` with the emulator for automated testing.

### Step 1: Import the Mock

In your test files or before your code uses gclib:

```python
# At the top of your test file or in a test setup
import sys
from dmc4143_emulator import FakeGclib

# Replace gclib module with fake
sys.modules['gclib'] = FakeGclib
```

### Step 2: Use Normally

Your existing code will work without changes:

```python
# This will now use the mock instead of real gclib
import gclib

g = gclib.py()
g.GOpen("127.0.0.1 -s ALL")  # Mock mode - connection string is ignored
g.GCommand("SHA")  # Enable servo on axis A
g.GCommand("PA A=1000")
g.GCommand("BGA")
response = g.GCommand("TPA")  # Get position
print(f"Position: {response}")
g.GClose()
```

## Supported Commands

The emulator supports all commands used in your codebase:

### Motion Commands
- `SHA`, `SHB` - Servo Here (enable servo)
- `MOA`, `MOB` - Motor Off (MO=1 to disable, MO=0 to enable)
- `JGA=5000`, `JGB=5000` - Set jog speed
- `BGA`, `BGB` - Begin motion
- `STA`, `STB`, `ST` - Stop motion
- `PA A=1000`, `PR A=1000` - Position Absolute/Relative
- `TPA`, `TPB` - Tell Position
- `SPA=100000`, `ACA=500000`, `DCA=500000` - Speed/Acceleration/Deceleration
- `DPA=0` - Define Position (zero position counter)
- `FI A`, `AM A` - Find Index, After Motion
- `BA A` - Brushless Align

### Status Queries (via MG command)
- `MG _TSA` - Torque Status
- `MG _BGA` - Busy Flag (0=idle, 1=busy)
- `MG _TPA` - Current Position
- `MG _TEA` - Following Error
- `MG _MOA` - Motor Off Status

### Global Parameters
- `TC` - Tell Error Code (TC 0 to clear)
- `OE=3` - Output Error
- `ER=2000000` - Error Limit
- `TL=8.0` - Torque Limit
- `TK=9.0` - Torque Kill

## Integration with Your Codebase

### Option A: Quick Test (Minimal Changes)

For quick testing, just run the TCP server and connect to `127.0.0.1:2323` in your GUI. No code changes needed!

### Option B: Automatic Mode Switching

You can modify `galil_connection.py` to automatically use the emulator in test mode:

```python
# In galil_connection.py, add at the top:
import os
USE_EMULATOR = os.getenv("GALIL_USE_EMULATOR", "false").lower() == "true"

# In GalilConnection.open():
def open(self):
    """Open connection to controller"""
    with self.lock:
        if self.connected:
            return
        
        if USE_EMULATOR or self.address == "127.0.0.1:2323":
            # Use emulator
            from dmc4143_emulator import FakeGclib
            self.g = FakeGclib.py()
        else:
            # Use real gclib
            import gclib
            self.g = gclib.py()
        
        self.g.GOpen(f"{self.address} -s ALL")
        self.connected = True
        print(f"[Galil] Connected to {self.address}")
```

Then set the environment variable:
```bash
set GALIL_USE_EMULATOR=true  # Windows
export GALIL_USE_EMULATOR=true  # Linux/Mac
```

### Option C: Test Wrapper

Create a test wrapper that automatically uses the emulator:

```python
# test_with_emulator.py
from dmc4143_emulator import FakeGclib
import sys

# Replace gclib module
sys.modules['gclib'] = FakeGclib

# Now import and run your tests
from comprehensive_testing import ComprehensiveTester
# ... run your tests
```

## Testing Your Full Application

1. **Start the emulator server**:
   ```bash
   python dmc4143_emulator.py --server
   ```

2. **Run your application** normally:
   ```bash
   python main.py
   ```

3. **In the GUI**, connect to `127.0.0.1:2323`

4. **Run all tests**:
   - Motor setup dialogs
   - Tuning dialogs
   - Comprehensive testing suite
   - Motion tests
   - Encoder monitoring
   - IO operations

## Emulator Behavior

The emulator simulates realistic controller behavior:

- **Axis State**: Each axis (A, B) maintains independent state (position, speed, servo status)
- **Motion Simulation**: Position updates over time when jogging or moving to targets
- **Status Variables**: `_BG`, `_TS`, `_TP`, `_TE`, `_MO` update realistically
- **Command Format**: Accepts same command format as real controller (CR/LF terminated)
- **Error Handling**: Returns `?` for unknown commands, just like real hardware

## Limitations

The emulator is designed for **testing**, not perfect hardware simulation:

- Motion physics are simplified (constant velocity, no complex acceleration profiles)
- No actual limit switches or home sensors (hardcoded mock values)
- No encoder noise or following error dynamics
- No actual IO hardware (all digital/analog IOs are mock)

For most testing purposes, this is sufficient!

## Troubleshooting

### Connection Issues
- Make sure the emulator server is running before connecting
- Check that port 2323 isn't blocked by firewall
- Try `telnet 127.0.0.1 2323` to test the connection

### Command Not Working
- Check the emulator console output for errors
- Unknown commands return `?` - check if command is supported
- Some commands may need axis specified (e.g., `SHA` not `SH`)

### Motion Not Updating
- Motion updates happen in background thread (~50Hz)
- Position changes may not be instant for large moves
- Check `_BG` status: `MG _BGA` should be `1` when moving

## Extending the Emulator

To add support for more commands, edit `dmc4143_emulator.py`:

1. Add command parsing in `parse_command()`
2. Add implementation method (e.g., `_cmd_your_command()`)
3. Update axis state as needed

Example:
```python
def _cmd_your_command(self, axis: Optional[str], value: Optional[int]) -> str:
    """YC - Your Command"""
    if axis and axis in self.axes and value is not None:
        # Do something
        return ""
    return "?"
```

## Next Steps

1. Try TCP server mode first - it's the easiest
2. Run your comprehensive test suite against the emulator
3. Verify all your dialogs work correctly
4. Add any missing commands you need

Happy testing!

