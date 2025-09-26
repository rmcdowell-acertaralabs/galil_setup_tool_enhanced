# teardown.py
# Requires an open gclib handle `g` (e.g., g = gclib.py(); g.GOpen("..."))
# Commands used: PA X=0, BGX, AMX, MOX

from typing import Iterable, Tuple, Union

AxisList = Union[Iterable[str], str]

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D","E","F","G","H"))
    if not axes:
        raise ValueError("No valid axes provided.")
    return axes

def _cmd(g, cmd: str) -> str:
    out = g.GCommand(cmd)
    return out.strip() if isinstance(out, str) else ""

def teardown_axes(
    g,
    axes: AxisList,
    power_off: bool = True,
) -> None:
    """
    Tear-down sequence per axis:
      1) Check servo status first
      2) PA X=0   (command absolute zero) - only for servo-enabled axes
      3) BGX      (begin) - only for servo-enabled axes
      4) AMX      (wait for profile complete) - only for servo-enabled axes
      5) MOX      (optional: motor off) - for all axes

    Notes:
      - Assumes absolute 0 is a safe park point for each axis.
      - Skips motion commands for axes with servos not enabled.
    """
    ax_list = _norm_axes(axes)
    servo_enabled_axes = []

    # Stop any existing motion first
    for a in ax_list:
        try:
            _cmd(g, f"ST{a}")
            _cmd(g, f"AM{a}")
        except:
            pass
    
    # Check servo status for each axis
    for a in ax_list:
        try:
            mo_status = _cmd(g, f"MG _MO{a}")
            # Clean up response - remove carriage returns, newlines, and colons
            mo_status = mo_status.replace('\r', '').replace('\n', '').replace(':', '') if mo_status else "1"
            mo_value = float(mo_status.split(",")[0]) if mo_status else 1.0
            if mo_value == 0.0:
                servo_enabled_axes.append(a)
                print(f"[TEARDOWN] {a}: Servo enabled, will perform motion teardown")
            else:
                print(f"[TEARDOWN] {a}: Servo not enabled (MO={mo_value}), skipping motion commands")
        except Exception as e:
            print(f"[TEARDOWN] {a}: Cannot check servo status: {e}, skipping motion commands")

    # 1) Set absolute targets to 0 for servo-enabled axes only
    for a in servo_enabled_axes:
        try:
            _cmd(g, f"PA{a}=0")
        except Exception as e:
            print(f"[TEARDOWN] {a}: PA command failed: {e}")

    # 2) Begin each servo-enabled axis motion
    for a in servo_enabled_axes:
        try:
            _cmd(g, f"BG{a}")
        except Exception as e:
            print(f"[TEARDOWN] {a}: BG command failed: {e}")

    # 3) Wait for each servo-enabled axis to complete its profile
    for a in servo_enabled_axes:
        try:
            _cmd(g, f"AM{a}")
        except Exception as e:
            print(f"[TEARDOWN] {a}: AM command failed: {e}")

    # 4) Turn motors off for all axes (this works even if servo not enabled)
    if power_off:
        for a in ax_list:
            try:
                _cmd(g, f"MO{a}")
            except Exception as e:
                print(f"[TEARDOWN] {a}: MO command failed: {e}")
