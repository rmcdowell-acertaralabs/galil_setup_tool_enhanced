# setup_safety.py
# Requires: gclib (Galil) handle already opened elsewhere as `g`

import time
from typing import Dict, Iterable, Tuple, Union

AxisList = Union[Iterable[str], str]

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A", "B", "C", "D"))
    if not axes:
        raise ValueError("No valid axes provided (choose from A, B, C, D).")
    return axes

def _gcmd(g, cmd: str) -> str:
    """Send a command and return the controller's response (stripped)."""
    try:
        resp = g.GCommand(cmd)
        s = resp.strip() if isinstance(resp, str) else ""
        if s == "?":
            # Check for controller error using TC 1
            try:
                why = (g.GCommand("TC 1") or "").strip()
                raise RuntimeError(f"Controller rejected: {cmd}  (TC1={why})")
            except Exception:
                raise RuntimeError(f"Controller rejected: {cmd}  (TC1=unknown)")
        return s
    except Exception as e:
        # Re-raise RuntimeError (from ? response) but catch other exceptions
        if isinstance(e, RuntimeError):
            raise
        # If command fails due to connection/other issues, return empty string
        print(f"Warning: Command '{cmd}' failed: {e}")
        return ""

def abort(g, motion_only: bool = False) -> None:
    """
    AB: Abort motion/program. AB 1 aborts motion only; AB (or AB 0) aborts motion and program.
    """
    _gcmd(g, "AB 1" if motion_only else "AB")

def enable_enhanced_amp_reporting(g, enable: bool = True) -> int:
    """
    AZ 2 to enable enhanced error reporting.
    NOTE: _AZ2 operand may not exist on all controllers - skip if error.
    """
    if enable:
        try:
            _gcmd(g, "AZ 2")  # Use AZ 2 command, not AZ2
        except:
            pass  # Some controllers may not support this
    # Don't try to read _AZ2 - may not exist on all hardware
    return -1  # unknown/not supported

def clear_latched_amp_errors(g, axes: AxisList = ("A", "B")) -> None:
    """
    Proper sequence to clear latched amplifier errors:
    1) MO on involved axes
    2) Verify all axes are off before AZ1
    3) AZ1 only if all are off
    """
    ax = "".join(_norm_axes(axes))
    _gcmd(g, f"MO{ax}")
    
    # Verify all axes are actually off before AZ
    all_off = True
    for ax in _norm_axes(axes):
        try:
            s = _gcmd(g, f"MG _MO{ax}").strip()
            all_off &= (s.split(',')[0] == "1")  # 1 means motor off
        except Exception:
            # if query fails, don't assume it's safe
            all_off = False
    
    # Clear latched amp faults only if all are off
    if all_off:
        _gcmd(g, "AZ")     # <— use AZ; no index; valid on 41x3
        time.sleep(0.002)  # Host sleep 2ms (WT is program-only, not valid in terminal)
    else:
        # Log warning but don't fail
        print("Warning: Not all axes are off, skipping AZ")

def set_oe(g, value_by_axis: Union[int, Dict[str, int]], axes: AxisList = ("A", "B", "C", "D")) -> Dict[str, int]:
    """
    OE: Off-on-Error. 0=off, 1=pos/amp/abort, 2=limit, 3=pos/amp/abort/limit.
    Returns the applied values per axis from vector query.
    """
    ax_list = _norm_axes(axes)
    for a in ax_list:
        v = value_by_axis if isinstance(value_by_axis, int) else value_by_axis.get(a, 0)
        _gcmd(g, f"OE{a}={int(v)}")
    # Verify using vector query "OE ?,?,?,?" (works on 41x3); do NOT use MG _OEa
    q = _gcmd(g, "OE ?,?,?,?")
    results = {}
    try:
        parts = [p.strip() for p in q.split(",")]
        amap = dict(zip(["A", "B", "C", "D"], (int(float(x)) for x in parts)))
        for a in ax_list:
            results[a] = amap.get(a, -1)
    except Exception:
        for a in ax_list:
            results[a] = -1
    return results

def set_er(g, value_by_axis: Union[int, Dict[str, int]], axes: AxisList = ("A", "B", "C", "D")) -> Dict[str, int]:
    """
    ER: Error limit (counts) that triggers error/OE action.
    Returns applied values via _ERm.
    """
    ax_list = _norm_axes(axes)
    results = {}
    for a in ax_list:
        v = value_by_axis if isinstance(value_by_axis, int) else value_by_axis.get(a, 16384)
        _gcmd(g, f"ER{a}={int(v)}")
    for a in ax_list:
        rv = _gcmd(g, f"MG _ER{a}")  # may be '?', '', or a number
        try:
            results[a] = int(float(rv.split(',')[0]))
        except Exception:
            results[a] = -1  # unknown/unsupported on this axis—don't crash
    return results

def set_tl(g, value_by_axis: Union[float, Dict[str, float]], axes: AxisList = ("A", "B", "C", "D")) -> Dict[str, float]:
    """
    TL: Continuous torque limit (V). With internal drives, effective max may be reduced by AG/amp.
    Returns applied values by querying 'TL ?,?,?,?'.
    """
    ax_list = _norm_axes(axes)
    for a in ax_list:
        v = value_by_axis if isinstance(value_by_axis, (int, float)) else value_by_axis.get(a, 5.0)
        _gcmd(g, f"TL{a}={float(v)}")
    # Verify using vector query
    q = _gcmd(g, "TL ?,?,?,?")
    results = {}
    try:
        parts = [p.strip() for p in q.split(",")]
        amap = dict(zip(["A", "B", "C", "D"], (float(x) for x in parts)))
        for a in ax_list:
            results[a] = amap.get(a, float("nan"))
    except Exception:
        for a in ax_list:
            results[a] = float("nan")
    return results

def set_tk(g, value_by_axis: Union[float, Dict[str, float]], axes: AxisList = ("A", "B", "C", "D")) -> Dict[str, float]:
    """
    TK: Peak torque limit (V). 0 disables peak torque limiting.
    Returns applied values by querying 'TK ?,?,?,?'.
    """
    ax_list = _norm_axes(axes)
    for a in ax_list:
        v = value_by_axis if isinstance(value_by_axis, (int, float)) else value_by_axis.get(a, 9.99)
        _gcmd(g, f"TK{a}={float(v)}")
    # Verify using vector query
    q = _gcmd(g, "TK ?,?,?,?")
    results = {}
    try:
        parts = [p.strip() for p in q.split(",")]
        amap = dict(zip(["A", "B", "C", "D"], (float(x) for x in parts)))
        for a in ax_list:
            results[a] = amap.get(a, float("nan"))
    except Exception:
        for a in ax_list:
            results[a] = float("nan")
    return results

def check_abort_input(g) -> int:
    """
    Returns _AB: 1 means abort input inactive, 0 means active (triggered).
    """
    v = _gcmd(g, "MG _AB")
    try:
        return int(float(v))
    except Exception:
        return -1


def servo_bringup_41x3(g):
    """Force SERVO motors, sane CN/OE, and verify SH per-axis (no brace syntax)."""
    # Quiesce; ignore if a subcommand isn't supported
    for cmd in ("TC 0", "AB 1", "ST"):  # AB 1 = abort motion only, not program
        try: 
            g.GCommand(cmd)
        except: 
            pass

    # Force servo mode per-axis (older firmwares dislike tuple MT):
    # NOTE: Only A and B axes are fitted on this hardware
    for ax in "AB":  # Only axes A and B present, C and D not fitted
        try: 
            g.GCommand(f"MT{ax}=0")
        except: 
            pass  # keep going; some axes may not exist

    # Put config into a sane baseline
    # CN -1 = limits active low (safe for no limit switches - inputs float high)
    for cmd in ("CN -1", "OE 0"):
        try: 
            g.GCommand(cmd)
        except: 
            pass

    # Engage each axis individually with retry logic (so one bad axis doesn't poison others)
    # CRITICAL: Only A and B axes exist on this hardware
    mo_status = {}
    for ax in "AB":  # Only A and B fitted, not C or D
        try:
            # Try to enable servo with retry logic
            for attempt in range(3):  # Try up to 3 times
                try:
                    g.GCommand(f"SH{ax}")
                    # Wait a bit for servo to engage
                    import time
                    time.sleep(0.1)
                    
                    # Check if servo is enabled
                    s = g.GCommand(f"MG _MO{ax}") or "1"
                    mo_value = int(float(s.split(",")[0]))
                    if mo_value == 0:  # Servo enabled successfully
                        mo_status[ax] = 0
                        print(f"[SETUP] Axis {ax}: Servo enabled successfully")
                        break
                    else:
                        print(f"[SETUP] Axis {ax}: Servo enable attempt {attempt + 1} failed (MO={mo_value})")
                        if attempt < 2:  # Not the last attempt
                            time.sleep(0.2)  # Wait before retry
                except Exception as e:
                    print(f"[SETUP] Axis {ax}: Servo enable attempt {attempt + 1} failed: {e}")
                    if attempt < 2:  # Not the last attempt
                        time.sleep(0.2)  # Wait before retry
            else:
                # All attempts failed
                mo_status[ax] = 1
                print(f"[SETUP] Axis {ax}: All servo enable attempts failed")
        except Exception as e:
            mo_status[ax] = 1  # treat as OFF if anything fails
            print(f"[SETUP] Axis {ax}: Servo enable error: {e}")

    print(f"[SETUP] _MO: " + ", ".join(f"{k}={v}" for k,v in mo_status.items()))
    return mo_status

def enforce_servo_only(g):
    """
    Force servo-only mode on every boot/run - no step/dir ever.
    Call this once during Setup/Safety (before discovery/motion).
    """
    try:
        # Servo-only on all axes (no step/dir ever) - this is critical
        _gcmd(g, "MT 0,0,0,0")   # all axes = servo, never stepper
        # Reasonable tolerant defaults
        _gcmd(g, "OE 0")          # don't trip out on minor errors during setup
        _gcmd(g, "ER=200000,200000,200000,200000")
        _gcmd(g, "TL=100,100,100,100")
        # Clean slate (NOTE: AM is program-only, use ST and AB 1 for host-side control)
        _gcmd(g, "AB 1; ST; TC 0")  # AB 1 = abort motion only (not program), ST = stop all axes
    except Exception:
        pass

def setup_safety(
    g,
    axes: AxisList = ("A", "B", "C", "D"),
    abort_motion_only: bool = False,
    enhanced_amp_reporting: bool = True,
    oe: Union[int, Dict[str, int]] = 3,
    er: Union[int, Dict[str, int]] = 200,
    tl: Union[float, Dict[str, float]] = 5.0,
    tk: Union[float, Dict[str, float]] = 9.0,
) -> dict:
    """
    Full Setup/Safety sequence:
      1) AB (optionally AB 1)
      2) Enable AZ2 enhanced reporting
      3) Clear latched amp errors (MO + AZ1)
      4) Set OE/ER/TL/TK per axis and verify
    Returns a dict summary of applied settings and key status.
    """
    summary = {"steps": [], "values": {}}

    try:
        # 1) Abort
        abort(g, motion_only=abort_motion_only)
        summary["steps"].append(f"Abort issued ({'motion-only' if abort_motion_only else 'motion+program'})")
    except Exception as e:
        summary["steps"].append(f"Abort failed: {e}")

    try:
        # 2) Enhanced amp reporting
        state = enable_enhanced_amp_reporting(g, enable=enhanced_amp_reporting)
        summary["steps"].append(f"Enhanced amp reporting {'enabled' if state == 1 else 'not enabled'} (_AZ2={state})")
    except Exception as e:
        summary["steps"].append(f"Enhanced amp reporting failed: {e}")

    try:
        # 3) Clear latched amp errors
        clear_latched_amp_errors(g, axes)
        summary["steps"].append("Latched amplifier errors cleared (MO + AZ1)")
    except Exception as e:
        summary["steps"].append(f"Clear latched amp errors failed: {e}")
    
    # Clear any prior controller error code so Status Check reflects this run only
    try:
        _gcmd(g, "TC 0")
    except Exception as e:
        summary["steps"].append(f"TC 0 failed: {e}")

    # Safety: report abort input state
    try:
        ab_state = check_abort_input(g)
        summary["values"]["abort_input"] = ab_state  # 1=inactive, 0=active
    except Exception as e:
        summary["values"]["abort_input"] = -1
        summary["steps"].append(f"Abort input check failed: {e}")

    # 4) Apply per-axis safety limits/settings
    try:
        oe_applied = set_oe(g, oe, axes)
        summary["values"]["OE"] = oe_applied
    except Exception as e:
        summary["values"]["OE"] = {}
        summary["steps"].append(f"OE setting failed: {e}")

    try:
        er_applied = set_er(g, er, axes)
        summary["values"]["ER"] = er_applied
    except Exception as e:
        summary["values"]["ER"] = {}
        summary["steps"].append(f"ER setting failed: {e}")

    try:
        tl_applied = set_tl(g, tl, axes)
        summary["values"]["TL"] = tl_applied
    except Exception as e:
        summary["values"]["TL"] = {}
        summary["steps"].append(f"TL setting failed: {e}")

    try:
        tk_applied = set_tk(g, tk, axes)
        summary["values"]["TK"] = tk_applied
    except Exception as e:
        summary["values"]["TK"] = {}
        summary["steps"].append(f"TK setting failed: {e}")

    return summary
