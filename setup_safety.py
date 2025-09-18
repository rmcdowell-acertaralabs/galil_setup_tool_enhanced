# setup_safety.py
# Requires: gclib (Galil) handle already opened elsewhere as `g`

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
    resp = g.GCommand(cmd)
    return resp.strip() if isinstance(resp, str) else ""

def abort(g, motion_only: bool = False) -> None:
    """
    AB: Abort motion/program. AB 1 aborts motion only; AB (or AB 0) aborts motion and program.
    """
    _gcmd(g, "AB 1" if motion_only else "AB")

def enable_enhanced_amp_reporting(g, enable: bool = True) -> int:
    """
    AZ2 to enable enhanced error reporting; returns _AZ2 (0 or 1).
    """
    if enable:
        _gcmd(g, "AZ2")
    state = _gcmd(g, "MG _AZ2")
    try:
        return int(float(state))
    except Exception:
        return -1  # unknown

def clear_latched_amp_errors(g, axes: AxisList = ("A", "B", "C", "D")) -> None:
    """
    Proper sequence to clear latched amplifier errors:
    1) MO on involved axes
    2) AZ1
    """
    ax = "".join(_norm_axes(axes))
    _gcmd(g, f"MO{ax}")
    _gcmd(g, "AZ1")
    _gcmd(g, "WT2")  # brief settle

def set_oe(g, value_by_axis: Union[int, Dict[str, int]], axes: AxisList = ("A", "B", "C", "D")) -> Dict[str, int]:
    """
    OE: Off-on-Error. 0=off, 1=pos/amp/abort, 2=limit, 3=pos/amp/abort/limit.
    Returns the applied values per axis from _OEm.
    """
    ax_list = _norm_axes(axes)
    results = {}
    for a in ax_list:
        v = value_by_axis if isinstance(value_by_axis, int) else value_by_axis.get(a, 0)
        _gcmd(g, f"OE{a}={int(v)}")
    # verify
    for a in ax_list:
        v = _gcmd(g, f"MG _OE{a}")
        results[a] = int(float(v)) if v else -1
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
        v = _gcmd(g, f"MG _ER{a}")
        results[a] = int(float(v)) if v else -1
    return results

def set_tl(g, value_by_axis: Union[float, Dict[str, float]], axes: AxisList = ("A", "B", "C", "D")) -> Dict[str, float]:
    """
    TL: Continuous torque limit (V). With internal drives, effective max may be reduced by AG/amp.
    Returns applied values by querying 'TL ?' per axis.
    """
    ax_list = _norm_axes(axes)
    for a in ax_list:
        v = value_by_axis if isinstance(value_by_axis, (int, float)) else value_by_axis.get(a, 5.0)
        _gcmd(g, f"TL{a}={float(v)}")
    # Verify using query form (returns the value for A with 'TL ?'; for others, temporarily swap axis assignment)
    results = {}
    for a in ax_list:
        # Use MG to read back the last-set value via operand is not documented for TL, so prefer TL ? by context switch
        # Easiest: issue 'TL ?' while axis context is 'a' by assigning a no-op; instead, just read 'TL ?,?,?,?' and parse
        q = _gcmd(g, "TL ?,?,?,?")
        if q:
            parts = [p.strip() for p in q.split(",")]
            amap = dict(zip(["A", "B", "C", "D"], (float(x) for x in parts)))
            results[a] = amap.get(a, float("nan"))
        else:
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
    results = {}
    q = _gcmd(g, "TK ?,?,?,?")
    if q:
        parts = [p.strip() for p in q.split(",")]
        amap = dict(zip(["A", "B", "C", "D"], (float(x) for x in parts)))
        for a in ax_list:
            results[a] = amap.get(a, float("nan"))
    else:
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

    # 1) Abort
    abort(g, motion_only=abort_motion_only)
    summary["steps"].append(f"Abort issued ({'motion-only' if abort_motion_only else 'motion+program'})")

    # 2) Enhanced amp reporting
    state = enable_enhanced_amp_reporting(g, enable=enhanced_amp_reporting)
    summary["steps"].append(f"Enhanced amp reporting {'enabled' if state == 1 else 'not enabled'} (_AZ2={state})")

    # 3) Clear latched amp errors
    clear_latched_amp_errors(g, axes)
    summary["steps"].append("Latched amplifier errors cleared (MO + AZ1)")

    # Safety: report abort input state
    ab_state = check_abort_input(g)
    summary["values"]["abort_input"] = ab_state  # 1=inactive, 0=active

    # 4) Apply per-axis safety limits/settings
    oe_applied = set_oe(g, oe, axes)
    er_applied = set_er(g, er, axes)
    tl_applied = set_tl(g, tl, axes)
    tk_applied = set_tk(g, tk, axes)

    summary["values"]["OE"] = oe_applied
    summary["values"]["ER"] = er_applied
    summary["values"]["TL"] = tl_applied
    summary["values"]["TK"] = tk_applied

    return summary
