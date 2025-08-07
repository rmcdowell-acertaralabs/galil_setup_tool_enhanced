import logging

logger = logging.getLogger(__name__)

def try_command(controller, label, command, fallback=None):
    """
    Attempts to run a command; returns “Label: value” or None on unsupported/error responses.
    """
    try:
        resp = controller.send_command(command).strip()
        if resp in ("?", "ERROR", "error", "Unsupported", ""):
            if fallback:
                return try_command(controller, label, fallback)
            return None
        return f"{label}: {resp}"
    except Exception as e:
        logger.debug(f"try_command {command!r} failed: {e}")
        return None

def get_controller_info(controller):
    """
    Static snapshot of firmware, serial, all-axis positions, error codes, etc.
    """
    commands = [
        ("Firmware",            "MG _FW",  "MG _ID"),
        ("Serial",              "MG _BN",  None),
        ("All Positions",       "TP",      None),
        ("Torque Command",      "MG _TC",  None),
        ("Error Code",          "MG _TE",  None),
        ("Limit Switch Status", "MG _LF",  None),
        ("Motion Status",       "MG _BG",  None),
        ("IP Address",          "MG _IP",  None),
    ]

    out = []
    for label, cmd, fb in commands:
        res = try_command(controller, label, cmd, fb)
        if res:
            out.append(res)
    return "\n".join(out)

def get_diagnostics(controller):
    """
    Live per-axis diagnostics: position and TS bit.
    """
    lines = []
    for axis in ("A", "B", "C", "D"):
        # 1) Position on this axis
        try:
            pos = controller.send_command(f"TP {axis}").strip()
            lines.append(f"Position {axis}: {pos}")
        except Exception as e:
            lines.append(f"Position {axis}: error {e}")

        # 2) TS bit (motion status) on this axis
        try:
            ts = controller.send_command(f"MG _TS{axis}").strip()
            lines.append(f"TS{axis}: {ts}")
        except Exception as e:
            lines.append(f"TS{axis}: error {e}")

    return "\n".join(lines)
