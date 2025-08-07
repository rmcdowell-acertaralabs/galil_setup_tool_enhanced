import logging
from constants import SERVO_BITS

logger = logging.getLogger(__name__)

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

        # Jog zero speed (no move)
        controller.send_command(f"JG{axis}=0")

        # Begin (applies servo-on / keeps it alive)
        controller.send_command(f"BG{axis}")

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
