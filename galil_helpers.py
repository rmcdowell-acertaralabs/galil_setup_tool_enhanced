"""
Galil Helper Functions - Shared Utilities
Thread-safe, DMC-4103 compliant helper functions for all motion testing
"""

import time
from typing import Optional, Callable


def cmd(gc, c: str, sleep_ms: int = 0) -> str:
    """
    Send a command and return raw reply with TC1 error text on failure.
    
    Args:
        gc: gclib connection object
        c: Command string to send
        sleep_ms: Optional sleep after command (milliseconds)
    
    Returns:
        Stripped response string
        
    Raises:
        RuntimeError with TC1 error text if command fails
    """
    try:
        r = gc.GCommand(c)
        if sleep_ms:
            time.sleep(sleep_ms / 1000.0)
        return r.strip()
    except Exception as e:
        # Fetch controller-side error text if available
        try:
            tc1 = gc.GCommand("TC1").strip()
        except Exception:
            tc1 = "TC1 unavailable"
        
        # Don't print errors for TP commands on disconnected axes to avoid flood
        error_msg = str(e).lower()
        if "device write error" in error_msg and any(c.startswith(f"TP{ax}") for ax in ["A", "B", "C", "D"]):
            # Silently raise for TP commands on disconnected axes
            raise RuntimeError(f"Command '{c}' failed: device write error")
        
        raise RuntimeError(f"Command failed: {c} | {e} | {tc1}")


def read_scalar(gc, query: str) -> float:
    """
    Read a single numeric value from controller.
    
    Args:
        gc: gclib connection object
        query: Query command (e.g., 'TPA', 'MG _MOA')
    
    Returns:
        Float value (first token of first line)
        
    Note:
        For multi-value queries, use read_vector() instead
    """
    r = cmd(gc, query)
    # Some replies can include trailing CRLF or spaces; ensure single token
    tok = r.split()[0]
    return float(tok)


def read_vector(gc, query: str) -> list:
    """
    Read multiple numeric values from controller.
    
    Args:
        gc: gclib connection object
        query: Query command that returns multiple values
    
    Returns:
        List of float values
    """
    r = cmd(gc, query)
    return [float(tok) for tok in r.split()]


def is_servo_on(gc, ax: str) -> bool:
    """
    Check if servo is enabled for an axis.
    
    Args:
        gc: gclib connection object
        ax: Axis letter ('A', 'B', 'C', etc.)
    
    Returns:
        True if servo on (MO=0), False if off (MO=1)
    """
    return int(read_scalar(gc, f"MG _MO{ax}")) == 0


def ensure_servo_on(gc, ax: str, settle_ms: int = 50):
    """
    Ensure servo is enabled for an axis with ST-MO-SH sequence.
    
    Args:
        gc: gclib connection object
        ax: Axis letter ('A', 'B', 'C', etc.)
        settle_ms: Milliseconds to wait after SH command
        
    Raises:
        RuntimeError if servo fails to enable
    """
    # Stop motion first
    cmd(gc, f"ST{ax}")
    time.sleep(0.05)
    
    # Turn servo OFF then ON to ensure clean state
    cmd(gc, f"MO{ax}")
    time.sleep(0.05)
    
    # Enable servo
    cmd(gc, f"SH{ax}")
    time.sleep(settle_ms / 1000.0)
    
    # Verify servo is on
    if not is_servo_on(gc, ax):
        mo = read_scalar(gc, f"MG _MO{ax}")
        raise RuntimeError(f"Servo for {ax} did not turn on (MO={mo})")


def wait_motion_complete(gc, ax: str, timeout_s: float = 10.0, debug: bool = False):
    """
    Wait for motion to complete by polling _BG status.
    This is the host-safe alternative to AM command (which is program-only).
    
    Args:
        gc: gclib connection object
        ax: Axis letter ('A', 'B', 'C', etc.)
        timeout_s: Maximum seconds to wait
        debug: If True, print diagnostic info during motion
        
    Raises:
        TimeoutError if motion doesn't complete in time
        RuntimeError if servo drops during motion
    """
    t0 = time.time()
    last_pos = None
    stall_count = 0
    
    while True:
        # Read all status variables
        busy = read_scalar(gc, f"MG _BG{ax}")
        mo = read_scalar(gc, f"MG _MO{ax}")
        tp = read_scalar(gc, f"TP{ax}")
        
        if debug:
            te = read_scalar(gc, f"MG _TE{ax}")
            ta = read_scalar(gc, f"MG _TA{ax}")
            elapsed = time.time() - t0
            print(f"    [DEBUG {elapsed:.2f}s] _BG={busy}, _MO={mo}, TP={tp:.0f}, TE={te:.0f}, TA={ta}")
        
        # Check if servo dropped
        if mo != 0.0:
            te = read_scalar(gc, f"MG _TE{ax}")
            ta = read_scalar(gc, f"MG _TA{ax}")
            raise RuntimeError(f"Servo dropped during motion! MO={mo}, TA={ta}, TE={te}, TP={tp}")
        
        # Check if motor stalled (position not changing)
        if last_pos is not None:
            if abs(tp - last_pos) < 0.1:
                stall_count += 1
                if stall_count > 10:  # Stalled for 200ms
                    te = read_scalar(gc, f"MG _TE{ax}")
                    ta = read_scalar(gc, f"MG _TA{ax}")
                    raise RuntimeError(f"Motor stalled at TP={tp}, TE={te}, TA={ta}, MO={mo}")
            else:
                stall_count = 0
        last_pos = tp
        
        # Check if motion complete
        if busy == 0.0:
            if debug:
                print(f"    [DEBUG] Motion complete at TP={tp}")
            return  # Motion complete
            
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"Axis {ax} motion timeout at TP={tp}")
        
        time.sleep(0.02)  # Poll every 20ms


def set_motion_profile(gc, ax: str, sp: int, ac: int, dc: int):
    """
    Set motion profile parameters for an axis.
    
    Args:
        gc: gclib connection object
        ax: Axis letter
        sp: Speed (counts/s)
        ac: Acceleration (counts/s^2)
        dc: Deceleration (counts/s^2)
    """
    cmd(gc, f"SP{ax}={sp}")
    cmd(gc, f"AC{ax}={ac}")
    cmd(gc, f"DC{ax}={dc}")


def zero_position(gc, ax: str):
    """
    Zero the commanded position for an axis.
    
    Args:
        gc: gclib connection object
        ax: Axis letter
    """
    cmd(gc, f"DP{ax}=0")


def move_absolute(gc, ax: str, position: int, wait: bool = True, timeout_s: float = 10.0, debug: bool = False):
    """
    Move axis to absolute position.
    
    Args:
        gc: gclib connection object
        ax: Axis letter
        position: Target position (counts)
        wait: If True, wait for motion to complete
        timeout_s: Maximum wait time if wait=True
        debug: If True, enable diagnostic output during motion
    """
    cmd(gc, f"PA{ax}={position}")
    cmd(gc, f"BG{ax}")
    if wait:
        wait_motion_complete(gc, ax, timeout_s, debug=debug)


def read_position(gc, ax: str) -> float:
    """
    Read current position for an axis.
    
    Args:
        gc: gclib connection object
        ax: Axis letter
    
    Returns:
        Current position (counts)
    """
    return read_scalar(gc, f"TP{ax}")


def clear_errors_and_baseline(gc, ax: str):
    """
    Clear controller errors and re-establish baseline for an axis.
    
    Args:
        gc: gclib connection object
        ax: Axis letter
    """
    try:
        cmd(gc, "TC")  # Read error code (optional)
    except:
        pass
    cmd(gc, "TC 0")  # Clear error
    
    # Re-establish baseline
    ensure_servo_on(gc, ax)
    cmd(gc, f"ST{ax}")
    zero_position(gc, ax)


def setup_global_parameters(gc, oe: int = 0, er: int = 2000000, tl: float = 8.0):
    """
    Set global controller parameters.
    
    Args:
        gc: gclib connection object
        oe: Off-on-error setting
        er: Error limit
        tl: Torque limit
    """
    cmd(gc, f"OE={oe}")
    cmd(gc, f"ER={er}")
    cmd(gc, f"TL={tl}")


def setup_axis_servo(gc, ax: str, motor_type: int = 0):
    """
    Configure axis for servo operation.
    
    Args:
        gc: gclib connection object
        ax: Axis letter
        motor_type: 0=servo, 1=servo reversed, 2=stepper, etc.
    """
    cmd(gc, f"MT{ax}={motor_type}")
    ensure_servo_on(gc, ax)


# Backward compatibility wrapper for existing code
def gnum(gc, query: str, default: float = float("nan")) -> float:
    """
    Robust numeric parser - handles multiline/echoed responses.
    Kept for backward compatibility with existing code.
    
    For new code, use read_scalar() instead.
    """
    try:
        return read_scalar(gc, query)
    except Exception:
        return default

