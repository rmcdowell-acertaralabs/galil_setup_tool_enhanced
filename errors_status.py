# errors_status.py
# Requires an open gclib handle `g`
# Commands used: TC, TE, TA{axis}, TB, MG _TS{axis}, SC {axis}, AZ1/AZ2, TW{axis}, MG _TW{axis}

from typing import Dict, Tuple, Iterable, Union

AxisList = Union[Iterable[str], str]

# ---- helpers ----

def _norm_axes(axes: AxisList):
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D"))
    if not axes:
        raise ValueError("No valid axes (A-D).")
    return axes

def _cmd(g, s: str) -> str:
    r = g.GCommand(s)
    return r.strip() if isinstance(r, str) else ""

def _num(s: str) -> float:
    try:
        return float(s.strip())
    except Exception:
        return float("nan")

# ---- TC (Tell Error Code) ----

# Subset of TC error text (covers the most common & your list)
_TC_TEXT = {
    1:"Unrecognized command",
    2:"Command only valid from program",
    3:"Command not valid in program",
    4:"Operand error",
    5:"Input buffer full",
    6:"Number out of range",
    7:"Command not valid while running",
    8:"Command not valid while not running",
    9:"Variable error",
    10:"Empty program line or undefined label",
    11:"Invalid label or line number",
    12:"Subroutine more than 16 deep",
    13:"JG only valid when running in jog mode",
    14:"EEPROM check sum error",
    15:"EEPROM write error",
    16:"IP incorrect sign during position move / forced decel",
    17:"ED/BN/DL not valid while program running",
    18:"Command not valid when contouring",
    19:"Application strand already executing",
    20:"Begin not valid with motor off",
    21:"Begin not valid while running",
    22:"Begin not possible due to Limit Switch",
    24:"Begin not valid because no sequence defined",
    28:"S operand not valid",
    29:"Not valid during coordinated move",
    30:"Sequence segment too short",
    31:"Total move distance in a sequence > 2B",
    32:"Segment buffer full",
    33:"VP/CR cannot be mixed with LI",
    39:"No time specified",
    41:"Contour record range error",
    42:"Contour data sent too slowly",
    46:"Gear axis both master and follower",
    50:"Not enough fields",
    51:"Question mark not valid",
    52:"Missing quote or string too long",
    53:"Error in {}",
    54:"Question mark part of string",
    55:"Missing [ or []",
    56:"Array index invalid or out of range",
    57:"Bad function or array",
    58:"Bad command response",
    59:"Mismatched parentheses",
    60:"Download error - line too long/too many lines",
    61:"Duplicate or bad label",
    62:"Too many labels",
    63:"IF without ENDIF",
    66:"Array space full",
    67:"Too many arrays or variables",
    80:"Record mode already running",
    81:"No array or source specified",
    82:"Undefined array",
    83:"Not a valid number",
    84:"Too many elements",
    90:"Only A B C D valid operand",
    97:"Bad binary command format",
    98:"Binary commands not valid in app program",
    99:"Bad binary command number",
    100:"Not valid when running ECAM",
    101:"Improper index into ET",
    102:"No master axis defined for ECAM",
    103:"Master axis modulus > 256 EP",
    104:"Not valid when axis performing ECAM",
    105:"EB1 must be given first",
    106:"Privilege violation",
    110:"No hall effect sensors detected",
    111:"Axis must be made brushless by BA",
    112:"BZ timeout",
    113:"No movement in BZ",
    114:"BZ runaway",
    118:"Controller has GL1600 not GL1800",
    119:"Not valid for axis configured as stepper",
    120:"Bad Ethernet transmit",
    121:"Bad Ethernet packet received",
    123:"TCP lost sync",
    124:"Ethernet handle already in use",
    125:"No ARP response from IP address",
    126:"Closed Ethernet handle",
    127:"Illegal Modbus function code",
    128:"IP address not valid",
    130:"Remote IO command error",
    131:"Serial port timeout",
    132:"Analog inputs not present",
    133:"Command not valid when locked / must be UDP",
    134:"All motors must be in MO",
    135:"Motor must be in MO",
    136:"Invalid password",
    137:"Invalid lock setting",
    138:"Passwords not identical",
    140:"Serial encoder error",
    141:"Feature not supported",
    143:"TM timed out",
    144:"Incompatible with encoder type",
    160:"BX failure",
    161:"Sine amp axis not initialized",
    163:"IA not valid with DHCP enabled",
    164:"Exceeded max sequence length, use BGS/BGT",
    165:"Cannot have both SINE and SSI",
    166:"Unable to set analog output",
}

def read_tc(g, with_message: bool = True) -> Dict[str, Union[int, str]]:
    """
    TC: returns the last command/programming error.
    NOTE: 'TC' (or 'TC n') *clears* the code; operand _TC does not.
    """
    # Peek via operand (does not clear)
    code_peek = int(_num(_cmd(g, "MG _TC")))
    result = {"tc_peek": code_peek, "code": 0, "text": ""}
    if with_message:
        # Pull + clear, with text
        s = _cmd(g, "TC 1")  # e.g. "1       Unrecognized command"
        if s:
            # Split at first whitespace group
            parts = s.split(None, 1)
            code = int(parts[0]) if parts else 0
            txt = parts[1].strip() if len(parts) > 1 else _TC_TEXT.get(code, "")
            result.update({"code": code, "text": txt or _TC_TEXT.get(code, "")})
    else:
        code = int(_num(_cmd(g, "TC 0")))
        result.update({"code": code, "text": _TC_TEXT.get(code, "")})
    return result

# ---- TB (controller status) ----

def read_tb(g) -> Dict[str, Union[int, Dict[str,int]]]:
    """
    TB: controller status byte + decoded flags.
    """
    v = int(_num(_cmd(g, "TB")))  # returns decimal
    return {
        "tb": v,
        "flags": {
            "executing_program": (v >> 7) & 1,
            "contouring":        (v >> 5) & 1,
            "in_error_routine":  (v >> 4) & 1,
            "input_int_enabled": (v >> 3) & 1,
            "in_input_isr":      (v >> 2) & 1,
            "echo_on":           (v >> 0) & 1,
        },
    }

# ---- TS (axis switches) ----

def read_ts(g, axis: str) -> Dict[str, Union[int, Dict[str,int]]]:
    """
    TS: axis switch/status byte via MG _TSX.
    """
    axis = axis.upper()
    v = int(_num(_cmd(g, f"MG _TS{axis}")))
    bits = {
        "in_motion":        (v >> 7) & 1,
        "error_limit":      (v >> 6) & 1,
        "motor_off":        (v >> 5) & 1,
        # bit4 reserved
        "fwd_limit_inact":  (v >> 3) & 1,  # 1 = inactive (typical CN config)
        "rev_limit_inact":  (v >> 2) & 1,  # 1 = inactive
        "home_switch":      (v >> 1) & 1,
        "latch_occurred":   (v >> 0) & 1,
    }
    return {"axis": axis, "ts": v, "bits": bits}

# ---- TE (position error), TA{X} (amplifier status) ----

def read_te(g, axis: str) -> int:
    """TE: instantaneous position error (counts)."""
    axis = axis.upper()
    return int(_num(_cmd(g, f"TE{axis}")))

def read_ta(g, axis: str) -> int:
    """
    TA{X}: amplifier error status (decimal bitfield).
    Note: meanings depend on amplifier model; we report the exact number.
    """
    axis = axis.upper()
    return int(_num(_cmd(g, f"TA{axis}")))  # e.g., TAA, TAB...

# ---- SC (stop code) ----

_SC_TEXT = {
    0:"Running (independent)",
    1:"Stopped at commanded position",
    2:"Stopped by FWD limit (FL)",
    3:"Stopped by REV limit (BL)",
    4:"Stopped by ST command",
    6:"Stopped by Abort input",
    7:"Stopped by AB command",
    8:"Stopped by Off-on-Error (OE1)",
    9:"Stopped after Find Edge (FE)",
    10:"Stopped after Homing (HM) or Find Index (FI)",
    11:"Stopped by selective abort",
    12:"Stopped by encoder failure (OA1)",
    15:"Amplifier fault (internal drives)",
    16:"Stepper position maintenance error",
    30:"Running in PVT",
    31:"PVT completed normally",
    32:"PVT buffer empty",
    50:"Contour running",
    51:"Contour stopped",
    60:"ECAM running",
    61:"ECAM stopped",
    70:"EtherCAT communication failure",
    71:"EtherCAT drive fault",
    99:"MC timeout",
    100:"Vector sequence running",
    101:"Vector sequence stopped",
}

def read_sc(g, axis: str) -> Dict[str, Union[int,str]]:
    axis = axis.upper()
    v = int(_num(_cmd(g, f"SC {axis}")))
    return {"axis": axis, "sc": v, "text": _SC_TEXT.get(v, "")}

# ---- AZ (amp errors) and TW (MC timeout) ----

def az_enable_enhanced(g, enable: bool = True) -> int:
    """AZ2 enable enhanced error reporting; returns _AZ2 (0/1)."""
    if enable:
        _cmd(g, "AZ2")
    return int(_num(_cmd(g, "MG _AZ2")))

def az_clear_latched(g) -> None:
    """
    AZ1 to clear latched amplifier errors.
    NOTE: Per docs, axes should be MO before AZ1. This helper only issues AZ1.
    """
    _cmd(g, "AZ1")
    _cmd(g, "WT 2")  # brief settle

def set_tw(g, axis: str, ms: int) -> int:
    """
    TW{axis}=ms : set MC timeout (ms). Returns the applied _TW{axis}.
    Use -1 to disable.
    """
    axis = axis.upper()
    _cmd(g, f"TW{axis}={int(ms)}")
    return int(_num(_cmd(g, f"MG _TW{axis}")))

def get_tw(g, axis: str) -> int:
    axis = axis.upper()
    return int(_num(_cmd(g, f"MG _TW{axis}")))

# ---- One-shot full snapshot ----

def collect_error_status(g, axes: AxisList) -> Dict[str, dict]:
    """
    Grab a comprehensive status snapshot using only TC, TE, TA(X), TB, _TSX, SC.
    Also returns parsed bits for quick diagnostics.
    """
    ax = _norm_axes(axes)

    # Controller/global
    tc = read_tc(g, with_message=True)
    tb = read_tb(g)

    # Per-axis details
    te = {a: read_te(g, a) for a in ax}
    sc = {a: read_sc(g, a) for a in ax}
    ts = {a: read_ts(g, a) for a in ax}
    ta = {a: read_ta(g, a) for a in ax}

    return {
        "TC": tc,
        "TB": tb,
        "TE": te,
        "SC": sc,
        "TS": ts,
        "TA": ta,
    }

# ---- Convenience: dump nice text (no extra commands, just formatting) ----

def format_status_report(snapshot: Dict[str, dict]) -> str:
    """
    Turn collect_error_status() into a readable multi-line string.
    (This function does not talk to the controller.)
    """
    lines = []
    tc = snapshot["TC"]
    if tc.get("code", 0):
        lines.append(f"TC: {tc['code']} {tc.get('message','').strip()}")
    else:
        lines.append("TC: 0 (no controller command error)")

    tb = snapshot["TB"]
    bits = tb["flags"]
    lines.append(f"TB: {tb['tb']}  exec={bits['executing_program']} contour={bits['contouring']} err/lim_rtn={bits['in_error_routine']} input_isr={bits['in_input_isr']} echo={bits['echo_on']}")

    te = snapshot["TE"]
    for a, e in te.items():
        sc = snapshot["SC"][a]
        ts = snapshot["TS"][a]
        ta = snapshot["TA"][a]
        tsb = ts["bits"]
        lines.append(f"{a}: TE={e}  SC={sc['sc']}({sc['text']})  TS={ts['ts']}[mot_off={tsb['motor_off']} fwd_lim_inact={tsb['fwd_limit_inact']} rev_lim_inact={tsb['rev_limit_inact']}]  TA={ta}")
        # If TA nonzero, show common flags:
        if ta:
            # Decode TA bits (generic)
            faults = []
            if ta & 1:  faults.append("OC")
            if ta & 2:  faults.append("OV")
            if ta & 4:  faults.append("OT")
            if ta & 8:  faults.append("UV")
            if faults:
                lines.append(f"    TA bits: {','.join(faults)}  (raw=0b{ta:08b})")
    return "\n".join(lines)
