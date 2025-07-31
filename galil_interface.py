import gclib

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
