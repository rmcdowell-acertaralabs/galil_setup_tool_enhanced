from serial.tools import list_ports
import shutil
import os
from tkinter import messagebox

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
