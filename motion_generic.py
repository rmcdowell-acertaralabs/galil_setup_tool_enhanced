# motion_generic.py
"""
Generic motion testing helpers that work for both servo and stepper axes.
Now integrates command validation via DMC-4103 validator prior to issuing
commands, to ensure syntax/value correctness consistent with controller rules.
"""

from typing import Tuple
from command_validator import DMC4103CommandValidator

_validator = DMC4103CommandValidator()

def _v_or_raise(cmd: str) -> None:
    v = _validator.validate_command(cmd)
    if not v.valid:
        raise ValueError(f"Invalid command '{cmd}': {v.error_message or 'rejected by validator'}")

def move_absolute_and_check(io, axis: str, target: int, sp=5000, ac=25000, dc=25000, tol=5) -> Tuple[int, int, bool]:
    """
    Move to absolute position and check accuracy.
    Uses validator to check SP/AC/DC/PA/BG/AM/TP before sending.
    """
    axis_u = (axis or "").upper()

    # Validate profile and motion commands (SPA/ACA/DCA/PAA/BGA/AMA/TPA)
    _v_or_raise(f"SP{axis_u}={int(sp)}")
    _v_or_raise(f"AC{axis_u}={int(ac)}")
    _v_or_raise(f"DC{axis_u}={int(dc)}")
    _v_or_raise(f"PA{axis_u}={int(target)}")
    _v_or_raise(f"BG{axis_u}")
    _v_or_raise(f"AM{axis_u}")
    _v_or_raise(f"TP{axis_u}")

    # Execute
    io.sp(axis_u, sp)
    io.ac(axis_u, ac)
    io.dc(axis_u, dc)
    io.pa(axis_u, target)
    io.bg(axis_u)
    io.am(axis_u)

    # Check final position
    pos = io.tp(axis_u)
    err = abs(pos - int(target))
    return pos, err, (err <= tol)

def move_relative_and_check(io, axis: str, distance: int, sp=5000, ac=25000, dc=25000, tol=5) -> Tuple[int, int, bool]:
    """
    Move relative distance and check accuracy.
    Uses validator to check SP/AC/DC/PR/BG/AM/TP before sending.
    """
    axis_u = (axis or "").upper()

    # Snapshot initial position (validate TP)
    _v_or_raise(f"TP{axis_u}")
    initial_pos = io.tp(axis_u)
    target = int(initial_pos) + int(distance)

    # Validate profile and motion commands
    _v_or_raise(f"SP{axis_u}={int(sp)}")
    _v_or_raise(f"AC{axis_u}={int(ac)}")
    _v_or_raise(f"DC{axis_u}={int(dc)}")
    _v_or_raise(f"PR{axis_u}={int(distance)}")
    _v_or_raise(f"BG{axis_u}")
    _v_or_raise(f"AM{axis_u}")
    _v_or_raise(f"TP{axis_u}")

    # Execute
    io.sp(axis_u, sp)
    io.ac(axis_u, ac)
    io.dc(axis_u, dc)
    io.pr(axis_u, distance)
    io.bg(axis_u)
    io.am(axis_u)

    # Check final position
    pos = io.tp(axis_u)
    err = abs(int(pos) - int(target))
    return pos, err, (err <= tol)
