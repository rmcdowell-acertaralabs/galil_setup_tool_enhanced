import gclib
import logging
import math
import time
import json
import os
import re
from typing import Dict, List, Optional, Tuple
from command_validator_proper import DMC4103CommandValidator, CommandValidation

logger = logging.getLogger(__name__)

# Constants
SERVO_BITS = {"A": 1, "B": 2, "C": 4, "D": 8}
VALID_AXES = ["A", "B", "C", "D"]

def mg_float(controller, expr: str, default: float = float("nan")) -> float:
    """Helper function for consistent MG parsing with float conversion"""
    s = controller.send_command(f"MG {expr}") or ""
    try:
        return float(s.strip().split(",")[0])
    except Exception:
        return default

# ============================================================================
# GALIL CONTROLLER INTERFACE CLASS
# ============================================================================

class GalilController:
    def __init__(self):
        self.g = None
        self.connection_addr = None
        self.last_open_str = None
        self.last_ip = None
        self.command_validator = DMC4103CommandValidator()

    def connect(self, address):
        try:
            # Creating gclib instance
            self.g = gclib.py()
            # Store connection address
            self.connection_addr = address
            # Attempting connection
            
            # For COM ports, add some troubleshooting info
            if address.upper().startswith('COM'):
                # COM port connection attempt
                
                # Add a small delay to prevent rapid connection attempts
                time.sleep(0.2)
            
            # Build open string and attempt with baud when using serial
            open_attempts = []
            if address.upper().startswith('COM'):
                # Try preferred baud first, then common fallbacks
                preferred_baud = 115200
                baud_candidates = [preferred_baud, 57600, 38400, 19200, 9600]
                # Try different open string formats for COM ports
                open_attempts = []
                for baud in baud_candidates:
                    open_attempts.extend([
                        f"{address} --direct --baud {baud}",
                        f"{address} --baud {baud}",
                        f"{address} --direct",
                        f"{address}",
                        # Additional formats that work with some Galil controllers
                        f"{address} --baud {baud} --direct",
                        f"{address} --timeout 5000 --baud {baud}",
                        f"{address} --timeout 10000 --baud {baud}",
                        f"{address} --timeout 5000 --direct --baud {baud}",
                        f"{address} --timeout 10000 --direct --baud {baud}"
                    ])
            else:
                open_attempts = [f"{address} --direct", f"{address}"]

            last_error = None
            for i, open_str in enumerate(open_attempts):
                try:
                    # Trying connection
                    self.g.GOpen(open_str)
                    # Connection successful - capture IP immediately
                    self.last_ip = self._extract_ip(address)
                    try:
                        info = self.g.GInfo() or ""
                        self.last_ip = self._extract_ip(info) or self.last_ip
                    except Exception:
                        pass
                    # Optional debug:
                    print(f"[GalilController] Connected. Resolved IP: {self.last_ip or 'N/A'}")
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    # GOpen attempt failed
                    
                    # If port is already open, rethrow immediately
                    if "already open" in error_msg or "access denied" in error_msg:
                        raise
                    
                    # For timeouts, try a longer wait before next attempt
                    if "timeout" in error_msg:
                        # Timeout detected, waiting longer
                        time.sleep(1.0)  # Longer wait for timeouts
                    else:
                        time.sleep(0.2)  # Short wait for other errors
                    
                    # If this is the last attempt, provide more detailed error info
                    if i == len(open_attempts) - 1:
                        # All connection attempts failed
                        if "timeout" in error_msg:
                            # Timeout errors suggest connection issues
                            pass
            else:
                # If we exhausted attempts without break, raise last error
                raise last_error if last_error else RuntimeError("Unable to open controller")
            # Connection established, waiting for stabilization
            
            # Give the connection time to establish properly
            time.sleep(0.5)
            
            # Testing connection
            # Test the connection with a simple command that works on DMC-4103
            test_response = self.g.GCommand("TPA")
            # Connection test successful
            
            # Store connection info for IP tracking
            self.last_open_str = open_str
        except Exception as e:
            # Connection failed
            
            # Provide specific troubleshooting advice based on error type
            if "device failed to open" in str(e).lower():
                if address.upper().startswith('COM'):
                    # COM port connection failed
                    pass
                else:
                    # Network connection failed
                    pass
            
            if self.g:
                try:
                    # Attempting to close connection
                    self.g.GClose()
                except Exception as close_error:
                    # Error closing connection
                    pass
                self.g = None
            raise

    def send_command(self, command):
        if not self.g:
            raise ConnectionError("Controller not connected.")
        
        # Safety check: ensure command is a string and doesn't contain widget references
        if not isinstance(command, str):
            raise ValueError(f"Command must be a string, got {type(command)}: {command}")
        
        # Check for widget references (Tkinter widget paths start with ".")
        if command.startswith(".") and ("frame" in command or "canvas" in command or "label" in command):
            raise ValueError(f"Invalid command contains widget reference: {command}")
        
        # Validate command using DMC-4103 command validator
        validation = self.command_validator.validate_command(command)
        if not validation.valid:
            error_msg = f"Invalid command '{command}': {validation.error_message}"
            if validation.warning_message:
                error_msg += f" (Warning: {validation.warning_message})"
            raise ValueError(error_msg)
        
        # Log warning if present but command is valid
        if validation.warning_message:
            logger.warning(f"Command '{command}' warning: {validation.warning_message}")
        
        try:
            # Send command and return response
            response = self.g.GCommand(command)
            # Check for "?" response silently for expected cases
            if response and response.strip() == "?":
                # For MG _* internal commands, suppress errors (expected on unsupported controllers)
                if command.startswith("MG _"):
                    return "?"
                raise ValueError(f"Command '{command}' returned '?' - unsupported")
            return response
        except Exception as e:
            error_str = str(e).lower()
            # Suppress logging for expected/known unsupported commands
            if ("question mark" in error_str or "?" in error_str) and command.startswith("MG _"):
                # MG _* commands often not supported - suppress
                return "?"
            # Suppress TP errors for unconfigured axes
            if command.startswith("TP") and ("question mark" in error_str or "?" in error_str):
                return "0"  # Return default position
            # Only log unexpected errors
            if "question mark" not in error_str and "?" not in error_str:
                print(f"Command '{command}' failed: {e}")
            # Check if this is a connection error
            if "not connected" in str(e).lower() or "connection" in str(e).lower():
                # Connection lost
                self.g = None
            raise

    def send_command_unvalidated(self, command):
        """
        Send a command to the controller without validation.
        Use this for basic information commands that may not be in the command reference.
        """
        if not self.g:
            raise ConnectionError("Controller not connected.")
        
        # Safety check: ensure command is a string and doesn't contain widget references
        if not isinstance(command, str):
            raise ValueError(f"Command must be a string, got {type(command)}: {command}")
        
        # Check for widget references (Tkinter widget paths start with ".")
        if command.startswith(".") and ("frame" in command or "canvas" in command or "label" in command):
            raise ValueError(f"Invalid command contains widget reference: {command}")
        
        try:
            # Send command and return response without validation
            response = self.g.GCommand(command)
            # Check if controller returned "?" indicating unsupported command
            if response and response.strip() == "?":
                # For MG _* internal commands, suppress errors (expected on unsupported controllers)
                if command.startswith("MG _"):
                    return "?"
                raise ValueError(f"Command '{command}' not supported by controller")
            return response
        except Exception as e:
            error_str = str(e).lower()
            # Suppress logging for expected/known unsupported commands
            if ("question mark" in error_str or "?" in error_str):
                # MG _* commands often not supported - suppress
                if command.startswith("MG _"):
                    return "?"
                # TP errors for unconfigured axes - return default
                if command.startswith("TP"):
                    return "0"
            # Only log unexpected errors (not question mark errors)
            if "question mark" not in error_str and "?" not in error_str:
                print(f"Command '{command}' failed: {e}")
            # Check if this is a connection error
            if "not connected" in str(e).lower() or "connection" in str(e).lower():
                # Connection lost
                self.g = None
                raise
            # For suppressed errors, return None to indicate failure
            if "question mark" in error_str or "?" in error_str:
                return None
            raise

    def validate_command(self, command: str) -> CommandValidation:
        """
        Validate a command without sending it to the controller.
        Returns CommandValidation object with validation results.
        """
        return self.command_validator.validate_command(command)
    
    def disconnect(self):
        if self.g:
            self.g.GClose()
            self.g = None

    @staticmethod
    def _extract_ip(s: str) -> Optional[str]:
        m = re.search(r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)', s or "")
        if not m:
            return None
        ip = m.group(0)
        try:
            return ip if all(0 <= int(p) <= 255 for p in ip.split(".")) else None
        except Exception:
            return None

    def get_current_ip(self) -> Optional[str]:
        """Best-effort: return the controller IP if we connected over Ethernet, or query it via serial."""
        if not self.g:
            return None
        # 1) what we connected to
        if self.last_ip:
            return self.last_ip
        # 2) ask gclib for connection info
        try:
            info = self.g.GInfo() or ""
            ip = self._extract_ip(info)
            if ip:
                self.last_ip = ip
                return ip
        except Exception:
            pass
        # 3) If connected via COM port, query the controller's IP address directly
        try:
            # Try to read the controller's configured IP address using the IA ? command
            # This works even when connected via COM port
            # IA ? returns IP in comma-separated format (e.g., "192,168,1,100")
            ip_response = self.send_command("IA ?")
            if ip_response and not ip_response.startswith('?'):
                # Convert comma-separated format to dot-separated (192,168,1,100 -> 192.168.1.100)
                ip_response = ip_response.strip().replace(',', '.')
                ip = self._extract_ip(ip_response)
                if ip:
                    self.last_ip = ip
                    return ip
        except Exception:
            pass
        # 4) Alternative: Try TH command which also shows IP
        try:
            th_response = self.send_command("TH")
            if th_response and not th_response.startswith('?'):
                # TH returns: "CONTROLLER IP ADDRESS 10,51,0,87 ETHERNET ADDRESS 00-50-4C-08-01-1F"
                # Extract IP from the response
                ip_match = re.search(r'IP ADDRESS\s+([\d,]+)', th_response)
                if ip_match:
                    ip_str = ip_match.group(1).replace(',', '.')
                    ip = self._extract_ip(ip_str)
                    if ip:
                        self.last_ip = ip
                        return ip
        except Exception:
            pass
        return None

# ============================================================================
# MOTOR SETUP FUNCTIONS
# ============================================================================

def tune_axis(controller, axis, kp, ki, kd):
    """
    Tune PID on the given axis, then issue a zero‐speed jog and a BG to apply.
    """
    axis = axis.upper()
    
    # Validate axis
    if axis not in SERVO_BITS:
        raise ValueError(f"Invalid axis '{axis}'. Must be one of {list(SERVO_BITS.keys())}")
    
    try:
        kp = float(kp)
        ki = float(ki)
        kd = float(kd)
    except ValueError as e:
        raise RuntimeError(f"Invalid PID values for axis {axis}: {e}")

    logger.info(f"[TUNE] Axis {axis}: KP={kp}, KI={ki}, KD={kd}")

    try:
        # Stop axis
        controller.send_command(f"ST{axis}")

        # Set PID
        controller.send_command(f"KP{axis}={kp}")
        controller.send_command(f"KI{axis}={ki}")
        controller.send_command(f"KD{axis}={kd}")

        # Servo on - use axis letter (no space)
        controller.send_command(f"SH{axis}")

        # Wait a moment for servo to stabilize
        time.sleep(0.1)

        # Stop any existing motion
        controller.send_command(f"ST{axis}")

        logger.info(f"[TUNE] Axis {axis} tune sequence complete")
    except Exception as e:
        raise RuntimeError(f"Error tuning axis {axis}: {e}")

def configure_axis(controller, axis, preset):
    """
    Apply a stored preset dictionary to the axis (KP/KI/KD/SP/AC/DC/TL).
    """
    axis = axis.upper()
    
    # Validate axis
    if axis not in SERVO_BITS:
        raise ValueError(f"Invalid axis '{axis}'. Must be one of {list(SERVO_BITS.keys())}")
    try:
        if "kp" in preset:
            controller.send_command(f"KP{axis}={float(preset['kp'])}")
        if "ki" in preset:
            controller.send_command(f"KI{axis}={float(preset['ki'])}")
        if "kd" in preset:
            controller.send_command(f"KD{axis}={float(preset['kd'])}")
        if "sp" in preset:
            controller.send_command(f"SP{axis}={int(float(preset['sp']))}")
        if "ac" in preset:
            controller.send_command(f"AC{axis}={int(float(preset['ac']))}")
        if "dc" in preset:
            controller.send_command(f"DC{axis}={int(float(preset['dc']))}")
        if "tl" in preset:
            controller.send_command(f"TL{axis}={float(preset['tl'])}")

        logger.info(f"[CONFIG] Axis {axis} configured with preset {preset}")
    except Exception as e:
        raise RuntimeError(f"Error configuring axis {axis}: {e}")

# ============================================================================
# MOTION CONTROL FUNCTIONS
# ============================================================================

def jog_distance(controller, axis, distance_mm, turns_per_mm, clicks_per_turn, speed=5000, accel=None, decel=None):
    """
    Jog the motor by a distance (in mm), calculating the equivalent number of encoder counts.
    Positive or negative direction depends on the sign of distance_mm.
    """
    try:
        # Stop any existing motion
        controller.send_command(f"ST{axis}")
        time.sleep(0.1)  # Wait for stop to take effect
        
        # Ensure servo is on
        controller.send_command(f"SH{axis}")
        time.sleep(0.1)  # Wait for servo to stabilize
        
        # Check servo status
        try:
            servo_status = float(controller.send_command(f"MG _MO{axis}").strip().split(',')[0])
        except Exception:
            servo_status = 1.0
        if servo_status == 0.0:
            # Try to enable servo again
            controller.send_command(f"SH{axis}")
            time.sleep(0.2)
            try:
                servo_status = float(controller.send_command(f"MG _MO{axis}").strip().split(',')[0])
            except Exception:
                servo_status = 1.0
            if servo_status == 0.0:
                raise RuntimeError(f"Could not enable servo for axis {axis}")
        
        # Use provided acceleration/deceleration or calculate based on speed
        if accel is None:
            accel = speed * 2  # 2x speed for acceleration
        if decel is None:
            decel = speed * 4  # 4x speed for deceleration
        
        # Apply speed/accel/decel parameters with more conservative fallbacks
        sp_response = controller.send_command(f"SP{axis}={speed}")
        if sp_response.strip() == "?":
            # Try more conservative values
            for fallback_speed in [1000, 500, 100]:
                sp_response = controller.send_command(f"SP{axis}={fallback_speed}")
                if sp_response.strip() != "?":
                    break
            if sp_response.strip() == "?":
                raise RuntimeError(f"Could not set speed for axis {axis}")
        
        ac_response = controller.send_command(f"AC{axis}={accel}")
        if ac_response.strip() == "?":
            # Try more conservative acceleration values
            for fallback_accel in [1000, 500, 100]:
                ac_response = controller.send_command(f"AC{axis}={fallback_accel}")
                if ac_response.strip() != "?":
                    break
            if ac_response.strip() == "?":
                raise RuntimeError(f"Could not set acceleration for axis {axis}")
        
        dc_response = controller.send_command(f"DC{axis}={decel}")
        if dc_response.strip() == "?":
            # Try more conservative deceleration values
            for fallback_decel in [2000, 1000, 200]:
                dc_response = controller.send_command(f"DC{axis}={fallback_decel}")
                if dc_response.strip() != "?":
                    break
            if dc_response.strip() == "?":
                raise RuntimeError(f"Could not set deceleration for axis {axis}")

        # Calculate relative distance in counts using provided kinematics
        turns = distance_mm * turns_per_mm
        counts = int(round(turns * clicks_per_turn))

        # Use PR for relative distance move (not JG)
        response = controller.send_command(f"PR{axis}={counts}")
        if response.strip() == "?":
            raise RuntimeError(f"Invalid relative move for axis {axis}")
        response = controller.send_command(f"BG{axis}")
        if response.strip() == "?":
            raise RuntimeError(f"Invalid begin command for axis {axis}")
        
    except Exception as e:
        raise RuntimeError(f"Jog distance error on axis {axis}: {e}")

def move_to_position(controller, axis, position_counts, speed=5000, accel=None, decel=None):
    """
    Move the motor to an absolute encoder position (in counts).
    """
    try:
        # Stop any existing motion
        controller.send_command(f"ST{axis}")
        time.sleep(0.1)  # Wait for stop to take effect
        
        # Ensure servo is on and stays on
        controller.send_command(f"SH{axis}")
        time.sleep(0.2)  # Wait longer for servo to stabilize
        
        # Verify servo is enabled
        try:
            servo_status = float(controller.send_command(f"MG _MO{axis}").strip().split(',')[0])
        except Exception:
            servo_status = 1.0
        if servo_status == 0.0:
            # Try to enable servo again with more attempts
            for attempt in range(3):
                controller.send_command(f"SH{axis}")
                time.sleep(0.3)
                try:
                    servo_status = float(controller.send_command(f"MG _MO{axis}").strip().split(',')[0])
                except Exception:
                    servo_status = 1.0
                if servo_status != 0.0:
                    break
            if servo_status == 0.0:
                raise RuntimeError(f"Could not enable servo for axis {axis}")
        
        # Use provided acceleration/deceleration or calculate based on speed
        if accel is None:
            accel = speed * 2  # 2x speed for acceleration
        if decel is None:
            decel = speed * 4  # 4x speed for deceleration
        
        # Apply speed/accel/decel parameters with more conservative fallbacks
        sp_response = controller.send_command(f"SP{axis}={speed}")
        if sp_response.strip() == "?":
            # Try more conservative values
            for fallback_speed in [1000, 500, 100]:
                sp_response = controller.send_command(f"SP{axis}={fallback_speed}")
                if sp_response.strip() != "?":
                    break
            if sp_response.strip() == "?":
                raise RuntimeError(f"Could not set speed for axis {axis}")
        
        ac_response = controller.send_command(f"AC{axis}={accel}")
        if ac_response.strip() == "?":
            # Try more conservative acceleration values
            for fallback_accel in [1000, 500, 100]:
                ac_response = controller.send_command(f"AC{axis}={fallback_accel}")
                if ac_response.strip() != "?":
                    break
            if ac_response.strip() == "?":
                raise RuntimeError(f"Could not set acceleration for axis {axis}")
        
        dc_response = controller.send_command(f"DC{axis}={decel}")
        if dc_response.strip() == "?":
            # Try more conservative deceleration values
            for fallback_decel in [2000, 1000, 200]:
                dc_response = controller.send_command(f"DC{axis}={fallback_decel}")
                if dc_response.strip() != "?":
                    break
            if dc_response.strip() == "?":
                raise RuntimeError(f"Could not set deceleration for axis {axis}")
        
        # Get current position first
        try:
            current_pos = int(controller.send_command(f"TP{axis}").strip())
        except:
            current_pos = 0
        
        # Use absolute positioning (PA) for precise position control
        pa_response = controller.send_command(f"PA{axis}={position_counts}")
        if pa_response.strip() == "?":
            raise RuntimeError(f"Invalid position command for axis {axis}")
        
        bg_response = controller.send_command(f"BG{axis}")
        if bg_response.strip() == "?":
            raise RuntimeError(f"Invalid begin command for axis {axis}")
        
        # Wait for motion to complete and ensure servo stays on
        time.sleep(0.1)
        try:
            servo_status = float(controller.send_command(f"MG _MO{axis}").strip().split(',')[0])
            if servo_status != 0.0:
                controller.send_command(f"SH{axis}")
        except Exception:
            pass
            
    except Exception as e:
        raise RuntimeError(f"Move to position error on axis {axis}: {e}")

# ============================================================================
# DIAGNOSTICS FUNCTIONS
# ============================================================================

def is_axis_available(controller, axis):
    """
    Check if an axis is available and responding to commands.
    """
    try:
        # Try to read position - this should work if axis is configured
        response = controller.send_command(f"TP{axis}")
        if response.strip() == "?":
            return False
        return True
    except Exception:
        return False

def try_command(controller, label, command, fallback=None):
    """
    Attempts to run a command; returns "Label: value" or None on unsupported/error responses.
    """
    try:
        # Special case for GInfo() - use gclib method directly
        if command == "GInfo":
            if hasattr(controller, 'g') and controller.g:
                s = controller.g.GInfo() or ""
                ip = controller._extract_ip(s)
                return f"{label}: {ip}" if ip else f"{label}: {s.strip()}"
            else:
                # Fallback to ID command if gclib connection not available
                resp = controller.send_command("ID").strip()
        else:
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
        ("Firmware",            "ID",      "ID"),
        ("Serial",              "MG _BN",  None),
        ("All Positions",       "TP",      None),
        ("Torque Command",      "MG _TC",  None),
        ("Error Code",          "TE",      None),
        ("Limit Switch Status", "MG _LF",  None),
        ("Motion Status",       "MG _BG",  None),
        ("IP Address",          "GInfo",  None),
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
            pos = controller.send_command(f"TP{axis}").strip()
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

# ============================================================================
# MOTOR SETTINGS FROM EXTERNAL CONFIG
# ============================================================================

_AXIS_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}

def _parse_float_list(value_str: str) -> List[float]:
    """Parse a bracketed list of numbers (supports scientific notation, floats)."""
    # Remove brackets if present and split by comma
    cleaned = value_str.strip().strip("[]")
    if not cleaned:
        return []
    parts = [p.strip() for p in cleaned.split(",")]
    out: List[float] = []
    for p in parts:
        try:
            out.append(float(p))
        except Exception:
            # Ignore unparsable entries silently
            continue
    return out

def load_motor_settings_from_config(config_path: str = r"C:\\AMS\\config.txt") -> Dict[str, List[float]]:
    """Load motor settings arrays from the given config file.

    Only the following keys are parsed:
    - motor_speed
    - motor_accel
    - motor_decel
    - jog_speed
    - motor_clicksPerTurn
    - motor_turnsPerMM
    """
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        raise RuntimeError(f"Unable to read config file at {config_path}: {e}")

    patterns = {
        "motor_speed": r"^motor_speed\s*=\s*\[(.*?)\]",
        "motor_accel": r"^motor_accel\s*=\s*\[(.*?)\]",
        "motor_decel": r"^motor_decel\s*=\s*\[(.*?)\]",
        "jog_speed": r"^jog_speed\s*=\s*\[(.*?)\]",
        "motor_clicksPerTurn": r"^motor_clicksPerTurn\s*=\s*\[(.*?)\]",
        "motor_turnsPerMM": r"^motor_turnsPerMM\s*=\s*\[(.*?)\]",
    }

    flags = re.MULTILINE
    parsed: Dict[str, List[float]] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags)
        if match:
            parsed[key] = _parse_float_list(match.group(1))
        else:
            parsed[key] = []

    return parsed

def apply_axis_settings_from_config(
    controller,
    axis: str,
    config_path: str = r"C:\\AMS\\config.txt",
) -> None:
    """Apply SP/AC/DC for a single axis from c:\AMS\config.txt motor arrays.

    This ignores any GUI-entered values and uses only the external file.
    """
    settings = load_motor_settings_from_config(config_path)
    axis_index = _AXIS_TO_INDEX.get(axis.upper())
    if axis_index is None:
        raise ValueError(f"Invalid axis {axis}")

    try:
        controller.send_command(f"ST{axis}")
        controller.send_command(f"SH{axis}")

        # Fetch values with safe fallbacks
        speed_val = int(settings.get("motor_speed", [0] * 4)[axis_index]) if settings.get("motor_speed") else None
        accel_val = int(settings.get("motor_accel", [0] * 4)[axis_index]) if settings.get("motor_accel") else None
        decel_val = int(settings.get("motor_decel", [0] * 4)[axis_index]) if settings.get("motor_decel") else None

        if speed_val is not None:
            resp = controller.send_command(f"SP{axis}={speed_val}")
            if resp.strip() == "?":
                raise RuntimeError(f"Controller rejected SP for axis {axis} with value {speed_val}")

        if accel_val is not None:
            resp = controller.send_command(f"AC{axis}={accel_val}")
            if resp.strip() == "?":
                raise RuntimeError(f"Controller rejected AC for axis {axis} with value {accel_val}")

        if decel_val is not None:
            resp = controller.send_command(f"DC{axis}={decel_val}")
            if resp.strip() == "?":
                raise RuntimeError(f"Controller rejected DC for axis {axis} with value {decel_val}")
    except Exception as e:
        raise RuntimeError(f"Failed applying settings from config for axis {axis}: {e}")

def diagnose_firmware_issue(com_port: str) -> Dict[str, any]:
    """
    Diagnose potential firmware issues with a Galil controller.
    
    Args:
        com_port: COM port to test (e.g., "COM4")
        
    Returns:
        Dictionary with diagnostic results and recommendations
    """
    results = {
        'port': com_port,
        'basic_connectivity': False,
        'firmware_responsive': False,
        'recovery_possible': False,
        'recommendations': [],
        'error_details': []
    }
    
    try:
        print(f"=== FIRMWARE DIAGNOSTIC FOR {com_port} ===")
        
        # Test 1: Basic port connectivity
        print(f"Testing basic port connectivity...")
        try:
            g = gclib.py()
            # Use a longer timeout for diagnostic to prevent overwhelming the controller
            g.GOpen(f"{com_port} --direct --timeout 10000")
            results['basic_connectivity'] = True
            print(f"✓ Port can be opened")
            
            # Add a delay to let the connection stabilize
            time.sleep(1.0)
            
        except Exception as e:
            error_msg = str(e).lower()
            results['error_details'].append(f"Port open failed: {e}")
            print(f"✗ Port cannot be opened: {e}")
            
            # If we get timeouts, the port can be opened but controller isn't responding
            if "timeout" in error_msg:
                results['basic_connectivity'] = True  # Port can be opened
                print(f"✓ Port can be opened (timeout indicates controller not responding)")
            else:
                return results  # Real port failure
        
        # Test 2: Try to get any response from controller
        print(f"Testing controller responsiveness...")
        test_commands = [
            "TPA",       # Tell Position
            "ID",        # Firmware version and Controller ID
            "ID",        # Controller ID
            "MG _BN",    # Serial number
        ]
        
        responsive_commands = []
        for cmd in test_commands:
            try:
                # Add delay between commands to prevent overwhelming the controller
                time.sleep(0.5)  # 500ms delay between commands
                
                response = g.GCommand(cmd)
                if response and response.strip() != "?":
                    responsive_commands.append(f"{cmd}: {response.strip()}")
                    print(f"✓ Command '{cmd}' responded: {response.strip()}")
                else:
                    print(f"✗ Command '{cmd}' returned: {response}")
            except Exception as e:
                print(f"✗ Command '{cmd}' failed: {e}")
                results['error_details'].append(f"Command '{cmd}' failed: {e}")
                # If we get a write error, stop testing to prevent further damage
                if "write error" in str(e).lower():
                    print(f"⚠️  Write error detected - stopping diagnostic to prevent controller damage")
                    break
        
        if responsive_commands:
            results['firmware_responsive'] = True
            print(f"✓ Controller is responsive to {len(responsive_commands)} commands")
        else:
            print(f"✗ Controller is not responsive to any commands")
        
        # Test 3: Check for recovery mode indicators (only if controller is responsive)
        if results['firmware_responsive']:
            print(f"Testing for recovery mode...")
            recovery_commands = [
                "BOOT",      # Boot command
                "RESET",     # Reset command
                "RECOVERY",  # Recovery command
                "UPDATE",    # Update command
            ]
            
            for cmd in recovery_commands:
                try:
                    time.sleep(0.5)  # Delay between recovery commands
                    response = g.GCommand(cmd)
                    if response and not response.startswith('?'):
                        print(f"✓ Recovery command '{cmd}' available: {response}")
                        results['recovery_possible'] = True
                        break
                except Exception as e:
                    print(f"✗ Recovery command '{cmd}' failed: {e}")
                    # Stop if we get write errors
                    if "write error" in str(e).lower():
                        break
        
        g.GClose()
        
        # Generate recommendations
        if not results['basic_connectivity']:
            results['recommendations'].append("Port cannot be opened - check hardware connection")
        elif not results['firmware_responsive']:
            results['recommendations'].append("FIRMWARE CORRUPTION DETECTED")
            results['recommendations'].append("1. Try Galil firmware recovery tools")
            results['recommendations'].append("2. Contact Galil support for firmware update")
            results['recommendations'].append("3. Check if controller has recovery mode")
            results['recommendations'].append("4. Verify controller model and firmware version")
        else:
            results['recommendations'].append("Controller appears to be working normally")
        
        print(f"=== DIAGNOSTIC COMPLETE ===")
        
    except Exception as e:
        results['error_details'].append(f"Diagnostic failed: {e}")
        print(f"Diagnostic error: {e}")
    
    return results

def get_axis_kinematics_from_config(
    axis: str, config_path: str = r"C:\\AMS\\config.txt"
) -> Dict[str, float]:
    """Return clicks_per_turn, turns_per_mm, jog_speed for an axis from config file."""
    settings = load_motor_settings_from_config(config_path)
    axis_index = _AXIS_TO_INDEX.get(axis.upper())
    if axis_index is None:
        raise ValueError(f"Invalid axis {axis}")

    def _get(name: str, default: float) -> float:
        arr = settings.get(name)
        if arr and len(arr) > axis_index:
            try:
                return float(arr[axis_index])
            except Exception:
                return default
        return default

    return {
        "clicks_per_turn": _get("motor_clicksPerTurn", 64000.0),
        "turns_per_mm": _get("motor_turnsPerMM", 0.2),
        "jog_speed": int(_get("jog_speed", 128000.0)),
        "motor_speed": int(_get("motor_speed", 1024000.0)),
        "motor_accel": int(_get("motor_accel", 2560000.0)),
        "motor_decel": int(_get("motor_decel", 2560000.0)),
    }

# ============================================================================
# ENCODER OVERLAY CLASS
# ============================================================================

class EncoderOverlay:
    def __init__(self, canvas, controller, center=(150, 150), radius=100, axis="A", clicks_per_turn=64000):
        self.canvas = canvas
        self.controller = controller
        self.center = center
        self.radius = radius
        self.axis = axis
        self.clicks_per_turn = clicks_per_turn
        self.dot = None

    def update(self):
        # Only try to read position if we're actually connected
        try:
            # TP <axis> needs a space
            pos_str = self.controller.send_command(f"TP{self.axis}")
            pos = int(pos_str.strip())
            angle = (pos % self.clicks_per_turn) / self.clicks_per_turn * 2 * math.pi

            x = self.center[0] + self.radius * math.cos(angle)
            y = self.center[1] + self.radius * math.sin(angle)

            if self.dot:
                self.canvas.delete(self.dot)

            self.dot = self.canvas.create_oval(
                x - 5, y - 5, x + 5, y + 5,
                fill="red", outline=""
            )
        except (ConnectionError, ValueError, AttributeError):
            # Controller not connected yet, or bad parse—just skip drawing
            return
        except Exception as e:
            # Other errors—log but don't spam
            logger.debug(f"EncoderOverlay.update error: {e}")

# ============================================================================
# CONFIGURATION FUNCTIONS
# ============================================================================

# Default configuration for all four axes
default_config = {
    "ip_address": "10.1.0.21",
    "jog_speed": 128000,
    "axis_presets": {
        axis: {
            "jog_speed": 128000,
            "kp": 10.0,
            "ki": 0.1,
            "kd": 50.0,
            "sp": 1024000,
            "ac": 2560000,
            "dc": 2560000,
            "tl": 8.2,
            "clicks_per_turn": 64000,
            "turns_per_mm": 0.2
        }
        for axis in ("A", "B", "C", "D")
    }
}

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        save_config(default_config)

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            # Ensure all axes are present
            if "axis_presets" not in config:
                config["axis_presets"] = {}
            for axis in ("A", "B", "C", "D"):
                if axis not in config["axis_presets"]:
                    config["axis_presets"][axis] = default_config["axis_presets"][axis]
            return config
    except (json.JSONDecodeError, IOError):
        # If the file is unreadable or malformed, overwrite with defaults
        save_config(default_config)
        return default_config.copy()

def save_config(config_data):
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    # Ensure the folder is there, then write
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4)
