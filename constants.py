import os

# Paths
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Window Dimensions
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 700

# Canvas for encoder overlay
CANVAS_WIDTH = 300
CANVAS_HEIGHT = 300
ENCODER_CENTER = (CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2)
ENCODER_RADIUS = 100  # Radius of encoder visual

# Defaults
DEFAULT_JOG_SPEED = 5000     # Default jog speed if nothing is configured
DEFAULT_AXIS = "A"           # Default axis selection
DEFAULT_CLICKS_PER_TURN = 64000  # Based on motor setup provided

# Status
STATUS_DISCONNECTED = "Disconnected"
