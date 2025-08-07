import json
import os
from constants import CONFIG_PATH

# Default configuration for all four axes
default_config = {
    "ip_address": "192.168.0.100",
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
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        save_config(default_config)

    try:
        with open(CONFIG_PATH, "r") as f:
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
    # Ensure the folder is there, then write
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)
