# Requires: pip install gclib (Galil)
# Assumes you have an open gclib connection object `gc` with gc.GCommand(cmd)

from time import sleep
from typing import Dict, List, Tuple
from galil_helpers import (
    cmd, read_scalar, is_servo_on, ensure_servo_on,
    wait_motion_complete, set_motion_profile, zero_position,
    move_absolute, read_position
)

def run_motion_test(
    gc,
    axes: Tuple[str, ...] = ("A", "B"),
    sp: int = 100_000,
    ac: int = 500_000,
    dc: int = 500_000,
    distance: int = 50_000,
    settle_ms: int = 50,
) -> Dict[str, Dict]:
    """
    Motion test for specified axes using axis-suffix commands only.
    Sequence: +distance -> 0 -> -distance -> 0.
    Returns structured results per axis with success flags and final TP.
    """

    # All helper functions now imported from galil_helpers module
    # Using shared, tested implementations

    # -------------------
    # Global, once per test
    # -------------------
    results: Dict[str, Dict] = {}

    # Global setup
    try:
        cmd(gc, "OE=0")
    except Exception:
        pass
    try:
        # CN -1 = limits active low (safe for no limit switches - inputs float high)
        cmd(gc, "CN -1")
    except Exception:
        pass

    # Servo-only config for A/B/C (0 = servo). Ignore missing axes gracefully.
    for ax in ("A", "B", "C"):
        try:
            cmd(gc, f"MT{ax}=0")
        except Exception:
            pass

    # Stop everything we might touch
    for ax in axes:
        try:
            cmd(gc, f"ST{ax}")
        except Exception:
            pass

    # -------------------
    # Per-axis sequence
    # -------------------
    for ax in axes:
        axis_result = {
            "axis": ax,
            "steps": [],
            "ok": False,
            "final_TP": None,
            "notes": [],
        }
        try:
            # Ensure servo ON (guard)
            if not is_servo_on(gc, ax):
                ensure_servo_on(gc, ax, settle_ms)

            # Baseline profile & zero
            set_motion_profile(gc, ax, sp, ac, dc)
            zero_position(gc, ax)

            # Test sequence: +D -> 0 -> -D -> 0
            for target in (distance, 0, -distance, 0):
                move_absolute(gc, ax, target, wait=True)
                tp = read_position(gc, ax)
                axis_result["steps"].append({"target": target, "TP": tp})

            # Final state
            axis_result["final_TP"] = read_position(gc, ax)
            axis_result["ok"] = True

        except Exception as e:
            # Attach controller error reason from our cmd wrapper
            axis_result["notes"].append(str(e))
            # Try to leave axis safe
            try:
                cmd(gc, f"ST{ax}")
                if not is_servo_on(gc, ax):
                    ensure_servo_on(gc, ax, settle_ms)
            except Exception:
                pass

        results[ax] = axis_result

    return results


# Example usage:
# gc = gclib.py()
# gc.GOpen('TCP,10.1.0.21')  # or COMx
# out = run_motion_test(gc, axes=("A","B"), sp=100000, ac=500000, dc=500000, distance=50000)
# print(out)

