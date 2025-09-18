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
      1) PA X=0   (command absolute zero)
      2) BGX      (begin)
      3) AMX      (wait for profile complete)
      4) MOX      (optional: motor off)

    Notes:
      - Assumes absolute 0 is a safe park point for each axis.
      - No extra commands are issued beyond the four specified.
    """
    ax_list = _norm_axes(axes)

    # 1) Set absolute targets to 0 for all axes
    for a in ax_list:
        _cmd(g, f"PA {a}=0")

    # 2) Begin each axis motion
    for a in ax_list:
        _cmd(g, f"BG{a}")

    # 3) Wait for each axis to complete its profile
    for a in ax_list:
        _cmd(g, f"AM{a}")

    # 4) Optionally turn motors off per axis
    if power_off:
        for a in ax_list:
            _cmd(g, f"MO{a}")
