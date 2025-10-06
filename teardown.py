# teardown.py
# Requires an open gclib handle `g` (e.g., g = gclib.py(); g.GOpen("..."))
# Commands used: PA X=0, BGX, AMX, MOX
# Uses command_validator.py for command validation

from typing import Iterable, Tuple, Union
from command_validator import DMC4103CommandValidator

AxisList = Union[Iterable[str], str]

# Initialize command validator
_command_validator = DMC4103CommandValidator()

def _norm_axes(axes: AxisList) -> Tuple[str, ...]:
    if isinstance(axes, str):
        axes = list(axes)
    axes = tuple(a.upper() for a in axes if a.upper() in ("A","B","C","D","E","F","G","H"))
    if not axes:
        raise ValueError("No valid axes provided.")
    return axes

def _validate_teardown_commands(axes: Tuple[str, ...]) -> bool:
    """
    Validate all teardown commands before execution.
    Returns True if all commands are valid, False otherwise.
    """
    commands_to_validate = [
        "ST",  # Stop all motion
    ]
    
    # Add axis-specific commands for validation
    for axis in axes:
        commands_to_validate.extend([
            f"MG _MO{axis}",  # Check motor status
            f"PA{axis}=0",    # Position absolute
            f"BG{axis}",      # Begin motion
            f"AM{axis}",      # After motion
            f"MO{axis}",      # Motor off
        ])
    
    print(f"[TEARDOWN] Validating {len(commands_to_validate)} commands...")
    
    for cmd in commands_to_validate:
        validation = _command_validator.validate_command(cmd)
        if not validation.valid:
            print(f"[TEARDOWN ERROR] Invalid command '{cmd}': {validation.error_message}")
            return False
        if validation.warning_message:
            print(f"[TEARDOWN WARNING] {cmd}: {validation.warning_message}")
    
    print("[TEARDOWN] All commands validated successfully")
    return True

def _cmd(g, cmd: str) -> str:
    """
    Execute a command with validation.
    Returns the command output if successful, raises exception if validation fails.
    """
    # Validate command before execution
    validation = _command_validator.validate_command(cmd)
    if not validation.valid:
        raise ValueError(f"Invalid command '{cmd}': {validation.error_message}")
    
    if validation.warning_message:
        print(f"[TEARDOWN WARNING] {cmd}: {validation.warning_message}")
    
    out = g.GCommand(cmd)
    return out.strip() if isinstance(out, str) else ""

def get_teardown_command_help() -> str:
    """
    Get help information for teardown commands.
    Returns formatted help text for all commands used in teardown.
    """
    teardown_commands = ["ST", "MG", "PA", "BG", "AM", "MO"]
    help_text = "Teardown Commands Help:\n"
    help_text += "=" * 50 + "\n"
    
    for cmd in teardown_commands:
        validation = _command_validator.validate_command(cmd)
        help_text += f"{cmd}: {validation.description}\n"
    
    return help_text

def teardown_axes(
    g,
    axes: AxisList,
    power_off: bool = True,
) -> None:
    """
    Tear-down sequence per axis:
      1) Validate all commands before execution
      2) Check servo status first
      3) PA X=0   (command absolute zero) - only for servo-enabled axes
      4) BGX      (begin) - only for servo-enabled axes
      5) AMX      (wait for profile complete) - only for servo-enabled axes
      6) MOX      (optional: motor off) - for all axes

    Notes:
      - Assumes absolute 0 is a safe park point for each axis.
      - Skips motion commands for axes with servos not enabled.
      - All commands are validated using command_validator.py before execution.
    """
    ax_list = _norm_axes(axes)
    
    # Validate all commands before execution
    if not _validate_teardown_commands(ax_list):
        raise ValueError("Command validation failed. Cannot proceed with teardown.")
    
    servo_enabled_axes = []

    # Stop any existing motion first
    for a in ax_list:
        try:
            _cmd(g, f"ST{a}")  # Stop motion on this axis
            # DO NOT use AM - it's program-only trippoint
            # Poll _BG instead
            import time
            time.sleep(0.1)  # Brief pause for motion to stop
        except Exception as e:
            print(f"[TEARDOWN] {a}: Error stopping motion: {e}")
    
    # Check servo status for each axis
    for a in ax_list:
        try:
            mo_status = _cmd(g, f"MG _MO{a}")
            # Clean up response - remove carriage returns, newlines, and colons
            mo_status = mo_status.replace('\r', '').replace('\n', '').replace(':', '') if mo_status else "1"
            mo_value = float(mo_status.split(",")[0]) if mo_status else 1.0
            if mo_value == 0.0:
                servo_enabled_axes.append(a)
                print(f"[TEARDOWN] {a}: Servo enabled (MO=0), will perform motion teardown")
            else:
                print(f"[TEARDOWN] {a}: Servo not enabled (MO={mo_value}), skipping motion commands")
        except Exception as e:
            print(f"[TEARDOWN] {a}: Cannot check servo status: {e}, skipping motion commands")

    # 1) Set absolute targets to 0 for servo-enabled axes only
    for a in servo_enabled_axes:
        try:
            _cmd(g, f"PA{a}=0")
        except Exception as e:
            print(f"[TEARDOWN] {a}: PA command failed: {e}")

    # 2) Begin each servo-enabled axis motion
    for a in servo_enabled_axes:
        try:
            _cmd(g, f"BG{a}")
        except Exception as e:
            print(f"[TEARDOWN] {a}: BG command failed: {e}")

    # 3) Wait for each servo-enabled axis to complete its profile
    for a in servo_enabled_axes:
        try:
            _cmd(g, f"AM{a}")
        except Exception as e:
            print(f"[TEARDOWN] {a}: AM command failed: {e}")

    # 4) Turn motors off for all axes (this works even if servo not enabled)
    if power_off:
        for a in ax_list:
            try:
                _cmd(g, f"MO{a}")
            except Exception as e:
                print(f"[TEARDOWN] {a}: MO command failed: {e}")
