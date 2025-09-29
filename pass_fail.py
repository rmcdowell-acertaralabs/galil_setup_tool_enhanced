# pass_fail.py
# Requires an open gclib handle `g`
# Uses controller-side IF/ELSE/ENDIF + @ABS[...] + MG for PASS/FAIL.

from typing import Iterable, Tuple, Dict, Union, List

Axis = str
Check = Dict[str, Union[str, int]]  # {"axis":"A","target":1000,"tol":5}

def build_pf_snippet(axis: Axis, target: int, tol: int) -> str:
    """
    Return a DMC code block that:
      - echoes the current position
      - computes |_TPX - target|
      - prints PASS/FAIL with error using only MG, IF/ELSE/ENDIF, @ABS[]
    Intended to run *after* the axis has reached the commanded absolute target.
    """
    a = axis.upper()
    t = int(target)
    tol = int(tol)
    return (
        f'MG "PF AX {a} TGT={t} TPL=",_TP{a}\n'
        f'IF (@ABS[_TP{a}-{t}] <= {tol})\n'
        f' MG "PF AX {a} PASS ERR=",@ABS[_TP{a}-{t}]\n'
        f'ELSE\n'
        f' MG "PF AX {a} FAIL ERR=",@ABS[_TP{a}-{t}]\n'
        f'ENDIF\n'
    )

def build_pf_program(checks: Iterable[Check], label: str = "#PFCHK") -> str:
    """
    Build a complete, runnable DMC program with PASS/FAIL checks for multiple axes/targets.
    Each item in `checks` is {"axis": "A|B|C|D", "target": <int>, "tol": <int>}.
    """
    lines = [label, 'MG "PF START"']
    for c in checks:
        lines.append(build_pf_snippet(c["axis"], int(c["target"]), int(c["tol"])))
    lines.append('MG "PF END"')
    lines.append("EN")
    return "\n".join(lines)

def run_pf_checks(
    g,
    checks: Iterable[Check],
    thread: int = 7,
    label: str = "#PFCHK",
) -> None:
    """
    Download and execute the one-shot PASS/FAIL program.
    Controller prints PASS/FAIL lines via MG.
    """
    prog = build_pf_program(checks, label=label)
    # Download & execute
    g.GProgramDownload(prog)
    g.GCommand(f"XQ {label},{thread}")
    # Note: MG lines are sent as unsolicited messages by the controller.
    # If you want to also collect host-side results, you can re-query _TPA etc. after moves.

# ---- Optional convenience: integrate after a host-driven PA/BG/AM move ----

def move_and_pf(
    g,
    axis: Axis,
    target: int,
    tol: int = 5,
    sp: int = None,
    ac: int = None,
    dc: int = None,
    thread: int = 7,
) -> None:
    """
    (Host-driven) Set profile (optional), do an absolute move, wait, then run controller-side
    PASS/FAIL (IF/ELSE/ENDIF + @ABS + MG).
    """
    ax = axis.upper()
    if sp is not None: g.GCommand(f"SP {ax}={int(sp)}")
    if ac is not None: g.GCommand(f"AC {ax}={int(ac)}")
    if dc is not None: g.GCommand(f"DC {ax}={int(dc)}")
    g.GCommand(f"PA {ax}={int(target)}")
    g.GCommand(f"BG{ax}")
    g.GCommand(f"AM{ax}")
    run_pf_checks(g, [{"axis": ax, "target": int(target), "tol": int(tol)}], thread=thread)
