import gclib
import logging
import math
import time
import json
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
SERVO_BITS = {"A": 1, "B": 2, "C": 4, "D": 8}
VALID_AXES = ["A", "B", "C", "D"]

# ============================================================================
# GALIL CONTROLLER INTERFACE CLASS
# ============================================================================

class GalilController:
    def __init__(self):
        self.g = None

    def connect(self, address):
        self.g = gclib.py()
        self.g.GOpen(f"{address}")

    def send_command(self, command):
        if not self.g:
            raise ConnectionError("Controller not connected.")
        return self.g.GCommand(command)

    def disconnect(self):
        if self.g:
            self.g.GClose()
            self.g = None

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
        servo_status = controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Try to enable servo again
            controller.send_command(f"SH{axis}")
            time.sleep(0.2)
            servo_status = controller.send_command(f"MG _MO{axis}").strip()
            if servo_status == "0":
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
        servo_status = controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Try to enable servo again with more attempts
            for attempt in range(3):
                controller.send_command(f"SH{axis}")
                time.sleep(0.3)
                servo_status = controller.send_command(f"MG _MO{axis}").strip()
                if servo_status != "0":
                    break
            if servo_status == "0":
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
            current_pos = int(controller.send_command(f"TP {axis}").strip())
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
        servo_status = controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Re-enable servo if it got disabled
            controller.send_command(f"SH{axis}")
            
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
        response = controller.send_command(f"TP {axis}")
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
            pos_str = self.controller.send_command(f"TP {self.axis}")
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
