import tkinter as tk
from tkinter import ttk, messagebox
from galil_interface import GalilController
from utils import find_galil_com_ports
from diagnostics import get_controller_info, get_diagnostics
from motor_setup import tune_axis, configure_axis
from network import set_ip_address
from encoder_overlay import EncoderOverlay
from config_manager import load_config, save_config
import os
from ctypes import cdll
from constants import (
    CONFIG_PATH, WINDOW_WIDTH, WINDOW_HEIGHT, STATUS_DISCONNECTED,
    CANVAS_WIDTH, CANVAS_HEIGHT, ENCODER_CENTER, ENCODER_RADIUS,
    DEFAULT_JOG_SPEED, DEFAULT_AXIS, DEFAULT_CLICKS_PER_TURN
)

controller = GalilController()

class GalilSetupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Galil DMC-4143 Setup Tool")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        if not self.check_gclib_dll():
            messagebox.showerror("Missing DLL", "Could not load gclib.dll. Make sure it is in the application folder or in your system PATH.")
            self.root.destroy()
            return

        self.config = load_config()

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.build_ui(self.main_frame)

        self.canvas = tk.Canvas(self.main_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='white')
        self.canvas.create_oval(
            ENCODER_CENTER[0]-ENCODER_RADIUS,
            ENCODER_CENTER[1]-ENCODER_RADIUS,
            ENCODER_CENTER[0]+ENCODER_RADIUS,
            ENCODER_CENTER[1]+ENCODER_RADIUS,
            outline="blue", width=2
        )
        self.canvas.pack(pady=5)
        self.encoder_overlay = EncoderOverlay(self.canvas, controller, center=ENCODER_CENTER, radius=ENCODER_RADIUS, axis="A", clicks_per_turn=DEFAULT_CLICKS_PER_TURN)
        self.root.after(200, self.update_encoder_position)

        self.diagnostics_frame = ttk.LabelFrame(self.main_frame, text="Diagnostics")
        self.diagnostics_frame.pack(padx=10, pady=10, fill="x")

        self.diagnostics_text = tk.Text(self.diagnostics_frame, height=10, width=80, wrap="word")
        self.diagnostics_text.pack(padx=5, pady=5)

        self.refresh_diagnostics_button = ttk.Button(self.diagnostics_frame, text="Refresh Diagnostics",
                                                     command=self.refresh_diagnostics)
        self.refresh_diagnostics_button.pack(pady=5)

        self.load_config_to_fields()

    def update_encoder_position(self):
        self.encoder_overlay.update()
        self.root.after(200, self.update_encoder_position)

    def refresh_diagnostics(self):
        if controller:
            diagnostics = get_diagnostics(controller)
            self.diagnostics_text.delete("1.0", tk.END)
            self.diagnostics_text.insert(tk.END, diagnostics)
        else:
            self.diagnostics_text.delete("1.0", tk.END)
            self.diagnostics_text.insert(tk.END, "Controller not connected.")

    def check_gclib_dll(self):
        try:
            cdll.LoadLibrary("gclib.dll")
            return True
        except OSError:
            return False

    def connect_to_controller(self):
        ports = find_galil_com_ports()
        if not ports:
            messagebox.showerror("Connection Error", "No Galil controller detected over USB.")
            return
        try:
            controller.connect(ports[0])
            self.status_var.set(f"Connected: {ports[0]}")
            info = get_controller_info(controller)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def build_ui(self, parent):
        frame = tk.Frame(parent)
        frame.pack(pady=10)

        tk.Label(frame, text="Axis:").grid(row=0, column=0, sticky="e")
        self.axis_entry = tk.Entry(frame, width=5)
        self.axis_entry.insert(0, DEFAULT_AXIS)
        self.axis_entry.grid(row=0, column=1)

        tk.Label(frame, text="Jog Speed:").grid(row=1, column=0, sticky="e")
        self.jog_speed_entry = tk.Entry(frame, width=10)
        self.jog_speed_entry.insert(0, str(DEFAULT_JOG_SPEED))
        self.jog_speed_entry.grid(row=1, column=1)



        tk.Button(frame, text="Jog +", command=self.jog_positive).grid(row=2, column=0)
        tk.Button(frame, text="Jog -", command=self.jog_negative).grid(row=2, column=1)
        tk.Button(frame, text="Stop", command=self.stop_motion).grid(row=2, column=2)

        tk.Button(frame, text="Connect", command=self.connect_to_controller).grid(row=3, column=0)
        tk.Button(frame, text="Run Diagnostics", command=self.run_diagnostics).grid(row=3, column=1)

        tk.Button(frame, text="Save Axis Preset", command=self.save_axis_preset).grid(row=4, column=0)
        tk.Button(frame, text="Load Axis Preset", command=self.load_axis_preset).grid(row=4, column=1)
        tk.Button(frame, text="Configure Axis", command=self.configure_selected_axis).grid(row=4, column=2)
        tk.Label(frame, text="IP Address:").grid(row=4, column=3, sticky="e")
        self.ip_entry = tk.Entry(frame, width=15)
        self.ip_entry.insert(0, self.config.get("ip_address", "192.168.0.100"))
        self.ip_entry.grid(row=4, column=4, padx=5)

        tk.Button(frame, text="Set IP Address", command=self.set_ip).grid(row=5, column=0)
        tk.Button(frame, text="Tune Axis", command=self.tune_motor).grid(row=5, column=1)
        tk.Button(frame, text="Install gclib.dll", command=self.install_gclib_dll).grid(row=5, column=2)

        tk.Label(frame, text="KP:").grid(row=6, column=0, sticky="e")
        self.kp_entry = tk.Entry(frame, width=10)
        self.kp_entry.grid(row=6, column=1)

        tk.Label(frame, text="KI:").grid(row=7, column=0, sticky="e")
        self.ki_entry = tk.Entry(frame, width=10)
        self.ki_entry.grid(row=7, column=1)

        tk.Label(frame, text="KD:").grid(row=8, column=0, sticky="e")
        self.kd_entry = tk.Entry(frame, width=10)
        self.kd_entry.grid(row=8, column=1)

        tk.Label(frame, text="SP:").grid(row=6, column=2, sticky="e")
        self.sp_entry = tk.Entry(frame, width=10)
        self.sp_entry.grid(row=6, column=3)

        tk.Label(frame, text="AC:").grid(row=7, column=2, sticky="e")
        self.ac_entry = tk.Entry(frame, width=10)
        self.ac_entry.grid(row=7, column=3)

        tk.Label(frame, text="DC:").grid(row=8, column=2, sticky="e")
        self.dc_entry = tk.Entry(frame, width=10)
        self.dc_entry.grid(row=8, column=3)

        tk.Label(frame, text="TL:").grid(row=9, column=2, sticky="e")
        self.tl_entry = tk.Entry(frame, width=10)
        self.tl_entry.grid(row=9, column=3)

        self.status_var = tk.StringVar(value=STATUS_DISCONNECTED)
        tk.Label(parent, textvariable=self.status_var).pack()

        self.info_text = tk.Text(parent, height=5, width=50)
        self.info_text.pack(pady=5)

    def jog_positive(self):
        axis = self.axis_entry.get().upper()
        speed = self.jog_speed_entry.get()
        try:
            # Load preset parameters if available
            preset = self.config.get("axis_presets", {}).get(axis, {})
            if preset:
                configure_axis(controller, axis, preset)

            controller.send_command(f"SH{axis}")  # Servo enable
            controller.send_command(f"JG{axis}={speed}")
            controller.send_command(f"BG{axis}")
        except Exception as e:
            messagebox.showerror("Jog Error", str(e))

    def jog_negative(self):
        axis = self.axis_entry.get().upper()
        speed = self.jog_speed_entry.get()
        try:
            preset = self.config.get("axis_presets", {}).get(axis, {})
            if preset:
                configure_axis(controller, axis, preset)

            controller.send_command(f"SH{axis}")  # Servo enable
            controller.send_command(f"JG{axis}=-{speed}")
            controller.send_command(f"BG{axis}")
        except Exception as e:
            messagebox.showerror("Jog Error", str(e))

    def stop_motion(self):
        axis = self.axis_entry.get().upper()
        try:
            controller.send_command(f"ST {axis}")
        except Exception as e:
            messagebox.showerror("Stop Error", str(e))

    def run_diagnostics(self):
        try:
            info = get_controller_info(controller)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, info)
        except Exception as e:
            messagebox.showerror("Diagnostics Error", str(e))

    def load_config_to_fields(self):
        if "jog_speed" in self.config:
            self.jog_speed_entry.delete(0, tk.END)
            self.jog_speed_entry.insert(0, str(self.config["jog_speed"]))
        if "ip_address" in self.config:
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, self.config["ip_address"])

    def save_axis_preset(self):
        axis = self.axis_entry.get().upper()
        speed = self.jog_speed_entry.get()
        kp = self.kp_entry.get()
        ki = self.ki_entry.get()
        kd = self.kd_entry.get()
        sp = self.sp_entry.get()
        ac = self.ac_entry.get()
        dc = self.dc_entry.get()
        tl = self.tl_entry.get()
        self.config["ip_address"] = self.ip_entry.get()
        if "axis_presets" not in self.config:
            self.config["axis_presets"] = {}
        self.config["axis_presets"][axis] = {
            "jog_speed": speed,
            "kp": kp,
            "ki": ki,
            "kd": kd,
            "sp": sp,
            "ac": ac,
            "dc": dc,
            "tl": tl
        }
        save_config(self.config)
        messagebox.showinfo("Saved", f"Preset saved for axis {axis}.")

    def load_axis_preset(self):
        axis = self.axis_entry.get().upper()
        try:
            preset = self.config.get("axis_presets", {}).get(axis, {})
            if preset:
                self.jog_speed_entry.delete(0, tk.END)
                self.jog_speed_entry.insert(0, preset.get("jog_speed", str(DEFAULT_JOG_SPEED)))
                self.kp_entry.delete(0, tk.END)
                self.kp_entry.insert(0, preset.get("kp", ""))
                self.ki_entry.delete(0, tk.END)
                self.ki_entry.insert(0, preset.get("ki", ""))
                self.kd_entry.delete(0, tk.END)
                self.kd_entry.insert(0, preset.get("kd", ""))
                self.sp_entry.delete(0, tk.END)
                self.sp_entry.insert(0, preset.get("sp", ""))
                self.ac_entry.delete(0, tk.END)
                self.ac_entry.insert(0, preset.get("ac", ""))
                self.dc_entry.delete(0, tk.END)
                self.dc_entry.insert(0, preset.get("dc", ""))
                self.tl_entry.delete(0, tk.END)
                self.tl_entry.insert(0, preset.get("tl", ""))
                self.ip_entry.delete(0, tk.END)
                self.ip_entry.insert(0, self.config.get("ip_address", "192.168.0.100"))
                messagebox.showinfo("Loaded", f"Preset loaded for axis {axis}.")
            else:
                messagebox.showwarning("Missing Preset", f"No preset found for axis {axis}.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def configure_selected_axis(self):
        axis = self.axis_entry.get().upper()
        try:
            preset = self.config.get("axis_presets", {}).get(axis, {})
            if not preset:
                messagebox.showwarning("Missing Preset", f"No preset found for axis {axis}.")
                return
            configure_axis(controller, axis, preset)
            messagebox.showinfo("Configured", f"Axis {axis} configured.")
        except Exception as e:
            messagebox.showerror("Configure Error", str(e))

    def set_ip(self):
        try:
            new_ip = self.ip_entry.get()
            set_ip_address(controller, new_ip)
            self.config["ip_address"] = new_ip
            save_config(self.config)
            messagebox.showinfo("IP Set", f"IP address set to {new_ip}")
        except Exception as e:
            messagebox.showerror("IP Error", f"Failed to set IP: {e}")

    def install_gclib_dll(self):
        import shutil
        import ctypes
        import sys

        dll_name = "gclib.dll"
        src_path = os.path.join(os.getcwd(), dll_name)
        system_folder = os.path.join(os.environ['WINDIR'], 'System32' if sys.maxsize > 2 ** 32 else 'SysWOW64')
        dest_path = os.path.join(system_folder, dll_name)

        if not os.path.exists(src_path):
            messagebox.showerror("Install Failed", f"{dll_name} not found in application folder.")
            return

        try:
            shutil.copy(src_path, dest_path)
            messagebox.showinfo("Install Success", f"{dll_name} installed to {system_folder}")
        except PermissionError:
            messagebox.showerror("Permission Denied", "Administrator privileges required to install DLL.")
        except Exception as e:
            messagebox.showerror("Install Failed", str(e))

    def tune_motor(self):
        axis = self.axis_entry.get().upper()
        try:
            kp = float(self.kp_entry.get())
            ki = float(self.ki_entry.get())
            kd = float(self.kd_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "KP, KI, and KD must be valid numbers.")
            return

        try:
            tune_axis(controller, axis, kp, ki, kd)
            messagebox.showinfo("Tuned", f"Axis {axis} tuned successfully.")
        except Exception as e:
            messagebox.showerror("Tune Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = GalilSetupApp(root)
    root.mainloop()
