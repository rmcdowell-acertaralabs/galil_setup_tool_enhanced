"""
Helper module for easily switching between real gclib and emulator

Usage:
    # Option 1: Set environment variable
    set GALIL_USE_EMULATOR=true
    
    # Option 2: Call enable_emulator() before importing gclib
    from galil_emulator_helper import enable_emulator
    enable_emulator()
    import gclib  # Will use emulator
    
    # Option 3: Use in test setup
    from galil_emulator_helper import patch_gclib
    patch_gclib()  # Replaces gclib module with emulator
"""

import os
import sys
from typing import Optional


def enable_emulator(use_emulator: Optional[bool] = None):
    """
    Enable or disable emulator mode based on environment variable or argument.
    
    Args:
        use_emulator: If None, reads from GALIL_USE_EMULATOR env var.
                     If True/False, explicitly sets emulator mode.
    
    This should be called BEFORE importing gclib or galil_connection.
    """
    if use_emulator is None:
        use_emulator = os.getenv("GALIL_USE_EMULATOR", "false").lower() == "true"
    
    if use_emulator:
        patch_gclib()
        print("[Galil Emulator] Emulator mode enabled")


def patch_gclib():
    """
    Replace gclib module with emulator mock.
    
    This modifies sys.modules so that any 'import gclib' will get the emulator.
    """
    try:
        from dmc4143_emulator import FakeGclib
        sys.modules['gclib'] = FakeGclib
        print("[Galil Emulator] Patched gclib module with emulator")
    except ImportError as e:
        print(f"[Galil Emulator] Failed to import emulator: {e}")
        raise


def get_emulator_instance():
    """
    Get an instance of the emulator for direct use.
    
    Returns:
        FakeGclib instance (not a gclib.py() instance, but the class itself)
    """
    from dmc4143_emulator import FakeGclib
    return FakeGclib


def start_emulator_server(host="127.0.0.1", port=2323):
    """
    Start the TCP emulator server in a background thread.
    
    Args:
        host: Server host (default: 127.0.0.1)
        port: Server port (default: 2323)
    
    Returns:
        DMC4143TCPServer instance
    """
    from dmc4143_emulator import DMC4143TCPServer
    import threading
    
    server = DMC4143TCPServer(host=host, port=port)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    print(f"[Galil Emulator] Started TCP server on {host}:{port} in background")
    return server


def is_emulator_enabled() -> bool:
    """Check if emulator is currently enabled"""
    return 'gclib' in sys.modules and hasattr(sys.modules['gclib'], 'FakeGclib')


# Auto-patch gclib when connecting to emulator IP
def auto_patch_for_emulator():
    """
    Automatically patch gclib if connecting to emulator IP (127.0.0.1:2323).
    This can be called before imports or set GALIL_AUTO_PATCH=true.
    """
    # Monkey-patch gclib.GOpen to use emulator for localhost
    try:
        import gclib
        original_GOpen = gclib.py.GOpen
        
        def patched_GOpen(self, connection_string):
            addr = connection_string.split()[0] if connection_string else ""
            if addr in ("127.0.0.1", "localhost") or ":2323" in addr:
                # Use emulator
                from dmc4143_emulator import FakeGclib
                # Replace the instance with fake
                if not hasattr(self, '_patched_with_fake'):
                    self._patched_with_fake = True
                    fake_instance = FakeGclib.py()
                    # Copy state
                    self.emulator = fake_instance.emulator
                    self.socket_client = fake_instance.socket_client
                    self.use_tcp = fake_instance.use_tcp
            return original_GOpen(self, connection_string)
        
        gclib.py.GOpen = patched_GOpen
        print("[Galil Emulator] Auto-patched gclib for emulator detection")
    except Exception as e:
        print(f"[Galil Emulator] Auto-patch failed: {e}")

# Auto-enable if environment variable is set
if os.getenv("GALIL_USE_EMULATOR", "false").lower() == "true":
    enable_emulator(True)

# Auto-patch if environment variable is set
if os.getenv("GALIL_AUTO_PATCH", "false").lower() == "true":
    auto_patch_for_emulator()

