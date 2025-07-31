import json
import os

CONFIG_FILE = "assets/config.json"

default_config = {
    "ip_address": "192.168.0.100",
    "jog_speed": 128000,
    "axis_presets": {
        "A": {
            "jog_speed": 128000,
            "kp": 10,
            "ki": 0.1,
            "kd": 50,
            "sp": 1024000,
            "ac": 2560000,
            "dc": 2560000,
            "tl": 8.2,
            "clicks_per_turn": 64000,
            "turns_per_mm": 0.2
        },
        "B": {
            "jog_speed": 128000,
            "kp": 10,
            "ki": 0.1,
            "kd": 50,
            "sp": 1024000,
            "ac": 2560000,
            "dc": 2560000,
            "tl": 8.2,
            "clicks_per_turn": 64000,
            "turns_per_mm": 0.2
        },
        "C": {
            "jog_speed": 128000,
            "kp": 10,
            "ki": 0.1,
            "kd": 50,
            "sp": 1024000,
            "ac": 2560000,
            "dc": 2560000,
            "tl": 8.2,
            "clicks_per_turn": 64000,
            "turns_per_mm": 0.2
        }
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)
