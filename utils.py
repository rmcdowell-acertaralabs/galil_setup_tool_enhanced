from serial.tools import list_ports
import shutil
import os
from tkinter import messagebox

def install_gclib_dll():
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

def find_galil_com_ports():
    galil_ports = []
    ports = list_ports.comports()
    for port in ports:
        if "Galil" in port.description or "USB Serial" in port.description:
            galil_ports.append(port.device)
    return galil_ports
