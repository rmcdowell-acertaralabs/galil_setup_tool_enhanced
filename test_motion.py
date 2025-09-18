# test_motion.py
# Requires an open gclib handle `g` (e.g., g = gclib.py(); g.GOpen("..."))
# Formatting honors your style:
#   - Begin motion:  BGA (no space)
#   - Absolute move: PA A=1000 (with space)
#   - Query pos:     TPA  (no space)
#   - Jog:           JGA=5000 (no space)

from typing import Dict, List, Iterable, Tuple, Union

AxisList = Union[Iterable[str], str]

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D"))
    if not axes:
        raise ValueError("No valid axes (A-D).")
    return axes

def _cmd(g, cmd: str) -> str:
    r = g.GCommand(cmd)
    return r.strip() if isinstance(r, str) else ""

def _num(s: str) -> float:
    try:
        return float(s.strip())
    except Exception:
        return float("nan")

def _tp(g, axis: str) -> float:
    return _num(_cmd(g, f"TP{axis}"))

def _set_profile(g, axis: str, sp: int, ac: int, dc: int) -> None:
    # SP A=…, AC A=…, DC A=…
    _cmd(g, f"SP {axis}={int(sp)}")
    _cmd(g, f"AC {axis}={int(ac)}")
    _cmd(g, f"DC {axis}={int(dc)}")

def _begin_and_wait(g, axis: str) -> None:
    _cmd(g, f"BG{axis}")
    _cmd(g, f"AM{axis}")

def _move_and_verify(g, axis: str, target: int, tol_counts: int) -> Dict[str, Union[float, int, bool]]:
    """
    Sequence:
      PA X=target
      BGX
      AMX
      TPA → error = |TPA - target|
      MG "..." and MG @ABS[...] for controller-side trace
    """
    # Announce from controller
    _cmd(g, f'MG "AX {axis} -> {target} BEGIN"')

    # Absolute target and run
    _cmd(g, f"PA {axis}={int(target)}")
    _begin_and_wait(g, axis)

    # Measure
    tp = _tp(g, axis)
    err = abs(tp - target)
    passed = err <= tol_counts

    # Controller-side message including @ABS usage (as requested)
    # Example: MG "ERR:", @ABS[TPA-1000]
    _cmd(g, f'MG "AX {axis} DONE TPL=",TP{axis}')
    _cmd(g, f"MG \"AX {axis} ERR=\", @ABS[TP{axis}-{int(target)}]")

    # Host-side result
    return {
        "axis": axis,
        "target": target,
        "tp": tp,
        "error": err,
        "pass": passed
    }

def optional_jog(g, axis: str, jg_speed: int = 5000, dwell_ms: int = 500) -> None:
    """
    Exercise velocity control briefly:
      JGX=<speed>, BGX, WT <ms>, STX, AMX
    """
    _cmd(g, f"JG{axis}={int(jg_speed)}")  # e.g., JGA=5000
    _cmd(g, f"BG{axis}")
    _cmd(g, f"WT {int(dwell_ms)}")
    _cmd(g, f"ST{axis}")
    _cmd(g, f"AM{axis}")
    _cmd(g, f'MG "AX {axis} JOG COMPLETE TPL=",TP{axis}')

def run_motion_tests(
    g,
    axes: AxisList,
    profiles: List[Dict[str, int]],
    target_offsets: List[int],
    tol_counts: int = 5,
    include_jog: bool = False,
    jog_speed: int = 5000,
    jog_dwell_ms: int = 500,
) -> Dict[str, List[Dict[str, Union[float, int, bool]]]]:
    """
    For each axis:
      - Capture base = TPX
      - For each profile {sp,ac,dc}:
           SP/AC/DC
           For each offset in target_offsets:
               absolute_target = base + offset
               PA/BG/AM → verify ±tol_counts
           (optional) brief jog segment JGX/STX
    Uses only: SP, AC, DC, PA, BGX, AMX, TPX, @ABS, MG, (optional JGX, STX, WT)
    """
    ax_list = _norm_axes(axes)
    summary: Dict[str, List[Dict[str, Union[float, int, bool]]]] = {}

    for axis in ax_list:
        results: List[Dict[str, Union[float, int, bool]]] = []

        # Base position (no DP used in this section)
        base = _tp(g, axis)
        _cmd(g, f'MG "== AX {axis} START base=",TP{axis}')

        for i, prof in enumerate(profiles, start=1):
            sp = int(prof.get("sp", 128000))
            ac = int(prof.get("ac", 2560000))
            dc = int(prof.get("dc", 2560000))

            # Announce profile
            _cmd(g, f'MG "AX {axis} PROFILE {i} SP={sp} AC={ac} DC={dc}"')

            # Apply profile
            _set_profile(g, axis, sp=sp, ac=ac, dc=dc)

            # Run through targets (absolute positions based on current base)
            for off in target_offsets:
                target = int(round(base + off))
                res = _move_and_verify(g, axis, target, tol_counts)
                # Host-side, also log pass/fail quickly
                _cmd(g, f'MG "AX {axis} @ {target} {"PASS" if res["pass"] else "FAIL"}"')
                results.append(res)

            # Optional jog exercise between profiles
            if include_jog:
                optional_jog(g, axis, jg_speed=jog_speed, dwell_ms=jog_dwell_ms)

        # Finish axis
        _cmd(g, f'MG "== AX {axis} COMPLETE"')
        summary[axis] = results

    return summary
