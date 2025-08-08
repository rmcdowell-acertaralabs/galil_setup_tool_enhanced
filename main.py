import tkinter as tk
from tkinter import ttk, messagebox
from galil_interface import GalilController
from utils import find_galil_com_ports
from diagnostics import get_controller_info, get_diagnostics
from motor_setup import tune_axis, configure_axis
from encoder_overlay import EncoderOverlay
from config_manager import load_config, save_config
import os
from ctypes import cdll
from constants import (
    CONFIG_PATH, WINDOW_WIDTH, WINDOW_HEIGHT, STATUS_DISCONNECTED,
    CANVAS_WIDTH, CANVAS_HEIGHT, ENCODER_CENTER, ENCODER_RADIUS,
    DEFAULT_JOG_SPEED, DEFAULT_AXIS, DEFAULT_CLICKS_PER_TURN,
    SERVO_BITS, VALID_AXES
)
from gclib import GclibError
import math

class Futuristic3DVisualizer:
    def __init__(self, canvas, controller):
        self.canvas = canvas
        self.controller = controller
        self.center_x = CANVAS_WIDTH // 2
        self.center_y = CANVAS_HEIGHT // 2
        self.radius = 80
        self.axis_positions = {"A": 0, "B": 0, "C": 0, "D": 0}
        self.axis_colors = {"A": "#FF4444", "B": "#44FF44", "C": "#4444FF", "D": "#FFFF44"}
        self.axis_angles = {"A": 0, "B": 90, "C": 180, "D": 270}
        
        # Create 3D base
        self.create_3d_base()
        
    def create_3d_base(self):
        """Create the 3D base structure"""
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw 3D coordinate system
        # X-axis (red)
        self.canvas.create_line(
            self.center_x - 100, self.center_y, 
            self.center_x + 100, self.center_y, 
            fill="#FF4444", width=3, tags="axis"
        )
        self.canvas.create_polygon(
            self.center_x + 100, self.center_y,
            self.center_x + 90, self.center_y - 5,
            self.center_x + 90, self.center_y + 5,
            fill="#FF4444", tags="axis"
        )
        
        # Y-axis (green)
        self.canvas.create_line(
            self.center_x, self.center_y - 100,
            self.center_x, self.center_y + 100,
            fill="#44FF44", width=3, tags="axis"
        )
        self.canvas.create_polygon(
            self.center_x, self.center_y - 100,
            self.center_x - 5, self.center_y - 90,
            self.center_x + 5, self.center_y - 90,
            fill="#44FF44", tags="axis"
        )
        
        # Z-axis (blue) - perspective
        self.canvas.create_line(
            self.center_x - 50, self.center_y + 50,
            self.center_x + 50, self.center_y - 50,
            fill="#4444FF", width=3, tags="axis"
        )
        self.canvas.create_polygon(
            self.center_x + 50, self.center_y - 50,
            self.center_x + 45, self.center_y - 45,
            self.center_x + 55, self.center_y - 45,
            fill="#4444FF", tags="axis"
        )
        
        # Draw 3D cube wireframe
        size = 60
        # Front face
        self.canvas.create_rectangle(
            self.center_x - size, self.center_y - size,
            self.center_x + size, self.center_y + size,
            outline="#888888", width=2, tags="cube"
        )
        # Back face (offset)
        self.canvas.create_rectangle(
            self.center_x - size + 20, self.center_y - size - 20,
            self.center_x + size + 20, self.center_y + size - 20,
            outline="#888888", width=2, tags="cube"
        )
        # Connecting lines
        self.canvas.create_line(
            self.center_x - size, self.center_y - size,
            self.center_x - size + 20, self.center_y - size - 20,
            fill="#888888", width=2, tags="cube"
        )
        self.canvas.create_line(
            self.center_x + size, self.center_y - size,
            self.center_x + size + 20, self.center_y - size - 20,
            fill="#888888", width=2, tags="cube"
        )
        self.canvas.create_line(
            self.center_x + size, self.center_y + size,
            self.center_x + size + 20, self.center_y + size - 20,
            fill="#888888", width=2, tags="cube"
        )
        self.canvas.create_line(
            self.center_x - size, self.center_y + size,
            self.center_x - size + 20, self.center_y + size - 20,
            fill="#888888", width=2, tags="cube"
        )
        
        # Add axis labels
        self.canvas.create_text(
            self.center_x + 120, self.center_y,
            text="X (A)", fill="#FF4444", font=("Arial", 10, "bold"), tags="label"
        )
        self.canvas.create_text(
            self.center_x, self.center_y - 120,
            text="Y (B)", fill="#44FF44", font=("Arial", 10, "bold"), tags="label"
        )
        self.canvas.create_text(
            self.center_x + 70, self.center_y - 70,
            text="Z (C)", fill="#4444FF", font=("Arial", 10, "bold"), tags="label"
        )
        
        # Create position indicators
        self.create_position_indicators()
        
    def create_position_indicators(self):
        """Create position indicators for each axis"""
        for axis in ["A", "B", "C", "D"]:
            # Create position dot
            x, y = self.get_axis_position(axis, 0)
            self.canvas.create_oval(
                x - 5, y - 5, x + 5, y + 5,
                fill=self.axis_colors[axis], outline="white", width=2,
                tags=f"pos_{axis}"
            )
            # Create position text
            self.canvas.create_text(
                x + 15, y - 15,
                text=f"{axis}: 0", fill=self.axis_colors[axis],
                font=("Arial", 8, "bold"), tags=f"text_{axis}"
            )
    
    def get_axis_position(self, axis, position):
        """Calculate 3D position for axis"""
        # Normalize position to -1 to 1 range
        normalized_pos = max(-1, min(1, position / 100000))
        
        if axis == "A":  # X-axis
            return (self.center_x + normalized_pos * 80, self.center_y)
        elif axis == "B":  # Y-axis
            return (self.center_x, self.center_y - normalized_pos * 80)
        elif axis == "C":  # Z-axis (perspective)
            return (self.center_x + normalized_pos * 40, self.center_y - normalized_pos * 40)
        else:  # D-axis (diagonal)
            return (self.center_x + normalized_pos * 60, self.center_y - normalized_pos * 60)
    
    def update_position(self, axis, position):
        """Update position indicator for an axis"""
        x, y = self.get_axis_position(axis, position)
        
        # Update position dot
        self.canvas.coords(f"pos_{axis}", x - 5, y - 5, x + 5, y + 5)
        
        # Update position text
        self.canvas.coords(f"text_{axis}", x + 15, y - 15)
        self.canvas.itemconfig(f"text_{axis}", text=f"{axis}: {position}")
        
        # Store position
        self.axis_positions[axis] = position
    
    def update_from_controller(self):
        """Update positions from controller data"""
        try:
            if hasattr(self.controller, 'g') and self.controller.g:
                # Get position data from controller
                response = self.controller.send_command("TP")
                if response:
                    positions = response.split(',')
                    if len(positions) >= 4:
                        for i, axis in enumerate(["A", "B", "C", "D"]):
                            try:
                                pos = int(positions[i])
                                self.update_position(axis, pos)
                            except (ValueError, IndexError):
                                pass
        except Exception:
            pass

class GalilSetupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Galil DMC-4143 Futuristic Control Interface")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)  # Make window resizable
        
        # Set dark theme
        self.setup_dark_theme()
        
        if not self.check_gclib_dll():
            messagebox.showerror(
                "Missing DLL",
                "Could not load gclib.dll. Make sure it is in the application folder or in your system PATH."
            )
            self.root.destroy()
            return

        # Initialize controller as instance variable
        self.controller = GalilController()
        self.config = load_config()
        
        # Create main container with futuristic styling
        self.create_futuristic_layout()
        
        # Initialize 3D visualizer
        self.visualizer = Futuristic3DVisualizer(self.canvas, self.controller)
        
        # Start position updates
        self.root.after(200, self.update_3d_position)

    def setup_dark_theme(self):
        """Setup dark futuristic theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure dark theme colors
        style.configure('Dark.TFrame', background='#1a1a1a')
        style.configure('Dark.TLabel', background='#1a1a1a', foreground='#00ff00')
        style.configure('Dark.TButton', 
                       background='#2a2a2a', 
                       foreground='#00ff00',
                       borderwidth=2,
                       relief='raised')
        style.configure('Futuristic.TButton',
                       background='#003300',
                       foreground='#00ff00',
                       borderwidth=3,
                       relief='raised')
        style.configure('Danger.TButton',
                       background='#330000',
                       foreground='#ff0000',
                       borderwidth=3,
                       relief='raised')

    def create_futuristic_layout(self):
        """Create the futuristic layout"""
        # Main container
        self.main_container = tk.Frame(self.root, bg='#1a1a1a')
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_frame = tk.Frame(self.main_container, bg='#1a1a1a')
        title_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(
            title_frame,
            text="GALIL DMC-4143 CONTROL INTERFACE",
            font=("Courier", 16, "bold"),
            bg='#1a1a1a',
            fg='#00ff00'
        )
        title_label.pack()
        
        # Create main content area
        content_frame = tk.Frame(self.main_container, bg='#1a1a1a')
        content_frame.pack(fill="both", expand=True)
        
        # Left panel - Controls
        self.create_control_panel(content_frame)
        
        # Right panel - 3D Visualization
        self.create_visualization_panel(content_frame)
        
        # Bottom panel - Diagnostics
        self.create_diagnostics_panel()

    def create_control_panel(self, parent):
        """Create the control panel"""
        # Create a frame with scrollbar
        control_container = tk.Frame(parent, bg='#1a1a1a')
        control_container.pack(side="left", fill="y", padx=(0, 10))
        
        # Create canvas for scrolling
        canvas = tk.Canvas(control_container, bg='#2a2a2a', highlightthickness=0)
        scrollbar = tk.Scrollbar(control_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2a2a2a')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control panel title
        tk.Label(
            scrollable_frame,
            text="CONTROL PANEL",
            font=("Courier", 12, "bold"),
            bg='#2a2a2a',
            fg='#00ff00'
        ).pack(pady=10)
        
        # Connection status
        self.status_var = tk.StringVar(value=STATUS_DISCONNECTED)
        status_label = tk.Label(
            scrollable_frame,
            textvariable=self.status_var,
            font=("Courier", 10, "bold"),
            bg='#2a2a2a',
            fg='#ff0000'
        )
        status_label.pack(pady=5)
        
        # Connection type selection
        conn_type_frame = tk.LabelFrame(scrollable_frame, text="CONNECTION TYPE", 
                                      bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        conn_type_frame.pack(fill="x", padx=10, pady=5)
        
        self.conn_type = tk.StringVar(value="USB")
        tk.Radiobutton(conn_type_frame, text="USB", variable=self.conn_type, value="USB",
                      bg='#2a2a2a', fg='#00ff00', selectcolor='#1a1a1a',
                      font=("Courier", 9)).pack(side="left", padx=5)
        tk.Radiobutton(conn_type_frame, text="Network", variable=self.conn_type, value="Network",
                      bg='#2a2a2a', fg='#00ff00', selectcolor='#1a1a1a',
                      font=("Courier", 9)).pack(side="left", padx=5)
        
        # IP Address entry (for network connection)
        ip_frame = tk.LabelFrame(scrollable_frame, text="IP ADDRESS", 
                               bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        ip_frame.pack(fill="x", padx=10, pady=5)
        
        self.ip_entry = tk.Entry(ip_frame, width=15, bg='#1a1a1a', fg='#00ff00',
                                insertbackground='#00ff00')
        self.ip_entry.insert(0, self.config.get("ip_address", "192.168.0.100"))
        self.ip_entry.pack(pady=5)
        
        # Axis selection
        axis_frame = tk.LabelFrame(scrollable_frame, text="AXIS SELECTION", 
                                 bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        axis_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(axis_frame, text="Axis:", bg='#2a2a2a', fg='#00ff00').pack(side="left", padx=5)
        self.axis_entry = tk.Entry(axis_frame, width=5, bg='#1a1a1a', fg='#00ff00', 
                                 insertbackground='#00ff00')
        self.axis_entry.insert(0, DEFAULT_AXIS)
        self.axis_entry.pack(side="left", padx=5)
        
        # Speed control
        speed_frame = tk.LabelFrame(scrollable_frame, text="SPEED CONTROL", 
                                  bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        speed_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(speed_frame, text="Speed:", bg='#2a2a2a', fg='#00ff00').pack(side="left", padx=5)
        self.jog_speed_entry = tk.Entry(speed_frame, width=10, bg='#1a1a1a', fg='#00ff00',
                                      insertbackground='#00ff00')
        self.jog_speed_entry.insert(0, str(DEFAULT_JOG_SPEED))
        self.jog_speed_entry.pack(side="left", padx=5)
        
        # Motion controls
        motion_frame = tk.LabelFrame(scrollable_frame, text="MOTION CONTROLS", 
                                   bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        motion_frame.pack(fill="x", padx=10, pady=5)
        
        # Jog buttons with futuristic styling
        jog_frame = tk.Frame(motion_frame, bg='#2a2a2a')
        jog_frame.pack(pady=5)
        
        tk.Button(jog_frame, text="JOG +", width=8, command=self.jog_positive,
                 bg='#003300', fg='#00ff00', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=2)
        tk.Button(jog_frame, text="JOG -", width=8, command=self.jog_negative,
                 bg='#003300', fg='#00ff00', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=2)
        tk.Button(jog_frame, text="STOP", width=8, command=self.stop_motion,
                 bg='#330000', fg='#ff0000', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=2)
        
        # Connection controls
        conn_frame = tk.LabelFrame(scrollable_frame, text="CONNECTION", 
                                 bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(conn_frame, text="CONNECT", command=self.connect_to_controller,
                 bg='#003300', fg='#00ff00', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(pady=5)
        
        # Test buttons
        test_frame = tk.LabelFrame(scrollable_frame, text="DIAGNOSTICS", 
                                 bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        test_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(test_frame, text="RUN DIAGNOSTICS", command=self.run_diagnostics,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(test_frame, text="TEST CONNECTION", command=self.test_connection,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(test_frame, text="TEST COMMANDS", command=self.test_jog_commands,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(test_frame, text="TEST SERVO", command=self.test_servo_commands,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # Configuration buttons
        config_frame = tk.LabelFrame(scrollable_frame, text="CONFIGURATION", 
                                   bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        config_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(config_frame, text="CONFIGURE AXIS", command=self.configure_selected_axis,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(config_frame, text="SET IP", command=self.set_controller_ip,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(config_frame, text="GET IP", command=self.get_controller_ip,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(config_frame, text="SAVE CONFIG", command=self.save_current_config,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # Position control
        pos_frame = tk.LabelFrame(scrollable_frame, text="POSITION CONTROL", 
                                bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        pos_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(pos_frame, text="RESET POSITION", command=self.reset_axis_position,
                 bg='#330033', fg='#ff00ff', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # PID controls
        pid_frame = tk.LabelFrame(scrollable_frame, text="PID TUNING", 
                                bg='#2a2a2a', fg='#00ff00', font=("Courier", 10, "bold"))
        pid_frame.pack(fill="x", padx=10, pady=5)
        
        for i, label in enumerate(["KP", "KI", "KD"]):
            frame = tk.Frame(pid_frame, bg='#2a2a2a')
            frame.pack(fill="x", pady=2)
            tk.Label(frame, text=f"{label}:", bg='#2a2a2a', fg='#00ff00').pack(side="left", padx=5)
            entry = tk.Entry(frame, width=8, bg='#1a1a1a', fg='#00ff00', insertbackground='#00ff00')
            entry.pack(side="right", padx=5)
            setattr(self, f"{label.lower()}_entry", entry)
        
        tk.Button(pid_frame, text="TUNE AXIS", command=self.tune_motor,
                 bg='#003300', fg='#00ff00', font=("Courier", 9, "bold"),
                 relief='raised', bd=3).pack(pady=5)

    def create_visualization_panel(self, parent):
        """Create the 3D visualization panel"""
        viz_frame = tk.Frame(parent, bg='#1a1a1a')
        viz_frame.pack(side="right", fill="both", expand=True)
        
        # 3D Visualization title
        tk.Label(
            viz_frame,
            text="3D MOVEMENT TRACKER",
            font=("Courier", 12, "bold"),
            bg='#1a1a1a',
            fg='#00ff00'
        ).pack(pady=10)
        
        # Canvas for 3D visualization
        self.canvas = tk.Canvas(
            viz_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg='#0a0a0a',
            highlightthickness=2,
            highlightbackground='#00ff00'
        )
        self.canvas.pack(pady=10)

    def create_diagnostics_panel(self):
        """Create the diagnostics panel"""
        diag_frame = tk.LabelFrame(self.main_container, text="SYSTEM DIAGNOSTICS", 
                                 bg='#1a1a1a', fg='#00ff00', font=("Courier", 12, "bold"))
        diag_frame.pack(fill="x", pady=10)
        
        # Diagnostics text area
        self.diagnostics_text = tk.Text(
            diag_frame,
            height=8,
            width=80,
            wrap="word",
            bg='#0a0a0a',
            fg='#00ff00',
            insertbackground='#00ff00',
            font=("Courier", 9)
        )
        self.diagnostics_text.pack(padx=10, pady=10)
        
        # Refresh button
        tk.Button(diag_frame, text="REFRESH DIAGNOSTICS", command=self.refresh_diagnostics,
                 bg='#003300', fg='#00ff00', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(pady=5)

    def update_3d_position(self):
        """Update 3D position display"""
        try:
            self.visualizer.update_from_controller()
        except Exception:
            pass
        self.root.after(100, self.update_3d_position)  # Increased frequency for more responsive updates

    def _append_diagnostic(self, line: str):
        """Insert a single line into the diagnostics box and scroll."""
        self.diagnostics_text.insert(tk.END, line + "\n")
        self.diagnostics_text.see(tk.END)

    def _finish_diagnostics(self):
        """Re-enable diagnostics buttons when done."""
        pass  # Updated for new layout

    def refresh_diagnostics(self):
        """Fetch a one‐off diagnostics snapshot."""
        if getattr(self.controller, "g", None):
            diag = get_diagnostics(self.controller)
            self.diagnostics_text.delete("1.0", tk.END)
            self.diagnostics_text.insert("1.0", diag)
        else:
            self.diagnostics_text.delete("1.0", tk.END)
            self.diagnostics_text.insert("1.0", "Controller not connected.")

    def check_gclib_dll(self):
        try:
            cdll.LoadLibrary("gclib.dll")
            return True
        except OSError:
            return False

    def connect_to_controller(self):
        """Connect to controller via USB or Network"""
        conn_type = self.conn_type.get()
        
        if conn_type == "USB":
            ports = find_galil_com_ports()
            if not ports:
                messagebox.showerror("Connection Error", "No Galil controller detected over USB.")
                return
            address = ports[0]
        else:  # Network
            address = self.ip_entry.get().strip()
            if not address:
                messagebox.showerror("Connection Error", "Please enter an IP address.")
                return
        
        try:
            self.controller.connect(address)
            self.status_var.set(f"Connected: {address}")
            
            # Update status color
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget("textvariable") == self.status_var:
                    widget.config(fg='#00ff00')
                    break

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_var.set(STATUS_DISCONNECTED)

    def jog_positive(self):
        axis = self.axis_entry.get().upper()
        speed = self.jog_speed_entry.get()
        
        # Check if controller is connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Validate axis
            if axis not in SERVO_BITS:
                messagebox.showerror("Invalid Axis", f"Axis {axis} is not valid. Use A, B, C, or D.")
                return
                
            # Validate speed
            try:
                speed_val = int(speed)
                if speed_val <= 0:
                    messagebox.showerror("Invalid Speed", "Speed must be a positive number.")
                    return
            except ValueError:
                messagebox.showerror("Invalid Speed", "Speed must be a valid number.")
                return

            # apply preset if any
            preset = self.config.get("axis_presets", {}).get(axis, {})
            if preset:
                configure_axis(self.controller, axis, preset)

            # Servo-on using axis letter (no space)
            self.controller.send_command(f"SH{axis}")
            # Jog forward (no space after JG)
            self.controller.send_command(f"JG{axis}={speed}")
            # Begin (no space after BG)
            self.controller.send_command(f"BG{axis}")
            
            # Update 3D display with actual position
            self.update_position_from_controller(axis)
            
            # Schedule additional updates for smooth visual feedback
            def delayed_update():
                self.update_position_from_controller(axis)
                self.visualizer.update_from_controller()
            
            # Update after a short delay to show movement
            self.root.after(50, delayed_update)
            
        except Exception as e:
            messagebox.showerror("Jog Error", f"Error: {str(e)}")

    def jog_negative(self):
        axis = self.axis_entry.get().upper()
        speed = self.jog_speed_entry.get()
        
        # Check if controller is connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Validate axis
            if axis not in SERVO_BITS:
                messagebox.showerror("Invalid Axis", f"Axis {axis} is not valid. Use A, B, C, or D.")
                return
                
            # Validate speed
            try:
                speed_val = int(speed)
                if speed_val <= 0:
                    messagebox.showerror("Invalid Speed", "Speed must be a positive number.")
                    return
            except ValueError:
                messagebox.showerror("Invalid Speed", "Speed must be a valid number.")
                return

            preset = self.config.get("axis_presets", {}).get(axis, {})
            if preset:
                configure_axis(self.controller, axis, preset)

            self.controller.send_command(f"SH{axis}")
            self.controller.send_command(f"JG{axis}=-{speed}")
            self.controller.send_command(f"BG{axis}")
            
            # Update 3D display with actual position
            self.update_position_from_controller(axis)
            
            # Schedule additional updates for smooth visual feedback
            def delayed_update():
                self.update_position_from_controller(axis)
                self.visualizer.update_from_controller()
            
            # Update after a short delay to show movement
            self.root.after(50, delayed_update)
            
        except Exception as e:
            messagebox.showerror("Jog Error", f"Error: {str(e)}")

    def stop_motion(self):
        axis = self.axis_entry.get().upper()
        
        # Check if controller is connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Validate axis
            if axis not in SERVO_BITS:
                messagebox.showerror("Invalid Axis", f"Axis {axis} is not valid. Use A, B, C, or D.")
                return
                
            # Stop command
            self.controller.send_command(f"ST{axis}")
            
            # Update 3D display with actual position
            self.update_position_from_controller(axis)
            
        except Exception as e:
            messagebox.showerror("Stop Error", str(e))

    def update_position_from_controller(self, axis):
        """Update 3D display with actual position from controller"""
        try:
            if hasattr(self.controller, 'g') and self.controller.g:
                response = self.controller.send_command("TP")
                if response:
                    positions = response.split(',')
                    if len(positions) >= 4:
                        axis_index = {"A": 0, "B": 1, "C": 2, "D": 3}.get(axis, 0)
                        try:
                            pos = int(positions[axis_index])
                            self.visualizer.update_position(axis, pos)
                        except (ValueError, IndexError):
                            pass
        except Exception:
            pass

    def test_jog_commands(self):
        """Test different jog command formats to find the correct syntax."""
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        axis = self.axis_entry.get().upper()
        speed = self.jog_speed_entry.get()
        
        # Test various command formats
        test_commands = [
            # Standard format with spaces
            f"SH {SERVO_BITS[axis]}",
            f"JG {axis}={speed}",
            f"BG {axis}",
            f"ST {axis}",
            
            # Alternative formats without spaces
            f"SH{SERVO_BITS[axis]}",
            f"JG{axis}={speed}",
            f"BG{axis}",
            
            # Alternative servo-on formats
            f"SH{axis}",
            f"SH {axis}",
            
            # Alternative jog formats
            f"JG{axis} {speed}",
            f"JG {axis} {speed}",
            
            # Test individual commands
            "SH",
            "JG",
            "BG",
            "ST",
            
            # Test speed setting first
            f"SP {axis}={speed}",
            f"SP{axis}={speed}",
            f"SP {axis}=1000",
            f"SP{axis}=1000"
        ]
        
        results = []
        for cmd in test_commands:
            try:
                response = self.controller.send_command(cmd)
                results.append(f"✓ {cmd}: {response}")
            except Exception as e:
                results.append(f"✗ {cmd}: {str(e)}")
        
        messagebox.showinfo("Command Test Results", "\n".join(results))

    def test_servo_commands(self):
        """Test different servo-on command formats."""
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        axis = self.axis_entry.get().upper()
        
        # Test various servo-on formats
        servo_commands = [
            f"SH {SERVO_BITS[axis]}",  # Bitmask with space
            f"SH{SERVO_BITS[axis]}",    # Bitmask without space
            f"SH {axis}",                # Axis letter with space
            f"SH{axis}",                 # Axis letter without space
            f"SH {axis}1",              # Axis letter with 1
            f"SH{axis}1",               # Axis letter with 1
            f"SH {axis}ON",             # Axis letter with ON
            f"SH{axis}ON",              # Axis letter with ON
            "SH",                       # Just SH
            "SH1",                      # Just SH1
            "SHA",                      # Just SHA
        ]
        
        results = []
        for cmd in servo_commands:
            try:
                response = self.controller.send_command(cmd)
                results.append(f"✓ {cmd}: {response}")
            except Exception as e:
                results.append(f"✗ {cmd}: {str(e)}")
        
        messagebox.showinfo("Servo Test Results", "\n".join(results))

    def configure_selected_axis(self):
        """Configure the selected axis with preset settings."""
        axis = self.axis_entry.get().upper()
        
        # Check if controller is connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Validate axis
            if axis not in SERVO_BITS:
                messagebox.showerror("Invalid Axis", f"Axis {axis} is not valid. Use A, B, C, or D.")
                return
            
            # Get preset for this axis
            preset = self.config.get("axis_presets", {}).get(axis, {})
            if not preset:
                messagebox.showerror("Configuration Error", f"No preset found for axis {axis}")
                return
            
            # Apply configuration
            configure_axis(self.controller, axis, preset)
            messagebox.showinfo("Configuration Success", f"Axis {axis} configured with preset settings.")
            
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Error configuring axis {axis}: {str(e)}")

    def save_current_config(self):
        """Save current configuration to file."""
        try:
            # Update config with current values
            self.config["ip_address"] = self.ip_entry.get()
            self.config["jog_speed"] = int(self.jog_speed_entry.get())
            
            # Save to file
            save_config(self.config)
            messagebox.showinfo("Configuration Saved", "Current settings have been saved to config.json")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving configuration: {str(e)}")

    def run_diagnostics(self):
        import threading, time

        # Must be connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Diagnostics Error", "Controller not connected. Please click Connect first.")
            return

        self.diagnostics_text.delete("1.0", tk.END)

        def worker():
            axes = ["A", "B", "C", "D"]
            SPEED = 10000  # Use a reasonable speed for testing
            TIMEOUT_S = 5

            self.root.after(0, self._append_diagnostic, "=== ±1 cm Movement Test ===")
            for axis in axes:
                # Servo-on
                try:
                    self.controller.send_command(f"SH{axis}")
                    self.root.after(0, self._append_diagnostic, f"Servo-on Axis {axis}")
                except Exception as e:
                    self.root.after(0, self._append_diagnostic, f"Axis {axis}: servo-on failed: {e}")
                    continue  # Try next axis instead of returning

                # Set speed
                try:
                    self.controller.send_command(f"SP{axis}={SPEED}")
                    self.root.after(0, self._append_diagnostic, f"Speed set for Axis {axis}")
                except Exception as e:
                    self.root.after(0, self._append_diagnostic, f"Axis {axis}: speed set failed: {e}")
                    continue

                # ±1 cm moves (positive then negative)
                for direction in (SPEED, -SPEED):
                    try:
                        # Use JG for continuous movement
                        self.controller.send_command(f"JG{axis}={direction}")
                        self.controller.send_command(f"BG{axis}")
                        self.root.after(
                            0, self._append_diagnostic,
                            f"Axis {axis}: moving {direction:+} speed..."
                        )
                    except Exception as e:
                        self.root.after(
                            0, self._append_diagnostic,
                            f"Axis {axis}: move cmd failed: {e}"
                        )
                        continue

                    # Wait for movement to complete
                    time.sleep(1)  # Simple wait instead of complex polling
                    
                    # Stop the movement
                    try:
                        self.controller.send_command(f"ST{axis}")
                        self.root.after(
                            0, self._append_diagnostic,
                            f"Axis {axis}: movement stopped"
                        )
                    except Exception as e:
                        self.root.after(
                            0, self._append_diagnostic,
                            f"Axis {axis}: stop failed: {e}"
                        )

                self.root.after(
                    0, self._append_diagnostic,
                    f"Axis {axis}: ±1 cm test done"
                )

            # Simple movement test
            self.root.after(0, self._append_diagnostic, "\n=== Simple Movement Test ===")
            try:
                # Test axis A with a simple movement
                self.controller.send_command("SHA")
                self.controller.send_command("SPA=5000")
                self.controller.send_command("JGA=5000")
                self.controller.send_command("BGA")
                self.root.after(0, self._append_diagnostic, "Axis A: Started movement")
                
                time.sleep(2)  # Let it move for 2 seconds
                
                self.controller.send_command("STA")
                self.root.after(0, self._append_diagnostic, "Axis A: Movement stopped")
            except Exception as e:
                self.root.after(0, self._append_diagnostic, f"Simple movement test failed: {e}")

            # Full settings dump
            self.root.after(0, self._append_diagnostic, "\n=== Full Settings Dump ===")
            try:
                info = get_controller_info(self.controller)
                for line in info.splitlines():
                    self.root.after(0, self._append_diagnostic, line)
            except Exception as e:
                self.root.after(0, self._append_diagnostic, f"Error reading settings: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def load_config_to_fields(self):
        if "jog_speed" in self.config:
            self.jog_speed_entry.delete(0, tk.END)
            self.jog_speed_entry.insert(0, str(self.config["jog_speed"]))

    def tune_motor(self):
        axis = self.axis_entry.get().upper()
        
        # Check if controller is connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            kp = float(self.kp_entry.get())
            ki = float(self.ki_entry.get())
            kd = float(self.kd_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "KP, KI, and KD must be numbers.")
            return
        try:
            tune_axis(self.controller, axis, kp, ki, kd)
            messagebox.showinfo("Tuned", f"Axis {axis} tuned.")
        except Exception as e:
            messagebox.showerror("Tune Error", str(e))

    def test_connection(self):
        """Test if the controller is responding to basic commands."""
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Try various basic commands to test connection
            commands = ["TP", "MG _FW", "MG _BN", "MG _ID"]
            results = []
            
            for cmd in commands:
                try:
                    response = self.controller.send_command(cmd)
                    results.append(f"✓ {cmd}: {response}")
                except Exception as e:
                    results.append(f"✗ {cmd}: {str(e)}")
            
            messagebox.showinfo("Connection Test", "\n".join(results))
        except Exception as e:
            messagebox.showerror("Connection Test Failed", f"Error: {str(e)}")

    def set_controller_ip(self):
        """Open a dialog to set the controller's IP address."""
        new_ip = messagebox.askstring("Set IP Address", "Enter the new IP address for the controller:",
                                      initialvalue=self.ip_entry.get())
        if new_ip:
            # Update the entry field
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, new_ip)
            self.config["ip_address"] = new_ip
            save_config(self.config)
            
            # If controller is connected, try to set the IP on the controller
            if getattr(self.controller, "g", None):
                try:
                    # Set the IP address on the controller - try different formats
                    ip_commands = [
                        f"IP{new_ip}",
                        f"IP {new_ip}",
                        f"IP={new_ip}",
                        f"IP {new_ip}",
                        f"IP{new_ip.replace('.', '')}"  # Some controllers use IP192168001
                    ]
                    
                    success = False
                    for cmd in ip_commands:
                        try:
                            self.controller.send_command(cmd)
                            success = True
                            break
                        except Exception:
                            continue
                    
                    if success:
                        messagebox.showinfo("IP Set", f"Controller IP address set to: {new_ip}\nNote: You may need to reconnect after IP change.")
                    else:
                        messagebox.showwarning("IP Set", f"IP address updated in config to: {new_ip}\nWarning: Could not set IP on controller. Try reconnecting.")
                except Exception as e:
                    messagebox.showwarning("IP Set", f"IP address updated in config to: {new_ip}\nWarning: Could not set IP on controller: {str(e)}")
            else:
                messagebox.showinfo("IP Set", f"Controller IP address set to: {new_ip}\nConnect to apply the new IP.")

    def get_controller_ip(self):
        """Get the current IP address from the controller."""
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Try different commands to get IP address from controller
            ip_commands = [
                "MG _IP",
                "MG _IPADDR", 
                "MG _IPADDRESS",
                "MG IP",
                "MG IPADDR",
                "MG IPADDRESS"
            ]
            
            for cmd in ip_commands:
                try:
                    response = self.controller.send_command(cmd)
                    if response and response.strip():
                        messagebox.showinfo("Current IP", f"Controller IP address: {response.strip()}")
                        return
                except Exception:
                    continue
            
            # If no IP command worked, try to get it from connection info
            try:
                # Try to get connection info
                response = self.controller.send_command("MG _FW")
                if response:
                    messagebox.showinfo("Controller Info", f"Firmware: {response}\nIP address not available via standard commands.")
                else:
                    messagebox.showinfo("Current IP", "Could not retrieve IP address from controller.\nTry using 'SET IP' to configure it.")
            except Exception:
                messagebox.showinfo("Current IP", "Could not retrieve IP address from controller.\nTry using 'SET IP' to configure it.")
                
        except Exception as e:
            messagebox.showerror("IP Error", f"Error getting IP address: {str(e)}")

    def reset_axis_position(self):
        """Reset the position of the selected axis to 0."""
        axis = self.axis_entry.get().upper()
        
        # Check if controller is connected
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Validate axis
            if axis not in SERVO_BITS:
                messagebox.showerror("Invalid Axis", f"Axis {axis} is not valid. Use A, B, C, or D.")
                return
                
            # First, stop any current motion
            try:
                self.controller.send_command("ST")
            except Exception:
                pass
                
            # Try to move the axis to position 0
            move_commands = [
                f"PA{axis}=0",     # Position absolute
                f"PA {axis}=0",    # Position absolute with space
                f"DP{axis}=0",     # Define position
                f"DP {axis}=0",    # Define position with space
            ]
            
            success = False
            for cmd in move_commands:
                try:
                    self.controller.send_command(cmd)
                    success = True
                    break
                except Exception:
                    continue
            
            if success:
                # Reset the encoder count to zero
                encoder_reset_commands = [
                    f"RZ{axis}",      # Reset zero position
                    f"RZ {axis}",      # Reset zero position with space
                    f"ZP{axis}=0",     # Zero position
                    f"ZP {axis}=0",    # Zero position with space
                    f"DP{axis}=0",     # Define position to 0
                    f"DP {axis}=0",    # Define position to 0 with space
                    f"CN{axis}=0",     # Clear encoder count
                    f"CN {axis}=0",    # Clear encoder count with space
                    f"CE{axis}",       # Clear encoder
                    f"CE {axis}",      # Clear encoder with space
                ]
                
                encoder_reset_success = False
                for cmd in encoder_reset_commands:
                    try:
                        self.controller.send_command(cmd)
                        encoder_reset_success = True
                        break
                    except Exception:
                        continue
                
                if encoder_reset_success:
                    messagebox.showinfo("Position Reset", f"Position and encoder count of axis {axis} reset to 0.")
                else:
                    messagebox.showinfo("Position Reset", f"Position of axis {axis} reset to 0. (Encoder reset may have failed)")
                
                # Update the visual marker to center position (0) immediately
                self.visualizer.update_position(axis, 0)
                
                # Schedule additional updates to ensure the display is current
                def delayed_update():
                    self.update_position_from_controller(axis)
                    self.visualizer.update_from_controller()
                
                # Update after a short delay to allow the controller to process
                self.root.after(100, delayed_update)
            else:
                messagebox.showwarning("Position Reset", f"Could not move axis {axis} to position 0.\nTry stopping motion first.")
                
        except Exception as e:
            messagebox.showerror("Reset Error", f"Error resetting position for axis {axis}: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GalilSetupApp(root)
    root.mainloop()
