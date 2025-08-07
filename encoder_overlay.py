import math
import logging

logger = logging.getLogger(__name__)

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
        # Only try to read position if we’re actually connected
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
            # Other errors—log but don’t spam
            logger.debug(f"EncoderOverlay.update error: {e}")
