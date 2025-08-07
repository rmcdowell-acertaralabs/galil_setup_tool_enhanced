def jog_distance(controller, axis, distance_mm, turns_per_mm, clicks_per_turn, speed=50000):
    """
    Jog the motor by a distance (in mm), calculating the equivalent number of encoder counts.
    Positive or negative direction depends on the sign of distance_mm.
    """
    try:
        turns = distance_mm * turns_per_mm
        counts = int(turns * clicks_per_turn)

        controller.send_command(f"PA{axis}={counts}")
        controller.send_command(f"SP{axis}={speed}")
        controller.send_command(f"BG{axis}")
    except Exception as e:
        raise RuntimeError(f"Jog distance error on axis {axis}: {e}")

def move_to_position(controller, axis, position_counts, speed=50000):
    """
    Move the motor to an absolute encoder position (in counts).
    """
    try:
        controller.send_command(f"PA{axis}={position_counts}")
        controller.send_command(f"SP{axis}={speed}")
        controller.send_command(f"BG{axis}")
    except Exception as e:
        raise RuntimeError(f"Move to position error on axis {axis}: {e}")
