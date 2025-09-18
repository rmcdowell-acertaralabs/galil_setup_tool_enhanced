# discovery.py
# Requires an open gclib handle `g` (e.g., g = gclib.py(); g.GOpen("..."))

from typing import Dict, Iterable, Tuple, Union

AxisList = Union[Iterable[str], str]

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D"))
    if not axes:
        raise ValueError("No valid axes provided (A-D).")
    return axes

def _cmd(g, cmd: str) -> str:
    """Send a command and return the (stripped) response (may be empty)."""
    r = g.GCommand(cmd)
    return r.strip() if isinstance(r, str) else ""

def _num(s: str) -> float:
    try:
        return float(s.strip())
    except Exception:
        return float("nan")

def _get_ts(g, axis: str) -> int:
    # MG _TSX  → decimal 0..255
    return int(_num(_cmd(g, f"MG _TS{axis}")))

def _get_tp(g, axis: str) -> float:
    # TPX (no space) → position counts
    return _num(_cmd(g, f"TP{axis}"))

def _get_ta(g, axis: str) -> int:
    """
    TAX: Tell amplifier error for axis (preferred by your style).
    Fallback: derive from _TA0.._TA3 if TAX isn't supported on this controller.
    """
    try:
        return int(_num(_cmd(g, f"TA{axis}")))  # e.g., TAA, TAB...
    except Exception:
        # Fallback: read banks and return a compact summary (OR of banks)
        ta0 = int(_num(_cmd(g, "MG _TA0")))
        ta1 = int(_num(_cmd(g, "MG _TA1")))
        ta2 = int(_num(_cmd(g, "MG _TA2")))
        ta3 = int(_num(_cmd(g, "MG _TA3")))
        # Not strictly per-axis, but preserves signal that an amp issue exists.
        return ta0 | ta1 | ta2 | ta3

def _decode_ts(ts: int) -> Dict[str, int]:
    # TS bits (1=bit set):
    # 7 motion, 6 error-limit, 5 motor-off, 4 reserved, 3 fwd-limit-inactive, 2 rev-limit-inactive, 1 home, 0 latch
    return {
        "motion":           (ts >> 7) & 1,
        "error_limit":      (ts >> 6) & 1,
        "motor_off":        (ts >> 5) & 1,
        "fwd_limit_inact":  (ts >> 3) & 1,
        "rev_limit_inact":  (ts >> 2) & 1,
        "home":             (ts >> 1) & 1,
        "latch":            (ts >> 0) & 1,
    }

def _set_profile(g, axis: str, sp: int, ac: int, dc: int) -> None:
    # SP X=…, AC X=…, DC X=…
    _cmd(g, f"SP {axis}={int(sp)}")
    _cmd(g, f"AC {axis}={int(ac)}")
    _cmd(g, f"DC {axis}={int(dc)}")

def _nudge(g, axis: str, counts: int) -> None:
    # PR X=…, BGX, AMX
    _cmd(g, f"PR {axis}={int(counts)}")
    _cmd(g, f"BG{axis}")
    _cmd(g, f"AM{axis}")

def probe_axis(
    g,
    axis: str,
    sp: int = 10000,
    ac: int = 100000,
    dc: int = 100000,
    nudge_counts: int = 100,
    settle_back: bool = True,
) -> Dict[str, Union[bool, int, float, Dict[str,int], str]]:
    """
    Discovery probe for one axis using:
      SHX; DP X=0; SP/AC/DC; PR X=±nudge; BGX; AMX; TPX; MG _TSX; TAX
    Returns dict with presence, TP deltas, TS/TA snapshots, and notes.
    """
    axis = axis.upper()
    result = {
        "axis": axis,
        "present": False,
        "tp_after_pos": float("nan"),
        "tp_after_neg": float("nan"),
        "ta": 0,
        "ts": 0,
        "ts_bits": {},
        "notes": "",
    }

    # SHX: enable servo here (clears position error)
    _cmd(g, f"SH{axis}")

    # DP X=0: define current position to zero
    _cmd(g, f"DP {axis}=0")

    # Initial profile
    _set_profile(g, axis, sp=sp, ac=ac, dc=dc)

    # Positive nudge
    _nudge(g, axis, +abs(nudge_counts))
    tp_pos = _get_tp(g, axis)
    ts_pos = _get_ts(g, axis)
    ta_pos = _get_ta(g, axis)

    # Negative nudge (back the other way)
    _nudge(g, axis, -abs(nudge_counts))
    tp_neg = _get_tp(g, axis)
    ts_neg = _get_ts(g, axis)
    ta_neg = _get_ta(g, axis)

    # Decide presence: saw motion in encoder and no amp fault
    moved_enough = abs(tp_pos) >= 0.9 * abs(nudge_counts)
    no_amp_fault = (ta_pos | ta_neg) == 0
    motor_on = (((ts_pos | ts_neg) >> 5) & 1) == 0  # TS bit5==0 ⇒ motor ON

    present = bool(moved_enough and no_amp_fault and motor_on)

    # Optionally settle back to 0 reference
    if settle_back:
        _cmd(g, f"PR {axis}={int(-_get_tp(g, axis))}")  # relative back to zero-ish
        _cmd(g, f"BG{axis}")
        _cmd(g, f"AM{axis}")

    # Final snapshots
    ts = _get_ts(g, axis)
    ta = _get_ta(g, axis)

    # Fill result
    result["present"] = present
    result["tp_after_pos"] = tp_pos
    result["tp_after_neg"] = tp_neg
    result["ta"] = int(ta)
    result["ts"] = int(ts)
    result["ts_bits"] = _decode_ts(ts)

    notes = []
    if not moved_enough:
        notes.append(f"TP change too small after +{nudge_counts} (TP+={tp_pos:.0f}).")
    if not motor_on:
        notes.append("Motor appears OFF (TS bit5=1).")
    if ta != 0:
        notes.append(f"Amplifier error (TA={ta}).")
    # Check limits: bits 3/2 are 1 when INACTIVE (with typical CN config)
    bits = _decode_ts(ts)
    if bits["fwd_limit_inact"] == 0:
        notes.append("Forward limit ACTIVE (TS bit3=0).")
    if bits["rev_limit_inact"] == 0:
        notes.append("Reverse limit ACTIVE (TS bit2=0).")
    result["notes"] = " ".join(notes)

    return result

def discover_axes(
    g,
    axes: AxisList = ("A","B","C","D"),
    sp: int = 10000,
    ac: int = 100000,
    dc: int = 100000,
    nudge_counts: int = 100,
) -> Dict[str, Dict]:
    """
    Runs discovery over the specified axes using only:
      SHX, DP X=0, SP/AC/DC, PR X=…, BGX, AMX, TPX, MG _TSX, TAX
    Returns a dict keyed by axis with probe results and a convenience list of active axes.
    """
    ax_list = _norm_axes(axes)
    results: Dict[str, Dict] = {}
    active = []
    for a in ax_list:
        r = probe_axis(
            g, a, sp=sp, ac=ac, dc=dc, nudge_counts=nudge_counts, settle_back=True
        )
        results[a] = r
        if r["present"]:
            active.append(a)

    results["active_axes"] = active  # convenience
    return results
