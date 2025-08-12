import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from galil_interface import GalilController
from utils import find_galil_com_ports
from diagnostics import get_controller_info, get_diagnostics
from motor_setup import tune_axis, configure_axis
from encoder_overlay import EncoderOverlay
from config_manager import load_config, save_config
from network_utils import (
    discover_galil_controllers, find_controllers_requesting_ip, assign_ip_to_controller,
    ping_controller, scan_network_range, validate_ip_address, validate_mac_address,
    test_controller_connection, get_controller_network_settings, set_controller_network_settings
)
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

class GaugeVisualizer:
    def __init__(self, canvas, controller):
        self.canvas = canvas
        self.controller = controller
        self.axis_positions = {"A": 0, "B": 0, "C": 0, "D": 0}
        self.axis_colors = {"A": "#0066cc", "B": "#00cc66", "C": "#cc6600", "D": "#cc00cc"}
        self.highlighted_colors = {"A": "#3399ff", "B": "#33ff99", "C": "#ff9933", "D": "#ff33ff"}
        self.gauge_centers = {
            "A": (150, 150),
            "B": (450, 150), 
            "C": (150, 350),
            "D": (450, 350)
        }
        self.gauge_radius = 80
        self.selected_axis = "A"
        
        # Create gauges
        self.create_gauges()
        
    def create_gauges(self):
        """Create RPM-style gauges for each axis"""
        # Clear canvas
        self.canvas.delete("all")
        
        for axis in ["A", "B", "C", "D"]:
            self.create_gauge(axis)
    
    def create_gauge(self, axis):
        """Create a single gauge for an axis"""
        center_x, center_y = self.gauge_centers[axis]
        radius = self.gauge_radius
        color = self.axis_colors[axis]
        
        # Draw gauge background (semi-circle)
        start_angle = 180
        extent = 180
        
        # Gauge background
        self.canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=start_angle, extent=extent,
            fill='#2a2a2a', outline='#404040', width=3,
            tags=f"gauge_bg_{axis}"
        )
        
        # Gauge scale marks
        for i in range(11):  # 0 to 10 marks
            angle = start_angle + (i * extent / 10)
            angle_rad = math.radians(angle)
            
            # Calculate mark position
            inner_radius = radius - 15
            outer_radius = radius - 5 if i % 2 == 0 else radius - 10
            
            x1 = center_x + inner_radius * math.cos(angle_rad)
            y1 = center_y - inner_radius * math.sin(angle_rad)
            x2 = center_x + outer_radius * math.cos(angle_rad)
            y2 = center_y - outer_radius * math.sin(angle_rad)
            
            self.canvas.create_line(x1, y1, x2, y2, fill='#ffffff', width=2,
                                  tags=f"mark_{axis}_{i}")
            
            # Add scale numbers
            if i % 2 == 0:
                text_radius = radius - 25
                text_x = center_x + text_radius * math.cos(angle_rad)
                text_y = center_y - text_radius * math.sin(angle_rad)
                self.canvas.create_text(text_x, text_y, text=str(i), 
                                      fill='#ffffff', font=("Arial", 8, "bold"),
                                      tags=f"scale_{axis}_{i}")
        
        # Center hub
        self.canvas.create_oval(
            center_x - 8, center_y - 8,
            center_x + 8, center_y + 8,
            fill=color, outline='#ffffff', width=2,
            tags=f"hub_{axis}"
        )
        
        # Needle (initially at 0)
        needle_length = radius - 20
        needle_angle = start_angle + (0 * extent / 10)  # Start at 0
        needle_rad = math.radians(needle_angle)
        needle_x = center_x + needle_length * math.cos(needle_rad)
        needle_y = center_y - needle_length * math.sin(needle_rad)
        
        self.canvas.create_line(
            center_x, center_y, needle_x, needle_y,
            fill=color, width=4, tags=f"needle_{axis}"
        )
        
        # Axis label
        self.canvas.create_text(
            center_x, center_y + radius + 20,
            text=f"Axis {axis}", fill=color, font=("Arial", 12, "bold"),
            tags=f"label_{axis}"
        )
        
        # Position value display
        self.canvas.create_text(
            center_x, center_y + radius + 40,
            text="0", fill='#ffffff', font=("Arial", 10, "bold"),
            tags=f"value_{axis}"
        )
    
    def update_position(self, axis, position):
        """Update gauge needle position for an axis"""
        center_x, center_y = self.gauge_centers[axis]
        radius = self.gauge_radius
        
        # Normalize position to 0-10 scale (adjust range as needed)
        max_position = 100000  # Adjust based on your controller's range
        normalized_pos = max(0, min(10, abs(position) / max_position * 10))
        
        # Calculate needle angle (180 to 360 degrees)
        start_angle = 180
        extent = 180
        needle_angle = start_angle + (normalized_pos * extent / 10)
        needle_rad = math.radians(needle_angle)
        
        # Update needle position
        needle_length = radius - 20
        needle_x = center_x + needle_length * math.cos(needle_rad)
        needle_y = center_y - needle_length * math.sin(needle_rad)
        
        # Update needle line
        self.canvas.coords(f"needle_{axis}", center_x, center_y, needle_x, needle_y)
        
        # Update position value
        self.canvas.itemconfig(f"value_{axis}", text=str(position))
        
        # Store position
        self.axis_positions[axis] = position
    
    def highlight_axis(self, axis):
        """Highlight the selected axis gauge"""
        self.selected_axis = axis
        
        # Update all gauge elements to show which one is selected
        for ax in ["A", "B", "C", "D"]:
            color = self.highlighted_colors[ax] if ax == axis else self.axis_colors[ax]
            
            # Update hub color
            if f"hub_{ax}" in self.canvas.find_all():
                self.canvas.itemconfig(f"hub_{ax}", fill=color)
            
            # Update needle color
            if f"needle_{ax}" in self.canvas.find_all():
                self.canvas.itemconfig(f"needle_{ax}", fill=color)
            
            # Update label color
            if f"label_{ax}" in self.canvas.find_all():
                self.canvas.itemconfig(f"label_{ax}", fill=color)
    
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
        
        # Initialize gauge visualizer
        self.visualizer = GaugeVisualizer(self.canvas, self.controller)
        
        # Start position updates
        self.root.after(200, self.update_gauge_position)

    def select_axis(self, axis):
        """Select an axis and update the UI"""
        self.selected_axis.set(axis)
        self.highlight_selected_axis(axis)
        self.current_axis_label.config(text=axis)
        
        # Update the gauge colors to highlight the selected axis
        self.highlight_gauge_axis(axis)
        
        # Update position display for the selected axis
        self.update_position_display()
    
    def highlight_selected_axis(self, selected_axis):
        """Highlight the selected axis button and unhighlight others"""
        for axis in ["A", "B", "C", "D"]:
            btn = getattr(self, f"axis_btn_{axis}")
            if axis == selected_axis:
                btn.config(bg='#0066cc', fg='#ffffff')
            else:
                btn.config(bg='#404040', fg='#ffffff')
    
    def highlight_gauge_axis(self, selected_axis):
        """Highlight the selected axis gauge with a brighter color"""
        # This will be implemented in the gauge visualizer
        if hasattr(self, 'visualizer'):
            self.visualizer.highlight_axis(selected_axis)

    def setup_dark_theme(self):
        """Setup modern black, white, blue, and grey theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern theme colors
        style.configure('Dark.TFrame', background='#1a1a1a')
        style.configure('Dark.TLabel', background='#1a1a1a', foreground='#ffffff')
        style.configure('Dark.TButton', 
                       background='#2a2a2a', 
                       foreground='#ffffff',
                       borderwidth=2,
                       relief='raised')
        style.configure('Primary.TButton',
                       background='#0066cc',
                       foreground='#ffffff',
                       borderwidth=3,
                       relief='raised')
        style.configure('Secondary.TButton',
                       background='#404040',
                       foreground='#ffffff',
                       borderwidth=3,
                       relief='raised')
        style.configure('Danger.TButton',
                       background='#cc0000',
                       foreground='#ffffff',
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
            font=("Arial", 18, "bold"),
            bg='#1a1a1a',
            fg='#ffffff'
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
            font=("Arial", 14, "bold"),
            bg='#2a2a2a',
            fg='#ffffff'
        ).pack(pady=10)
        
        # Connection status
        self.status_var = tk.StringVar(value=STATUS_DISCONNECTED)
        status_label = tk.Label(
            scrollable_frame,
            textvariable=self.status_var,
            font=("Arial", 10, "bold"),
            bg='#2a2a2a',
            fg='#ff6666'
        )
        status_label.pack(pady=5)
        
        # Connection type selection
        conn_type_frame = tk.LabelFrame(scrollable_frame, text="CONNECTION TYPE", 
                                      bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        conn_type_frame.pack(fill="x", padx=10, pady=5)
        
        self.conn_type = tk.StringVar(value="USB")
        tk.Radiobutton(conn_type_frame, text="USB", variable=self.conn_type, value="USB",
                      bg='#2a2a2a', fg='#ffffff', selectcolor='#1a1a1a',
                      font=("Arial", 9)).pack(side="left", padx=5)
        tk.Radiobutton(conn_type_frame, text="Network", variable=self.conn_type, value="Network",
                      bg='#2a2a2a', fg='#ffffff', selectcolor='#1a1a1a',
                      font=("Arial", 9)).pack(side="left", padx=5)
        
        # IP Address entry (for network connection)
        ip_frame = tk.LabelFrame(scrollable_frame, text="IP ADDRESS", 
                               bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        ip_frame.pack(fill="x", padx=10, pady=5)
        
        self.ip_entry = tk.Entry(ip_frame, width=15, bg='#1a1a1a', fg='#ffffff',
                                insertbackground='#ffffff')
        self.ip_entry.insert(0, self.config.get("ip_address", "192.168.0.100"))
        self.ip_entry.pack(pady=5)
        
        # Axis selection
        axis_frame = tk.LabelFrame(scrollable_frame, text="AXIS SELECTION", 
                                 bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        axis_frame.pack(fill="x", padx=10, pady=5)
        
        # Axis selector buttons
        axis_selector_frame = tk.Frame(axis_frame, bg='#2a2a2a')
        axis_selector_frame.pack(pady=5)
        
        self.selected_axis = tk.StringVar(value=DEFAULT_AXIS)
        
        # Create axis selector buttons
        for axis in ["A", "B", "C", "D"]:
            axis_btn = tk.Button(
                axis_selector_frame,
                text=f"Axis {axis}",
                width=8,
                command=lambda a=axis: self.select_axis(a),
                bg='#404040',
                fg='#ffffff',
                font=("Arial", 9, "bold"),
                relief='raised',
                bd=2
            )
            axis_btn.pack(side="left", padx=2)
            setattr(self, f"axis_btn_{axis}", axis_btn)
        
        # Highlight the default selected axis
        self.highlight_selected_axis(DEFAULT_AXIS)
        
        # Current axis display
        current_axis_frame = tk.Frame(axis_frame, bg='#2a2a2a')
        current_axis_frame.pack(pady=5)
        
        tk.Label(current_axis_frame, text="Current Axis:", bg='#2a2a2a', fg='#ffffff', 
                font=("Arial", 9, "bold")).pack(side="left", padx=5)
        
        self.current_axis_label = tk.Label(
            current_axis_frame,
            text=DEFAULT_AXIS,
            bg='#0066cc',
            fg='#ffffff',
            font=("Arial", 12, "bold"),
            width=3,
            relief='raised',
            bd=2
        )
        self.current_axis_label.pack(side="left", padx=5)
        
        # Current position display
        position_frame = tk.Frame(axis_frame, bg='#2a2a2a')
        position_frame.pack(pady=5)
        
        tk.Label(position_frame, text="Position:", bg='#2a2a2a', fg='#ffffff', 
                font=("Arial", 9, "bold")).pack(side="left", padx=5)
        
        self.position_label = tk.Label(
            position_frame,
            text="0",
            bg='#1a1a1a',
            fg='#ffffff',
            font=("Arial", 10, "bold"),
            width=12,
            relief='sunken',
            bd=2
        )
        self.position_label.pack(side="left", padx=5)
        
        # Speed control
        speed_frame = tk.LabelFrame(scrollable_frame, text="SPEED CONTROL", 
                                  bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        speed_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(speed_frame, text="Speed:", bg='#2a2a2a', fg='#ffffff').pack(side="left", padx=5)
        self.jog_speed_entry = tk.Entry(speed_frame, width=10, bg='#1a1a1a', fg='#ffffff',
                                      insertbackground='#ffffff')
        self.jog_speed_entry.insert(0, str(DEFAULT_JOG_SPEED))
        self.jog_speed_entry.pack(side="left", padx=5)
        
        # Motion controls
        motion_frame = tk.LabelFrame(scrollable_frame, text="MOTION CONTROLS", 
                                   bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        motion_frame.pack(fill="x", padx=10, pady=5)
        
        # Jog buttons with modern styling
        jog_frame = tk.Frame(motion_frame, bg='#2a2a2a')
        jog_frame.pack(pady=5)
        
        tk.Button(jog_frame, text="JOG +", width=8, command=self.jog_positive,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=2)
        tk.Button(jog_frame, text="JOG -", width=8, command=self.jog_negative,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=2)
        tk.Button(jog_frame, text="STOP", width=8, command=self.stop_motion,
                 bg='#cc0000', fg='#ffffff', font=("Arial", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=2)
        
        # Connection controls
        conn_frame = tk.LabelFrame(scrollable_frame, text="CONNECTION", 
                                 bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(conn_frame, text="CONNECT", command=self.connect_to_controller,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 10, "bold"),
                 relief='raised', bd=3).pack(pady=5)
        
        # Test buttons
        test_frame = tk.LabelFrame(scrollable_frame, text="DIAGNOSTICS", 
                                 bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        test_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(test_frame, text="RUN DIAGNOSTICS", command=self.run_diagnostics,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(test_frame, text="TEST CONNECTION", command=self.test_connection,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(test_frame, text="TEST COMMANDS", command=self.test_jog_commands,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(test_frame, text="TEST SERVO", command=self.test_servo_commands,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # Configuration buttons
        config_frame = tk.LabelFrame(scrollable_frame, text="CONFIGURATION", 
                                   bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        config_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(config_frame, text="CONFIGURE AXIS", command=self.configure_selected_axis,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(config_frame, text="SAVE CONFIG", command=self.save_current_config,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # Network Configuration buttons
        network_frame = tk.LabelFrame(scrollable_frame, text="NETWORK CONFIGURATION", 
                                    bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        network_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(network_frame, text="SET IP (SIMPLE)", command=self.set_controller_ip,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="SET IP (ADVANCED)", command=self.set_controller_ip_advanced,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="GET IP", command=self.get_controller_ip,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="DISCOVER CONTROLLERS", command=self.discover_network_controllers,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="FIND IP REQUESTS", command=self.find_ip_requests,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="ASSIGN IP BY MAC", command=self.assign_ip_to_controller,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="SCAN NETWORK", command=self.scan_network_for_controllers,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        tk.Button(network_frame, text="TEST CONNECTION", command=self.test_network_connection,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # Position control
        pos_frame = tk.LabelFrame(scrollable_frame, text="POSITION CONTROL", 
                                bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        pos_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(pos_frame, text="RESET POSITION", command=self.reset_axis_position,
                 bg='#404040', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=2)
        
        # PID controls
        pid_frame = tk.LabelFrame(scrollable_frame, text="PID TUNING", 
                                bg='#2a2a2a', fg='#ffffff', font=("Arial", 10, "bold"))
        pid_frame.pack(fill="x", padx=10, pady=5)
        
        for i, label in enumerate(["KP", "KI", "KD"]):
            frame = tk.Frame(pid_frame, bg='#2a2a2a')
            frame.pack(fill="x", pady=2)
            tk.Label(frame, text=f"{label}:", bg='#2a2a2a', fg='#ffffff').pack(side="left", padx=5)
            entry = tk.Entry(frame, width=8, bg='#1a1a1a', fg='#ffffff', insertbackground='#ffffff')
            entry.pack(side="right", padx=5)
            setattr(self, f"{label.lower()}_entry", entry)
        
        tk.Button(pid_frame, text="TUNE AXIS", command=self.tune_motor,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 9, "bold"),
                 relief='raised', bd=3).pack(pady=5)

    def create_visualization_panel(self, parent):
        """Create the gauge visualization panel"""
        viz_frame = tk.Frame(parent, bg='#1a1a1a')
        viz_frame.pack(side="right", fill="both", expand=True)
        
        # Gauge Visualization title
        tk.Label(
            viz_frame,
            text="AXIS POSITION GAUGES",
            font=("Arial", 14, "bold"),
            bg='#1a1a1a',
            fg='#ffffff'
        ).pack(pady=10)
        
        # Canvas for gauge visualization
        self.canvas = tk.Canvas(
            viz_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg='#0a0a0a',
            highlightthickness=2,
            highlightbackground='#0066cc'
        )
        self.canvas.pack(pady=10)

    def create_diagnostics_panel(self):
        """Create the diagnostics panel"""
        diag_frame = tk.LabelFrame(self.main_container, text="SYSTEM DIAGNOSTICS", 
                                 bg='#1a1a1a', fg='#ffffff', font=("Arial", 12, "bold"))
        diag_frame.pack(fill="x", pady=10)
        
        # Diagnostics text area
        self.diagnostics_text = tk.Text(
            diag_frame,
            height=8,
            width=80,
            wrap="word",
            bg='#0a0a0a',
            fg='#ffffff',
            insertbackground='#ffffff',
            font=("Arial", 9)
        )
        self.diagnostics_text.pack(padx=10, pady=10)
        
        # Refresh button
        tk.Button(diag_frame, text="REFRESH DIAGNOSTICS", command=self.refresh_diagnostics,
                 bg='#0066cc', fg='#ffffff', font=("Arial", 10, "bold"),
                 relief='raised', bd=3).pack(pady=5)

    def update_gauge_position(self):
        """Update gauge position display"""
        try:
            self.visualizer.update_from_controller()
            # Also update the position display
            self.update_position_display()
        except Exception:
            pass
        self.root.after(100, self.update_gauge_position)  # Increased frequency for more responsive updates
    
    def update_position_display(self):
        """Update the position display for the currently selected axis"""
        try:
            current_axis = self.selected_axis.get()
            if hasattr(self.visualizer, 'axis_positions'):
                position = self.visualizer.axis_positions.get(current_axis, 0)
                self.position_label.config(text=str(position))
        except Exception:
            pass

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
                    widget.config(fg='#00cc00')
                    break

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_var.set(STATUS_DISCONNECTED)

    def jog_positive(self):
        axis = self.selected_axis.get()
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
            
            # Update gauge display with actual position
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
        axis = self.selected_axis.get()
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
            
            # Update gauge display with actual position
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
        axis = self.selected_axis.get()
        
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
            
            # Update gauge display with actual position
            self.update_position_from_controller(axis)
            
        except Exception as e:
            messagebox.showerror("Stop Error", str(e))

    def update_position_from_controller(self, axis):
        """Update gauge display with actual position from controller"""
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
            
        axis = self.selected_axis.get()
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
            
        axis = self.selected_axis.get()
        
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
        axis = self.selected_axis.get()
        
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
        axis = self.selected_axis.get()
        
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
        new_ip = simpledialog.askstring("Set IP Address", "Enter the new IP address for the controller:",
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

    def discover_network_controllers(self):
        """Discover Galil controllers on the network."""
        try:
            addresses = discover_galil_controllers()
            
            if addresses:
                # Format the results
                result = "Available Galil Controllers:\n\n"
                for addr, info in addresses.items():
                    result += f"Address: {addr}\n"
                    if info:
                        result += f"Info: {info}\n"
                    result += "-" * 40 + "\n"
                
                messagebox.showinfo("Network Discovery", result)
            else:
                messagebox.showinfo("Network Discovery", "No Galil controllers found on the network.")
                
        except Exception as e:
            messagebox.showerror("Discovery Error", f"Error discovering controllers: {str(e)}")

    def find_ip_requests(self):
        """Find controllers requesting IP addresses."""
        try:
            ip_requests = find_controllers_requesting_ip()
            
            if ip_requests:
                # Format the results
                result = "Controllers Requesting IP Addresses:\n\n"
                for model_serial, mac in ip_requests.items():
                    result += f"Model-Serial: {model_serial}\n"
                    result += f"MAC Address: {mac}\n"
                    result += "-" * 40 + "\n"
                
                messagebox.showinfo("IP Requests", result)
            else:
                messagebox.showinfo("IP Requests", "No controllers requesting IP addresses found.")
                
        except Exception as e:
            messagebox.showerror("IP Request Error", f"Error finding IP requests: {str(e)}")

    def assign_ip_to_controller(self):
        """Assign IP address to a controller by MAC address."""
        # Get MAC address from user
        mac_address = simpledialog.askstring("Assign IP", "Enter the MAC address of the controller (e.g., 00:50:4c:20:03:0f):")
        if not mac_address:
            return
            
        # Validate MAC address
        if not validate_mac_address(mac_address):
            messagebox.showerror("Invalid MAC", "Please enter a valid MAC address (e.g., 00:50:4c:20:03:0f)")
            return
            
        # Get IP address from user
        ip_address = simpledialog.askstring("Assign IP", "Enter the IP address to assign:", initialvalue=self.ip_entry.get())
        if not ip_address:
            return
            
        # Validate IP address
        if not validate_ip_address(ip_address):
            messagebox.showerror("Invalid IP", "Please enter a valid IP address (e.g., 192.168.0.100)")
            return
            
        try:
            # Assign IP address
            if assign_ip_to_controller(ip_address, mac_address):
                messagebox.showinfo("IP Assignment", f"IP address {ip_address} assigned to controller with MAC {mac_address}")
                
                # Update the entry field
                self.ip_entry.delete(0, tk.END)
                self.ip_entry.insert(0, ip_address)
                self.config["ip_address"] = ip_address
                save_config(self.config)
            else:
                messagebox.showerror("Assignment Error", "Failed to assign IP address. Check network permissions.")
            
        except Exception as e:
            messagebox.showerror("Assignment Error", f"Error assigning IP address: {str(e)}")

    def set_controller_ip_advanced(self):
        """Advanced IP setting with multiple options."""
        # Create a custom dialog for advanced IP setting
        dialog = tk.Toplevel(self.root)
        dialog.title("Advanced IP Configuration")
        dialog.geometry("400x300")
        dialog.configure(bg='#1a1a1a')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # IP Address entry
        tk.Label(dialog, text="IP Address:", bg='#1a1a1a', fg='#00ff00', font=("Courier", 10)).pack(pady=5)
        ip_entry = tk.Entry(dialog, width=20, bg='#1a1a1a', fg='#00ff00', insertbackground='#00ff00')
        ip_entry.insert(0, self.ip_entry.get())
        ip_entry.pack(pady=5)
        
        # Subnet Mask entry
        tk.Label(dialog, text="Subnet Mask:", bg='#1a1a1a', fg='#00ff00', font=("Courier", 10)).pack(pady=5)
        mask_entry = tk.Entry(dialog, width=20, bg='#1a1a1a', fg='#00ff00', insertbackground='#00ff00')
        mask_entry.insert(0, "255.255.255.0")
        mask_entry.pack(pady=5)
        
        # Gateway entry
        tk.Label(dialog, text="Gateway:", bg='#1a1a1a', fg='#00ff00', font=("Courier", 10)).pack(pady=5)
        gateway_entry = tk.Entry(dialog, width=20, bg='#1a1a1a', fg='#00ff00', insertbackground='#00ff00')
        gateway_entry.insert(0, "192.168.0.1")
        gateway_entry.pack(pady=5)
        
        def apply_settings():
            ip = ip_entry.get().strip()
            mask = mask_entry.get().strip()
            gateway = gateway_entry.get().strip()
            
            if not ip:
                messagebox.showerror("Error", "IP address is required.")
                return
                
            try:
                # Update config
                self.config["ip_address"] = ip
                save_config(self.config)
                
                # Update main entry
                self.ip_entry.delete(0, tk.END)
                self.ip_entry.insert(0, ip)
                
                # If controller is connected, try to set network settings
                if getattr(self.controller, "g", None):
                    try:
                        # Prepare settings dictionary
                        settings = {'ip': ip}
                        if mask and mask != "255.255.255.0":
                            settings['subnet_mask'] = mask
                        if gateway and gateway != "192.168.0.1":
                            settings['gateway'] = gateway
                        
                        # Set network settings using utility function
                        results = set_controller_network_settings(self.controller, settings)
                        
                        # Check results
                        if results.get('ip', False):
                            messagebox.showinfo("Success", f"Network settings applied:\nIP: {ip}\nMask: {mask}\nGateway: {gateway}\n\nYou may need to reconnect.")
                        else:
                            messagebox.showwarning("Warning", f"Settings saved to config but could not apply to controller.\nTry reconnecting.")
                            
                    except Exception as e:
                        messagebox.showwarning("Warning", f"Settings saved to config but could not apply to controller: {str(e)}")
                else:
                    messagebox.showinfo("Success", f"Network settings saved to config:\nIP: {ip}\nMask: {mask}\nGateway: {gateway}\n\nConnect to apply settings.")
                
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving settings: {str(e)}")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg='#1a1a1a')
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Apply", command=apply_settings,
                 bg='#003300', fg='#00ff00', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg='#330000', fg='#ff0000', font=("Courier", 10, "bold"),
                 relief='raised', bd=3).pack(side="left", padx=5)

    def get_controller_ip(self):
        """Get the current IP address from the controller."""
        if not getattr(self.controller, "g", None):
            messagebox.showerror("Connection Error", "Controller not connected. Please click Connect first.")
            return
            
        try:
            # Get network settings from controller
            settings = get_controller_network_settings(self.controller)
            
            if settings:
                result = "Current Network Settings:\n\n"
                for setting, value in settings.items():
                    result += f"{setting.upper()}: {value}\n"
                messagebox.showinfo("Network Settings", result)
            else:
                messagebox.showinfo("Network Settings", "Could not retrieve network settings from controller.")
                
        except Exception as e:
            messagebox.showerror("Network Error", f"Error getting network settings: {str(e)}")

    def scan_network_for_controllers(self):
        """Scan the network for Galil controllers."""
        # Get base IP from current IP
        current_ip = self.ip_entry.get().strip()
        if not current_ip:
            messagebox.showerror("Error", "Please enter an IP address first.")
            return
            
        # Extract base IP (first three octets)
        try:
            base_ip = '.'.join(current_ip.split('.')[:3])
        except:
            messagebox.showerror("Error", "Invalid IP address format.")
            return
            
        # Ask user for scan range
        start = simpledialog.askinteger("Scan Range", f"Start IP (last octet):", initialvalue=1)
        if start is None:
            return
            
        end = simpledialog.askinteger("Scan Range", f"End IP (last octet):", initialvalue=254)
        if end is None:
            return
            
        try:
            # Scan the network
            responding_ips = scan_network_range(base_ip, start, end)
            
            if responding_ips:
                result = f"Controllers found on {base_ip}.{start}-{end}:\n\n"
                for ip in responding_ips:
                    # Test each IP for Galil controller
                    test_result = test_controller_connection(ip)
                    if test_result['connection_success']:
                        result += f"✓ {ip} - Galil Controller"
                        if test_result['model']:
                            result += f" ({test_result['model']})"
                        if test_result['firmware']:
                            result += f" - FW: {test_result['firmware']}"
                        result += "\n"
                    elif test_result['ping_success']:
                        result += f"○ {ip} - Responding (not Galil)\n"
                    else:
                        result += f"✗ {ip} - No response\n"
            else:
                result = f"No responding devices found on {base_ip}.{start}-{end}"
                
            messagebox.showinfo("Network Scan Results", result)
            
        except Exception as e:
            messagebox.showerror("Scan Error", f"Error scanning network: {str(e)}")

    def test_network_connection(self):
        """Test connection to the current IP address."""
        ip_address = self.ip_entry.get().strip()
        if not ip_address:
            messagebox.showerror("Error", "Please enter an IP address first.")
            return
            
        try:
            # Test the connection
            result = test_controller_connection(ip_address)
            
            # Format the results
            status = "Connection Test Results:\n\n"
            status += f"IP Address: {result['ip']}\n"
            status += f"Ping Test: {'✓ PASS' if result['ping_success'] else '✗ FAIL'}\n"
            status += f"Connection Test: {'✓ PASS' if result['connection_success'] else '✗ FAIL'}\n"
            
            if result['model']:
                status += f"Controller Model: {result['model']}\n"
            if result['firmware']:
                status += f"Firmware: {result['firmware']}\n"
            if result['error']:
                status += f"Error: {result['error']}\n"
                
            messagebox.showinfo("Connection Test", status)
            
        except Exception as e:
            messagebox.showerror("Test Error", f"Error testing connection: {str(e)}")

    def reset_axis_position(self):
        """Reset the position of the selected axis to 0."""
        axis = self.selected_axis.get()
        
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
                
                # Update the gauge needle to center position (0) immediately
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
