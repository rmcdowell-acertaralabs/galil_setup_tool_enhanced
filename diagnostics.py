def try_command(controller, label, command, fallback=None):
    """
    Attempts to send a command to the controller. Falls back if needed.
    Returns None if the command is unsupported.
    """
    try:
        response = controller.send_command(command).strip()
        if response in ["?", "ERROR", "error", "Unsupported", ""]:
            if fallback:
                return try_command(controller, label, fallback)
            return None
        return f"{label}: {response}"
    except Exception:
        return None

def get_controller_info(controller):
    commands = [
        ("Firmware", "MG _FW", "MG _ID"),
        ("Serial", "MG _BN", None),
        ("Positions", "TP", None),
        ("Torque Command", "MG _TC", None),
        ("Error Code", "MG _TE", None),
        ("Limit Switch Status", "MG _LF", None),
        ("Motion Status", "MG _BG", None)
    ]

    diagnostics = []
    for label, command, fallback in commands:
        result = try_command(controller, label, command, fallback)
        if result:
            diagnostics.append(result)

    return "\n".join(diagnostics)

def get_diagnostics(controller):
    return get_controller_info(controller)
