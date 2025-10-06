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
    try:
        r = g.GCommand(s)
        return r.strip() if isinstance(r, str) else ""
    except Exception as e:
        error_str = str(e).lower()
        if any(conn_error in error_str for conn_error in ["connection", "timeout", "network", "socket", "ethernet", "not connected"]):
            # Return empty string for connection errors to avoid crashing the status check
            return ""
        else:
            # Re-raise non-connection errors
            raise

def _num(s: str) -> float:
    try:
        return float(s.strip())
    except Exception:
        return float("nan")

def _safe_int(s: str, default: int = 0) -> int:
    """Safely convert string to int, handling NaN and invalid values"""
    try:
        val = _num(s)
        if str(val).lower() == 'nan' or str(val).lower() == 'inf':
            return default
        return int(val)
    except (ValueError, TypeError):
        return default

# ---- TC (Tell Error Code) ----

# Complete TC error text from command_validator.py
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
    16:"IP incorrect sign during position move or IP given during forced deceleration",
    17:"ED, BN and DL not valid while program running",
    18:"Command not valid when contouring",
    19:"Application strand already executing",
    20:"Begin not valid with motor off",
    21:"Begin not valid while running",
    22:"Begin not possible due to Limit Switch",
    24:"Begin not valid because no sequence defined",
    28:"S operand not valid",
    29:"Not valid during coordinated move",
    30:"Sequence Segment Too Short",
    31:"Total move distance in a sequence > 2 billion",
    32:"Segment buffer full",
    33:"VP or CR commands cannot be mixed with LI commands",
    39:"No time specified",
    41:"Contouring record range error",
    42:"Contour data being sent too slowly",
    46:"Gear axis both master and follower",
    50:"Not enough fields",
    51:"Question mark not valid",
    52:"Missing \" or string too long",
    53:"Error in {}",
    54:"Question mark part of string",
    55:"Missing [ or []",
    56:"Array index invalid or out of range",
    57:"Bad function or array",
    58:"Bad command response",
    59:"Mismatched parentheses",
    60:"Download error - line too long or too many lines",
    61:"Duplicate or bad label",
    62:"Too many labels",
    63:"IF statement without ENDIF",
    66:"Array space full",
    67:"Too many arrays or variables",
    80:"Record mode already running",
    81:"No array or source specified",
    82:"Undefined Array",
    83:"Not a valid number",
    84:"Too many elements",
    90:"Only A B C D valid operand",
    97:"Bad Binary Command Format",
    98:"Binary Commands not valid in application program",
    99:"Bad binary command number",
    100:"Not valid when running ECAM",
    101:"Improper index into ET",
    102:"No master axis defined for ECAM",
    103:"Master axis modulus greater than 256 EP value",
    104:"Not valid when axis performing ECAM",
    105:"EB1 command must be given first",
    106:"Privilege Violation",
    110:"No hall effect sensors detected",
    111:"Must be made brushless by BA command",
    112:"BZ command timeout",
    113:"No movement in BZ command",
    114:"BZ command runaway",
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
    131:"Serial Port Timeout",
    132:"Analog inputs not present",
    133:"Command not valid when locked / Handle must be UDP",
    134:"All motors must be in MO for this command",
    135:"Motor must be in MO",
    136:"Invalid Password",
    137:"Invalid lock setting",
    138:"Passwords not identical",
    140:"Serial encoder error",
    141:"Feature not supported",
    143:"TM timed out",
    144:"Incompatible with encoder type",
    160:"BX failure",
    161:"Sine amp axis not initialized",
    163:"IA command not valid when DHCP mode enabled",
    164:"Exceeded maximum sequence length, BGS or BGT is required",
    165:"Cannot have both SINE and SSI feedback enabled at once",
    166:"Unable to set analog output",
}

def read_tc(g, with_message: bool = True) -> Dict[str, Union[int, str]]:
    """
    TC: returns the last command/programming error.
    NOTE: 'TC' (or 'TC n') *clears* the code; operand _TC does not.
    """
    result = {"tc_peek": 0, "code": 0, "text": ""}
    try:
        # Peek via operand (does not clear)
        tc_response = _cmd(g, "MG _TC")
        if tc_response:
            code_peek = _safe_int(tc_response)
            result["tc_peek"] = code_peek
        
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
            tc0_response = _cmd(g, "TC 0")
            if tc0_response:
                code = _safe_int(tc0_response)
                result.update({"code": code, "text": _TC_TEXT.get(code, "")})
    except Exception as e:
        # If we can't read TC, return default values
        result["text"] = f"Could not read TC: {e}"
    
    return result

# ---- TB (controller status) ----

def read_tb(g) -> Dict[str, Union[int, Dict[str,int]]]:
    """
    TB: controller status byte + decoded flags.
    Bit definitions from command_validator.py:
    Bit 7: Executing application program
    Bit 6: N/A
    Bit 5: Contouring
    Bit 4: Executing error or limit switch routine
    Bit 3: Input Interrupt enabled
    Bit 2: Executing input interrupt routine
    Bit 1: N/A
    Bit 0: Echo on
    """
    v = _safe_int(_cmd(g, "TB"))  # returns decimal
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
    Bit definitions from command_validator.py:
    Bit 7: Axis in motion
    Bit 6: Position error exceeds error limit
    Bit 5: Motor off
    Bit 4: Reserved (0)
    Bit 3: Forward Limit switch inactive
    Bit 2: Reverse Limit switch inactive
    Bit 1: Home switch status
    Bit 0: Position Latch has occurred
    """
    axis = axis.upper()
    v = _safe_int(_cmd(g, f"MG _TS{axis}"))
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
    return _safe_int(_cmd(g, f"TE{axis}"))

def read_ta(g, axis: str) -> int:
    """
    DMC-41x3 safe amp-fault read. Avoid TA{axis} (unsupported).
    _TA0.._TA3 are bitfields; mask this axis' bit and OR the banks.
    Returns 0/1 (no fault / fault present for this axis).
    """
    axis = axis.upper()
    idx = "ABCD".find(axis)
    if idx < 0:
        return 0
    try:
        # Safely convert to int, handling NaN and invalid values
        def safe_int(val):
            try:
                fval = float(val)
                if str(fval).lower() == 'nan' or str(fval).lower() == 'inf':
                    return 0
                return int(fval)
            except (ValueError, TypeError):
                return 0
        
        b0 = safe_int(_cmd(g, "MG _TA0") or "0")
        b1 = safe_int(_cmd(g, "MG _TA1") or "0")
        b2 = safe_int(_cmd(g, "MG _TA2") or "0")
        b3 = safe_int(_cmd(g, "MG _TA3") or "0")
        combined = b0 | b1 | b2 | b3
        return (combined >> idx) & 1
    except Exception:
        return 0

# ---- SC (stop code) ----

_SC_TEXT = {
    0:"Motors are running, independent mode",
    1:"Motors decelerating or stopped at commanded independent position",
    2:"Decelerating or stopped by FWD limit switch or soft limit FL",
    3:"Decelerating or stopped by REV limit switch or soft limit BL",
    4:"Decelerating or stopped by Stop Command (ST)",
    6:"Stopped by Abort input",
    7:"Stopped by Abort command (AB)",
    8:"Decelerating or stopped by Off on Error (OE1)",
    9:"Stopped after finding edge (FE)",
    10:"Stopped after homing (HM) or Find Index (FI)",
    11:"Stopped by selective abort input",
    12:"Decelerating or stopped by encoder failure (OA1)",
    15:"Amplifier Fault (For controllers with internal drives)",
    16:"Stepper position maintenance error",
    30:"Running in PVT mode",
    31:"PVT mode completed normally",
    32:"PVT mode exited because buffer is empty",
    50:"Contour Running",
    51:"Contour Stopped",
    60:"ECAM Running",
    61:"ECAM Stopped",
    70:"Stopped due to EtherCAT communication failure",
    71:"Stopped due to EtherCAT drive fault",
    99:"MC timeout",
    100:"Vector Sequence running",
    101:"Vector Sequence stopped",
}

def read_sc(g, axis: str) -> Dict[str, Union[int,str]]:
    axis = axis.upper()
    v = _safe_int(_cmd(g, f"SC {axis}"))
    return {"axis": axis, "sc": v, "text": _SC_TEXT.get(v, "")}

# ---- AZ (amp errors) and TW (MC timeout) ----

def az_enable_enhanced(g, enable: bool = True) -> int:
    """AZ2 enable enhanced error reporting; returns _AZ2 (0/1)."""
    if enable:
        _cmd(g, "AZ2")
    return _safe_int(_cmd(g, "MG _AZ2"))

def az_clear_latched(g) -> None:
    """
    AZ1 to clear latched amplifier errors.
    NOTE: Per docs, axes should be MO before AZ1. This helper only issues AZ1.
    """
    _cmd(g, "AZ1")
    _cmd(g, "WT 2,0")  # Wait 2ms - brief settle

def set_tw(g, axis: str, ms: int) -> int:
    """
    TW{axis}=ms : set MC timeout (ms). Returns the applied _TW{axis}.
    Use -1 to disable.
    """
    axis = axis.upper()
    _cmd(g, f"TW{axis}={int(ms)}")
    return _safe_int(_cmd(g, f"MG _TW{axis}"))

def get_tw(g, axis: str) -> int:
    axis = axis.upper()
    return _safe_int(_cmd(g, f"MG _TW{axis}"))

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
