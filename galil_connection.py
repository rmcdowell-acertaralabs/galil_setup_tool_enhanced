"""
Thread-safe Galil connection wrapper with connection recovery
Implements single command pipe with serialization lock
"""

import threading
import time
import gclib

# Hardware configuration - ONLY A and B axes are fitted on this DMC-4143
SUPPORTED_AXES = ("A", "B")  # C and D not present
MAX_DI = 8  # Digital inputs 1..8
MAX_DO = 8  # Digital outputs 1..8 (not 16)

class GalilConnection:
    """Thread-safe Galil controller connection with automatic recovery"""
    
    def __init__(self, address):
        self.address = address
        self.lock = threading.RLock()
        self.g = None
        self.connected = False
        self.pollers_paused = False
        
    def open(self):
        """Open connection to controller"""
        with self.lock:
            if self.connected:
                return
            self.g = gclib.py()
            self.g.GOpen(f"{self.address} -s ALL")
            self.connected = True
            print(f"[Galil] Connected to {self.address}")
    
    def close(self):
        """Close connection to controller"""
        with self.lock:
            if self.g:
                try:
                    self.g.GClose()
                except:
                    pass
            self.g = None
            self.connected = False
            print(f"[Galil] Disconnected from {self.address}")
    
    def _reconnect(self):
        """Internal reconnection - stop pollers BEFORE tearing down socket"""
        print("[Galil] Reconnecting...")
        # Stop pollers BEFORE tearing down socket
        self.pollers_paused = True
        self.close()
        time.sleep(0.2)
        self.open()
        self.pollers_paused = False
        print("[Galil] Reconnection complete")
    
    def cmd(self, s, retries=1):
        """Send command with automatic reconnection on dead handle"""
        with self.lock:
            if not self.connected:
                raise ConnectionError("Controller not connected")
            
            for attempt in range(retries + 1):
                try:
                    return self.g.GCommand(s)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Dead handle? Reconnect once
                    if "connection to hardware not established" in error_msg and attempt < retries:
                        print(f"[Galil] Dead handle detected, reconnecting...")
                        self._reconnect()
                        continue
                    raise

# Global connection instance
_galil_instance = None

def get_galil_connection(address=None):
    """Get or create the global Galil connection"""
    global _galil_instance
    if _galil_instance is None and address:
        _galil_instance = GalilConnection(address)
    return _galil_instance

def gsend(s):
    """Safe send - bail on error, don't continue sending"""
    galil = get_galil_connection()
    if not galil:
        raise ConnectionError("Galil connection not initialized")
    try:
        out = galil.cmd(s)
        return out
    except Exception as e:
        # Bail up the stack; do not keep sending more commands here
        raise

def num(cmd):
    """Robust numeric parser - first token of first non-empty line only
    
    Note: For status variables, caller must wrap in MG, e.g.:
        num("MG {_MOA}") not num("_MOA")
    """
    s = gsend(cmd).strip()
    if not s or s == "?":
        return float("nan")
    line = s.splitlines()[0]
    tok = line.split()[0]
    return float(tok)

def wait_bg(ax, timeout=10.0):
    """Wait for motion completion by polling _BG (host-safe, no AM)"""
    if ax not in SUPPORTED_AXES:
        raise ValueError(f"Axis {ax} not in SUPPORTED_AXES {SUPPORTED_AXES}")
    
    t0 = time.time()
    while True:
        try:
            # Read first token of first line only - MUST use MG {_BGx}
            busy = float(gsend(f"MG {{_BG{ax}}}").split()[0])
            if busy == 0.0:
                return  # Motion complete
            if time.time() - t0 > timeout:
                raise TimeoutError(f"Axis {ax} still busy after {timeout}s")
            time.sleep(0.02)  # Poll every 20ms
        except Exception as e:
            if "connection to hardware not established" in str(e).lower():
                raise  # Let caller handle reconnection
            # Other errors - continue polling
            time.sleep(0.02)

def clear_errors_and_rebaseline(ax):
    """Clear controller errors and re-establish baseline for an axis"""
    if ax not in SUPPORTED_AXES:
        raise ValueError(f"Axis {ax} not in SUPPORTED_AXES {SUPPORTED_AXES}")
    
    try:
        gsend("TC")  # Read error code
    except:
        pass
    gsend("TC 0")  # Clear error code
    
    # Re-establish baseline for this axis
    gsend(f"SH{ax}")
    time.sleep(0.05)  # Let servo engage
    gsend(f"ST{ax}")
    gsend(f"DP{ax}=0")
    print(f"[Galil] Cleared errors and rebaselined axis {ax}")

def motion_profile(ax):
    """Execute full motion profile for an axis (host-safe)"""
    if ax not in SUPPORTED_AXES:
        raise ValueError(f"Axis {ax} not in SUPPORTED_AXES {SUPPORTED_AXES}")
    
    print(f"[Galil] Starting motion profile for axis {ax}")
    
    # Setup global parameters
    gsend("OE=0")
    gsend("ER=2000000")
    gsend("TL=8")
    gsend(f"MT{ax}=1")
    
    # Enable servo and baseline
    gsend(f"SH{ax}")
    time.sleep(0.05)
    gsend(f"ST{ax}")
    gsend(f"DP{ax}=0")
    
    # Set motion parameters
    gsend(f"SP{ax}=100000")
    gsend(f"AC{ax}=500000")
    gsend(f"DC{ax}=500000")
    
    # Execute four-segment move
    targets = [50000, 0, -50000, 0]
    target_names = ["forward +50k", "return to 0", "backward -50k", "final return to 0"]
    
    for tgt, name in zip(targets, target_names):
        print(f"[Galil] Axis {ax}: Moving to {tgt} ({name})")
        gsend(f"PA{ax}={tgt}")
        gsend(f"BG{ax}")
        wait_bg(ax)
        pos = num(f"TP{ax}")
        print(f"[Galil] Axis {ax}: Position = {pos}")
    
    print(f"[Galil] Motion profile complete for axis {ax}")

# Context manager for quiet phases
from contextlib import contextmanager

@contextmanager
def quiet_phase(name=""):
    """Pause background pollers during sensitive operations"""
    galil = get_galil_connection()
    if galil:
        print(f"[Galil] Entering quiet phase: {name}")
        galil.pollers_paused = True
    try:
        yield
    finally:
        if galil:
            galil.pollers_paused = False
            print(f"[Galil] Exiting quiet phase: {name}")

