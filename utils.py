from serial.tools import list_ports
import shutil
import os
import math
from tkinter import messagebox
from typing import List, Dict, Any

def install_gclib_dll():
    """Install gclib.dll to System32 directory."""
    dll_name = "gclib.dll"
    destination = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", dll_name)
    source = os.path.join(os.getcwd(), dll_name)

    if not os.path.exists(source):
        messagebox.showerror("Install Failed", f"{dll_name} not found in application folder.")
        return False

    try:
        shutil.copy2(source, destination)
        messagebox.showinfo("Success", f"{dll_name} copied to System32.")
        return True
    except PermissionError:
        messagebox.showerror("Permission Denied", "Run this application as Administrator to install the DLL.")
        return False
    except Exception as e:
        messagebox.showerror("Install Failed", str(e))
        return False

def install_gclibo_dll():
    """Install gclibo.dll to System32 directory."""
    dll_name = "gclibo.dll"
    destination = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", dll_name)
    source = os.path.join(os.getcwd(), dll_name)

    if not os.path.exists(source):
        messagebox.showerror("Install Failed", f"{dll_name} not found in application folder.")
        return False

    try:
        shutil.copy2(source, destination)
        messagebox.showinfo("Success", f"{dll_name} copied to System32.")
        return True
    except PermissionError:
        messagebox.showerror("Permission Denied", "Run this application as Administrator to install the DLL.")
        return False
    except Exception as e:
        messagebox.showerror("Install Failed", str(e))
        return False

def install_all_gclib_dlls():
    """Install both gclib.dll and gclibo.dll to System32 directory."""
    dll_files = ["gclib.dll", "gclibo.dll"]
    results = []
    
    for dll_name in dll_files:
        destination = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", dll_name)
        source = os.path.join(os.getcwd(), dll_name)

        if not os.path.exists(source):
            results.append(f"✗ {dll_name}: Not found in application folder")
            continue

        try:
            shutil.copy2(source, destination)
            results.append(f"✓ {dll_name}: Successfully installed to System32")
        except PermissionError:
            results.append(f"✗ {dll_name}: Permission denied - Run as Administrator")
            return False
        except Exception as e:
            results.append(f"✗ {dll_name}: {str(e)}")
            return False
    
    # Show results
    result_text = "\n".join(results)
    if all("✓" in result for result in results):
        messagebox.showinfo("Installation Complete", f"All DLL files installed successfully!\n\n{result_text}")
        return True
    else:
        messagebox.showerror("Installation Failed", f"Some DLL files failed to install:\n\n{result_text}")
        return False

def check_dll_installation():
    """Check if the DLL files are properly installed in System32."""
    dll_files = ["gclib.dll", "gclibo.dll"]
    system32_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
    
    results = []
    for dll_name in dll_files:
        dll_path = os.path.join(system32_path, dll_name)
        if os.path.exists(dll_path):
            results.append(f"✓ {dll_name}: Found in System32")
        else:
            results.append(f"✗ {dll_name}: Not found in System32")
    
    return results

def find_galil_com_ports():
    galil_ports = []
    ports = list_ports.comports()
    for port in ports:
        if "Galil" in port.description or "USB Serial" in port.description:
            galil_ports.append(port.device)
    return galil_ports

def validate_axis(axis):
    """Validate that the axis is one of A, B, C, or D."""
    valid_axes = ["A", "B", "C", "D"]
    if axis.upper() not in valid_axes:
        raise ValueError(f"Invalid axis '{axis}'. Must be one of {valid_axes}")
    return axis.upper()

# ============================================================================
# LOGGING AND UTILITY FUNCTIONS
# ============================================================================

class LoggingUtils:
    """Utility functions for logging and data processing"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback or self._default_log
        
    def _default_log(self, message: str):
        """Default logging function if no callback provided"""
        print(message)
    
    def log(self, message: str):
        """Log a message using the callback"""
        self.log_callback(message)
    
    def log_info(self, message: str):
        """Log an info message"""
        self.log(f"INFO: {message}")
    
    def log_success(self, message: str):
        """Log a success message"""
        self.log(f"SUCCESS: {message}")
    
    def log_error(self, message: str):
        """Log an error message"""
        self.log(f"ERROR: {message}")
    
    def append_test_log(self, line: str):
        """Append a line to the test log"""
        self.log(line)

def estimate_bm_from_movement(positions: List[float], total_movement: float) -> float:
    """Estimate BM (backlash compensation) from movement data"""
    if not positions or len(positions) < 2:
        return 0.0
    
    # Calculate the difference between first and last positions
    position_diff = abs(positions[-1] - positions[0])
    
    # Estimate BM as a percentage of total movement
    # This is a heuristic - actual BM calculation would be more complex
    if total_movement > 0:
        bm_estimate = (position_diff / total_movement) * 100.0
        # Cap the estimate at reasonable values
        return min(max(bm_estimate, 0.0), 50.0)
    
    return 0.0

def calculate_motion_parameters(speed: float, acceleration: float, deceleration: float) -> Dict[str, float]:
    """Calculate motion parameters for Galil controller"""
    return {
        'speed': max(1.0, speed),
        'acceleration': max(1.0, acceleration),
        'deceleration': max(1.0, deceleration),
        'jerk': max(1.0, acceleration * 0.1)  # Jerk is typically 10% of acceleration
    }

def validate_motion_parameters(params: Dict[str, float]) -> bool:
    """Validate motion parameters"""
    required_keys = ['speed', 'acceleration', 'deceleration']
    
    for key in required_keys:
        if key not in params:
            return False
        if not isinstance(params[key], (int, float)):
            return False
        if params[key] <= 0:
            return False
    
    return True

def format_position_value(position: float, precision: int = 2) -> str:
    """Format position value for display"""
    if position is None:
        return "N/A"
    
    try:
        return f"{position:.{precision}f}"
    except (ValueError, TypeError):
        return "N/A"

def calculate_encoder_resolution(steps_per_revolution: int, gear_ratio: float = 1.0) -> float:
    """Calculate encoder resolution in steps per unit"""
    if steps_per_revolution <= 0 or gear_ratio <= 0:
        return 0.0
    
    return steps_per_revolution * gear_ratio

def convert_units(value: float, from_units: str, to_units: str) -> float:
    """Convert between different units"""
    # Common unit conversions
    conversions = {
        ('mm', 'inches'): 0.0393701,
        ('inches', 'mm'): 25.4,
        ('degrees', 'radians'): math.pi / 180.0,
        ('radians', 'degrees'): 180.0 / math.pi,
        ('steps', 'mm'): 1.0,  # This would need to be configured based on system
        ('mm', 'steps'): 1.0,  # This would need to be configured based on system
    }
    
    conversion_key = (from_units.lower(), to_units.lower())
    if conversion_key in conversions:
        return value * conversions[conversion_key]
    
    # If no conversion found, return original value
    return value

def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max"""
    return max(min_val, min(max_val, value))

def is_within_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    """Check if actual value is within tolerance of expected value"""
    return abs(actual - expected) <= tolerance

def calculate_percentage_error(actual: float, expected: float) -> float:
    """Calculate percentage error between actual and expected values"""
    if expected == 0:
        return 0.0 if actual == 0 else float('inf')
    
    return ((actual - expected) / expected) * 100.0

def format_time_duration(seconds: float) -> str:
    """Format time duration in a human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float with a default"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert a value to int with a default"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
