def tune_axis(controller, axis, kp, ki, kd):
    try:
        axis = axis.upper()
        kp = float(kp)
        ki = float(ki)
        kd = float(kd)

        print(f"[TUNE] Tuning Axis {axis}: KP={kp}, KI={ki}, KD={kd}")

        print("Stopping axis...")
        controller.send_command(f"ST {axis}")

        print("Setting KP...")
        controller.send_command(f"KP{axis}={kp}")

        print("Setting KI...")
        controller.send_command(f"KI{axis}={ki}")

        print("Setting KD...")
        controller.send_command(f"KD{axis}={kd}")

        print("Servo ON...")
        controller.send_command(f"SH {axis}")

        print("Jog to 0 speed (no motion)...")
        controller.send_command(f"JG{axis}=0")

        print("Begin motion...")
        controller.send_command(f"BG {axis}")

        # Removed AM {axis}, since motion isn't actually happening

    except Exception as e:
        raise RuntimeError(f"Error tuning axis {axis}: {e}")

def configure_axis(controller, axis, preset):
    try:
        axis = axis.upper()
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
    except Exception as e:
        raise RuntimeError(f"Error configuring axis {axis}: {e}")
