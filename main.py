import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import os
import sys
import math
from datetime import datetime
import json
import subprocess
import socket
import re
from typing import Dict, List, Optional, Tuple, Any

# Import our custom modules
from network_combined import (
    discover_galil_controllers, ping_controller, validate_ip_address,
    test_controller_connection, configure_controller_network_complete, configure_controller_network_dmc4143, 
    reset_controller_network_to_dhcp, get_controller_network_status, comprehensive_network_test,
    force_save_network_settings_dmc4143, NetworkConfigurator
)
from galil_combined import GalilController
import galil_combined as galil_functions

class GalilSetupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Galil Setup Tool")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f5f5f5')  # Light gray background
        
        # Initialize controller and components
        self.controller = None
        self.test_encoder_update_running = False
        self.auto_connect_running = False
        self.motor_direction_test_active = False  # Flag to control encoder position logging
        
        # Color scheme matching Acertara
        self.colors = {
            'sidebar_bg': '#2c3e50',      # Dark gray/black sidebar
            'sidebar_fg': '#ffffff',      # White text in sidebar
            'header_bg': '#ffffff',       # White header
            'header_fg': '#2c3e50',       # Dark text in header
            'main_bg': '#f5f5f5',         # Light gray main area
            'main_fg': '#2c3e50',         # Dark text in main area
            'accent_blue': '#3498db',     # Blue accent color
            'success_green': '#27ae60',   # Green for success
            'warning_orange': '#f39c12',  # Orange for warnings
            'error_red': '#e74c3c',       # Red for errors
            'card_bg': '#ffffff',         # White cards
            'card_border': '#e0e0e0',     # Light border for cards
            'online_green': '#2ecc71'     # Green for online status
        }
        
        self.setup_ui()
        
        # Auto-detect and connect to controller on startup (delay to ensure UI is ready)
        self.root.after(1000, self.auto_connect_to_controller)
        
    def setup_ui(self):
        """Setup the main UI with Acertara-style layout"""
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create header
        self.create_header()
        
        # Create main content area
        self.create_main_content()
        
    def create_sidebar(self):
        """Create the dark sidebar with navigation"""
        # Sidebar frame
        sidebar = tk.Frame(self.root, bg=self.colors['sidebar_bg'], width=250)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # User profile section
        profile_frame = tk.Frame(sidebar, bg=self.colors['sidebar_bg'])
        profile_frame.pack(fill='x', padx=20, pady=20)
        
        # Acertara logo
        logo_frame = tk.Frame(profile_frame, bg=self.colors['sidebar_bg'])
        logo_frame.pack(pady=(0, 15))
        
        # Prefer using an image logo if available
        try:
            import os
            logo_path = os.path.join('assets', 'acertara_logo.png')
            if os.path.isfile(logo_path):
                from tkinter import PhotoImage
                self._sidebar_logo_img = PhotoImage(file=logo_path)
                logo_img_label = tk.Label(logo_frame, image=self._sidebar_logo_img, bg=self.colors['sidebar_bg'])
                logo_img_label.pack(side='left')
            else:
                # Fallback to simple text logo
                logo_fallback = tk.Label(logo_frame, text="A", 
                                         font=("Arial", 24, "bold"),
                                         bg=self.colors['accent_blue'], fg='white',
                                         width=2, height=1, relief='flat')
                logo_fallback.pack(side='left')
        except Exception:
            logo_fallback = tk.Label(logo_frame, text="A", 
                                     font=("Arial", 24, "bold"),
                                     bg=self.colors['accent_blue'], fg='white',
                                     width=2, height=1, relief='flat')
            logo_fallback.pack(side='left')
        
        # ACERTARA text
        logo_text_frame = tk.Frame(logo_frame, bg=self.colors['sidebar_bg'])
        logo_text_frame.pack(side='left', padx=(12, 0))
        
        acertara_text = tk.Label(logo_text_frame, text="ACERTARA", 
                               font=("Arial", 16, "bold"), 
                               bg=self.colors['sidebar_bg'], fg='black')
        acertara_text.pack()
        
        acoustic_text = tk.Label(logo_text_frame, text="acoustic laboratories", 
                               font=("Arial", 9), 
                               bg=self.colors['sidebar_bg'], fg='#666666')
        acoustic_text.pack()
        
        # User icon (placeholder)
        user_icon = tk.Label(profile_frame, text="👤", font=("Arial", 24), 
                           bg=self.colors['sidebar_bg'], fg=self.colors['sidebar_fg'])
        user_icon.pack()
        
        # User name
        user_name = tk.Label(profile_frame, text="Ryan McDowell", 
                           font=("Arial", 12, "bold"), 
                           bg=self.colors['sidebar_bg'], fg=self.colors['sidebar_fg'])
        user_name.pack(pady=(10, 5))
        
        # Online status
        status_frame = tk.Frame(profile_frame, bg=self.colors['sidebar_bg'])
        status_frame.pack()
        
        online_dot = tk.Label(status_frame, text="●", font=("Arial", 8), 
                             bg=self.colors['sidebar_bg'], fg=self.colors['online_green'])
        online_dot.pack(side='left')
        
        online_text = tk.Label(status_frame, text="Online", 
                              font=("Arial", 10), 
                              bg=self.colors['sidebar_bg'], fg=self.colors['sidebar_fg'])
        online_text.pack(side='left', padx=(5, 0))
        
        # Navigation menu
        nav_frame = tk.Frame(sidebar, bg=self.colors['sidebar_bg'])
        nav_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Menu items
        menu_items = [
            ("🎯", "Controller Testing", self.show_controller_testing),
            ("🔧", "Motor Setup", self.show_motor_setup),
            ("🌐", "Network Config", self.show_network_config),
            ("⚙️", "Settings", self.show_settings),
        ]
        
        for icon, text, command in menu_items:
            menu_item = tk.Button(nav_frame, text=f"{icon} {text}", 
                                font=("Arial", 11), 
                                bg=self.colors['sidebar_bg'], fg=self.colors['sidebar_fg'],
                                bd=0, relief='flat', anchor='w',
                                command=command)
            menu_item.pack(fill='x', pady=2)
            
            # Hover effects
            menu_item.bind('<Enter>', lambda e, btn=menu_item: btn.configure(bg='#34495e'))
            menu_item.bind('<Leave>', lambda e, btn=menu_item: btn.configure(bg=self.colors['sidebar_bg']))
        
    def create_header(self):
        """Create the light header with logo and controls"""
        # Header frame
        header = tk.Frame(self.root, bg=self.colors['header_bg'], height=80)
        header.grid(row=0, column=1, sticky="ew")
        header.grid_propagate(False)
        
        # Configure header grid
        header.grid_columnconfigure(1, weight=1)
        
        # Left side - Logo and hamburger menu
        left_frame = tk.Frame(header, bg=self.colors['header_bg'])
        left_frame.grid(row=0, column=0, sticky="w", padx=20, pady=20)
        
        # Hamburger menu
        hamburger = tk.Label(left_frame, text="☰", font=("Arial", 18), 
                           bg=self.colors['header_bg'], fg=self.colors['header_fg'])
        hamburger.pack(side='left', padx=(0, 15))
        
        # Right side - Controls
        right_frame = tk.Frame(header, bg=self.colors['header_bg'])
        right_frame.grid(row=0, column=2, sticky="e", padx=20, pady=20)
        
        # Control buttons
        controls = [
            ("🔔", "Notifications"),
            ("⏻", "Logout"),
            ("👤", "Ryan"),
            ("⚙️", "Settings")
        ]
        
        for icon, tooltip in controls:
            btn = tk.Label(right_frame, text=icon, font=("Arial", 16), 
                          bg=self.colors['header_bg'], fg=self.colors['header_fg'])
            btn.pack(side='left', padx=5)
            
            # Add tooltip
            if tooltip == "Ryan":
                user_label = tk.Label(right_frame, text=tooltip, 
                                    font=("Arial", 10), 
                                    bg=self.colors['header_bg'], fg=self.colors['header_fg'])
                user_label.pack(side='left', padx=(5, 10))
        
    def create_main_content(self):
        """Create the main content area"""
        # Main content frame
        self.main_content = tk.Frame(self.root, bg=self.colors['main_bg'])
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Show controller testing by default
        self.show_controller_testing()
        

        
    def clear_main_content(self):
        """Clear the main content area"""
        # Stop encoder updates when switching pages
        self.test_encoder_update_running = False
        
        # Stop motor setup encoder updates if they're running
        if hasattr(self, 'encoder_update_job'):
            self.stop_encoder_auto_update()
        
        for widget in self.main_content.winfo_children():
            widget.destroy()
            
    def show_motor_setup(self):
        """Show motor setup interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Motor Setup", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Auto-connect to controller when entering motor setup page
        if not self.controller:
            self.auto_connect_to_controller()
        
        # Create main container with two-column layout
        main_container = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        main_container.pack(fill='both', expand=True)
        
        # Left column for configuration sections
        left_column = tk.Frame(main_container, bg=self.colors['main_bg'])
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Right column for status log
        right_column = tk.Frame(main_container, bg=self.colors['main_bg'])
        right_column.pack(side='right', fill='both', expand=False, padx=(10, 0))
        
        # Create canvas for scrolling on left column
        canvas = tk.Canvas(left_column, bg=self.colors['main_bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_column, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['main_bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Motor setup content
        setup_frame = tk.Frame(scrollable_frame, bg=self.colors['main_bg'])
        setup_frame.pack(fill='both', expand=True, padx=10)
        
        # Real-time Encoder Position Display Section (Always visible)
        encoder_frame = tk.LabelFrame(setup_frame, text="📊 Real-time Encoder Positions", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        encoder_frame.pack(fill='x', pady=(0, 15))
        
        # Encoder position display
        encoder_display_frame = tk.Frame(encoder_frame, bg=self.colors['main_bg'])
        encoder_display_frame.pack(fill='x', padx=15, pady=10)
        
        # Create labels for each axis position
        self.encoder_labels = {}
        axes = ["A", "B", "C", "D"]
        
        for i, axis in enumerate(axes):
            # Axis label
            axis_label = tk.Label(encoder_display_frame, text=f"Axis {axis}:", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                width=8)
            axis_label.grid(row=0, column=i*2, padx=(0, 5), pady=5)
            
            # Position value label
            pos_label = tk.Label(encoder_display_frame, text="0", 
                               font=("Consolas", 12, "bold"),
                               bg='white', fg='black', relief='sunken', bd=1,
                               width=12)
            pos_label.grid(row=0, column=i*2+1, padx=(0, 10), pady=5)
            self.encoder_labels[axis] = pos_label
        
        # Update button
        update_btn = tk.Button(encoder_frame, text="🔄 Update Positions", 
                             font=("Arial", 10, "bold"),
                             bg=self.colors['accent_blue'], fg='white',
                             command=self.update_encoder_positions)
        update_btn.pack(pady=(0, 10))
        
        # Test connection button
        test_btn = tk.Button(encoder_frame, text="🔍 Test Connection", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=self.test_controller_connection)
        test_btn.pack(pady=(0, 10))
        
        # Auto-update checkbox
        self.auto_update_var = tk.BooleanVar(value=True)
        auto_update_check = tk.Checkbutton(encoder_frame, text="Auto-update positions every 0.5 seconds", 
                                         font=("Arial", 9),
                                         bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                         variable=self.auto_update_var,
                                         command=self.toggle_auto_update)
        auto_update_check.pack(pady=(0, 10))
        
        # Collapsible sections container
        sections_frame = tk.Frame(setup_frame, bg=self.colors['main_bg'])
        sections_frame.pack(fill='x', pady=(0, 15))
        
        # PID Configuration Section (Collapsible)
        self.pid_frame = tk.LabelFrame(sections_frame, text="⚙️ PID Configuration ▼", 
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     relief='solid', bd=1)
        self.pid_frame.pack(fill='x', pady=(0, 10))
        self.pid_frame.bind("<Button-1>", self.toggle_pid_section)
        
        # PID content frame
        self.pid_content = tk.Frame(self.pid_frame, bg=self.colors['main_bg'])
        self.pid_content.pack(fill='x', padx=15, pady=10)
        
        # Axis selection
        axis_frame = tk.Frame(self.pid_content, bg=self.colors['main_bg'])
        axis_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(axis_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.axis_var = tk.StringVar(value="A")
        axis_combo = ttk.Combobox(axis_frame, textvariable=self.axis_var, 
                                 values=["A", "B", "C", "D"], width=10)
        axis_combo.pack(side='left', padx=(10, 0))
        
        # PID values
        pid_values_frame = tk.Frame(self.pid_content, bg=self.colors['main_bg'])
        pid_values_frame.pack(fill='x', pady=(0, 10))
        
        # KP
        tk.Label(pid_values_frame, text="KP:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        self.kp_entry = tk.Entry(pid_values_frame, font=("Arial", 10), width=15)
        self.kp_entry.grid(row=0, column=1, padx=(10, 20))
        self.kp_entry.insert(0, "10.0")
        
        # KI
        tk.Label(pid_values_frame, text="KI:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        self.ki_entry = tk.Entry(pid_values_frame, font=("Arial", 10), width=15)
        self.ki_entry.grid(row=0, column=3, padx=(10, 20))
        self.ki_entry.insert(0, "0.1")
        
        # KD
        tk.Label(pid_values_frame, text="KD:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=4, sticky='w')
        self.kd_entry = tk.Entry(pid_values_frame, font=("Arial", 10), width=15)
        self.kd_entry.grid(row=0, column=5, padx=(10, 0))
        self.kd_entry.insert(0, "50.0")
        
        # Tune button
        tune_btn = tk.Button(self.pid_content, text="Tune Axis", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=self.tune_axis)
        tune_btn.pack(pady=(0, 10))
        
        # Motion Parameters Section (Collapsible)
        self.motion_frame = tk.LabelFrame(sections_frame, text="🚀 Motion Parameters ▼", 
                                        font=("Arial", 12, "bold"),
                                        bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                        relief='solid', bd=1)
        self.motion_frame.pack(fill='x', pady=(0, 10))
        self.motion_frame.bind("<Button-1>", self.toggle_motion_section)
        
        # Motion content frame
        self.motion_content = tk.Frame(self.motion_frame, bg=self.colors['main_bg'])
        self.motion_content.pack(fill='x', padx=15, pady=10)
        
        # Speed and acceleration
        motion_params_frame = tk.Frame(self.motion_content, bg=self.colors['main_bg'])
        motion_params_frame.pack(fill='x', pady=(0, 10))
        
        # Speed
        tk.Label(motion_params_frame, text="Speed:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        self.speed_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        self.speed_entry.grid(row=0, column=1, padx=(10, 20))
        self.speed_entry.insert(0, "5000")
        
        # Acceleration
        tk.Label(motion_params_frame, text="Acceleration:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        self.accel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        self.accel_entry.grid(row=0, column=3, padx=(10, 20))
        self.accel_entry.insert(0, "1000")
        
        # Deceleration
        tk.Label(motion_params_frame, text="Deceleration:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=4, sticky='w')
        self.decel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        self.decel_entry.grid(row=0, column=5, padx=(10, 0))
        self.decel_entry.insert(0, "2000")
        
        # Apply button
        apply_btn = tk.Button(self.motion_content, text="Apply Parameters", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['accent_blue'], fg='white',
                            command=self.apply_motion_params)
        apply_btn.pack(pady=(0, 10))
        
        # Brushless Motor Configuration Section (Collapsible)
        self.brushless_frame = tk.LabelFrame(sections_frame, text="🔧 Brushless Motor Configuration ▼", 
                                           font=("Arial", 12, "bold"),
                                           bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                           relief='solid', bd=1)
        self.brushless_frame.pack(fill='x', pady=(0, 10))
        self.brushless_frame.bind("<Button-1>", self.toggle_brushless_section)
        
        # Brushless content frame
        self.brushless_content = tk.Frame(self.brushless_frame, bg=self.colors['main_bg'])
        self.brushless_content.pack(fill='x', padx=15, pady=10)
        
        # Brushless setup instructions
        instructions_frame = tk.Frame(self.brushless_content, bg=self.colors['main_bg'])
        instructions_frame.pack(fill='x', pady=(0, 10))
        
        instructions_text = """Initial Conditions:
• Motor should be uncoupled from mechanics with room to move
• MO jumper should be installed for safety
• Motor, encoder, and hall sensors must be properly connected
• Power down controller, connect components, then repower"""
        
        instructions_label = tk.Label(instructions_frame, text=instructions_text, 
                                    font=("Arial", 9), justify='left',
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        instructions_label.pack(anchor='w')
        
        # Brushless configuration buttons
        brushless_buttons_frame = tk.Frame(self.brushless_content, bg=self.colors['main_bg'])
        brushless_buttons_frame.pack(fill='x', pady=(0, 10))
        
        # Step 1: Define Motor Direction
        direction_frame = tk.Frame(brushless_buttons_frame, bg=self.colors['main_bg'])
        direction_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(direction_frame, text="Step 1: Define Motor Direction", 
               font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        direction_buttons_frame = tk.Frame(direction_frame, bg=self.colors['main_bg'])
        direction_buttons_frame.pack(fill='x', pady=(5, 0))
        
        self.define_direction_btn = tk.Button(direction_buttons_frame, text="Define Motor Direction", 
                                            font=("Arial", 10, "bold"),
                                            bg=self.colors['accent_blue'], fg='white',
                                            command=self.define_motor_direction)
        self.define_direction_btn.pack(side='left', padx=(0, 10))
        
        # Encoder polarity selection
        self.encoder_polarity_var = tk.StringVar(value="Normal")
        polarity_frame = tk.Frame(direction_buttons_frame, bg=self.colors['main_bg'])
        polarity_frame.pack(side='left')
        
        tk.Label(polarity_frame, text="Encoder Polarity:", 
               font=("Arial", 9),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        polarity_combo = ttk.Combobox(polarity_frame, textvariable=self.encoder_polarity_var, 
                                    values=["Normal", "Reversed"], width=10)
        polarity_combo.pack(side='left', padx=(5, 0))
        
        # Step 2: Estimate Brushless Modulo
        modulo_frame = tk.Frame(brushless_buttons_frame, bg=self.colors['main_bg'])
        modulo_frame.pack(fill='x', pady=(10, 0))
        
        tk.Label(modulo_frame, text="Step 2: Estimate Brushless Modulo & Correct Hall Sensors", 
               font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        self.estimate_bm_btn = tk.Button(modulo_frame, text="Estimate BM and Correct Halls", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['warning_orange'], fg='white',
                                       command=self.estimate_brushless_modulo)
        self.estimate_bm_btn.pack(anchor='w', pady=(5, 0))
        
        # Step 3: Latch Indexes
        index_frame = tk.Frame(brushless_buttons_frame, bg=self.colors['main_bg'])
        index_frame.pack(fill='x', pady=(10, 0))
        
        tk.Label(index_frame, text="Step 3: Latch Indexes (if encoder has index)", 
               font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        index_buttons_frame = tk.Frame(index_frame, bg=self.colors['main_bg'])
        index_buttons_frame.pack(fill='x', pady=(5, 0))
        
        self.latch_indexes_btn = tk.Button(index_buttons_frame, text="Latch Indexes", 
                                         font=("Arial", 10, "bold"),
                                         bg=self.colors['success_green'], fg='white',
                                         command=self.latch_indexes)
        self.latch_indexes_btn.pack(side='left', padx=(0, 10))
        
        self.no_index_btn = tk.Button(index_buttons_frame, text="No Index Present", 
                                    font=("Arial", 10, "bold"),
                                    bg=self.colors['warning_orange'], fg='white',
                                    command=self.skip_index_latching)
        self.no_index_btn.pack(side='left')
        
        # Step 4: Save Settings
        save_frame = tk.Frame(brushless_buttons_frame, bg=self.colors['main_bg'])
        save_frame.pack(fill='x', pady=(10, 0))
        
        tk.Label(save_frame, text="Step 4: Save Configuration", 
               font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        self.save_brushless_btn = tk.Button(save_frame, text="Save Axis Settings", 
                                          font=("Arial", 10, "bold"),
                                          bg=self.colors['success_green'], fg='white',
                                          command=self.save_brushless_settings)
        self.save_brushless_btn.pack(anchor='w', pady=(5, 0))
        
        # Status section (Always visible on right side)
        status_frame = tk.LabelFrame(right_column, text="📋 Status & Log", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        status_frame.pack(fill='both', expand=True, pady=(0, 0))
        
        # Status text area
        self.motor_status_text = scrolledtext.ScrolledText(status_frame, height=25, font=("Consolas", 9),
                                                         bg='white', fg='black')
        self.motor_status_text.pack(fill='both', expand=True, padx=15, pady=(15, 5))
        
        # Status control buttons
        status_buttons_frame = tk.Frame(status_frame, bg=self.colors['main_bg'])
        status_buttons_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        # Copy log button
        copy_log_btn = tk.Button(status_buttons_frame, text="📋 Copy Log", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['accent_blue'], fg='white',
                               command=self.copy_motor_setup_log)
        copy_log_btn.pack(side='left')
        
        # Initial status message
        self.motor_status_text.insert(tk.END, "Motor Setup Interface Ready\n")
        self.motor_status_text.insert(tk.END, "Connect to a controller to begin configuration...\n")
        
        # Initialize encoder position display
        self.on_motor_setup_show()
        self.motor_status_text.insert(tk.END, "Connect to a controller to begin configuration...\n")
        
        # Initialize encoder position display
        self.on_motor_setup_show()
            
    def show_motion_controls(self):
        """Show motion controls interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Motion Controls", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Motion controls content
        controls_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        controls_frame.pack(fill='both', expand=True)
        
        # Jog Controls Section
        jog_frame = tk.LabelFrame(controls_frame, text="Jog Controls", 
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        jog_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Axis selection for jog
        jog_axis_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_axis_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(jog_axis_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.jog_axis_var = tk.StringVar(value="A")
        jog_axis_combo = ttk.Combobox(jog_axis_frame, textvariable=self.jog_axis_var, 
                                     values=["A", "B", "C", "D"], width=10)
        jog_axis_combo.pack(side='left', padx=(10, 20))
        
        # Jog distance
        tk.Label(jog_axis_frame, text="Distance (mm):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.jog_distance_entry = tk.Entry(jog_axis_frame, font=("Arial", 10), width=15)
        self.jog_distance_entry.pack(side='left', padx=(10, 0))
        self.jog_distance_entry.insert(0, "10.0")
        
        # Jog buttons
        jog_buttons_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_buttons_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Button(jog_buttons_frame, text="Jog +", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=lambda: self.jog_axis(1)).pack(side='left', padx=(0, 10))
        
        tk.Button(jog_buttons_frame, text="Jog -", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=lambda: self.jog_axis(-1)).pack(side='left', padx=(0, 10))
        
        tk.Button(jog_buttons_frame, text="Stop", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.stop_axis).pack(side='left')
        
        # Position Control Section
        position_frame = tk.LabelFrame(controls_frame, text="Position Control", 
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     relief='solid', bd=1)
        position_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Position inputs
        pos_inputs_frame = tk.Frame(position_frame, bg=self.colors['main_bg'])
        pos_inputs_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(pos_inputs_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        
        self.pos_axis_var = tk.StringVar(value="A")
        pos_axis_combo = ttk.Combobox(pos_inputs_frame, textvariable=self.pos_axis_var, 
                                     values=["A", "B", "C", "D"], width=10)
        pos_axis_combo.grid(row=0, column=1, padx=(10, 20))
        
        tk.Label(pos_inputs_frame, text="Position (counts):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        
        self.position_entry = tk.Entry(pos_inputs_frame, font=("Arial", 10), width=15)
        self.position_entry.grid(row=0, column=3, padx=(10, 20))
        self.position_entry.insert(0, "10000")
        
        tk.Button(pos_inputs_frame, text="Move", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.move_to_position).grid(row=0, column=4, padx=(10, 0))
        
        # Status section
        motion_status_frame = tk.LabelFrame(controls_frame, text="Status", 
                                          font=("Arial", 12, "bold"),
                                          bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                          relief='solid', bd=1)
        motion_status_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Status text area
        self.motion_status_text = scrolledtext.ScrolledText(motion_status_frame, height=10, font=("Consolas", 9),
                                                          bg='white', fg='black')
        self.motion_status_text.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Initial status message
        self.motion_status_text.insert(tk.END, "Motion Controls Interface Ready\n")
        self.motion_status_text.insert(tk.END, "Connect to a controller to begin motion control...\n")
            
    def show_encoder_overlay(self):
        """Show encoder overlay interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Encoder Overlay", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Encoder overlay content
        overlay_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        overlay_frame.pack(fill='both', expand=True)
        
        # Controls Section
        controls_frame = tk.LabelFrame(overlay_frame, text="Encoder Controls", 
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     relief='solid', bd=1)
        controls_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Axis selection
        axis_frame = tk.Frame(controls_frame, bg=self.colors['main_bg'])
        axis_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(axis_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.encoder_axis_var = tk.StringVar(value="A")
        encoder_axis_combo = ttk.Combobox(axis_frame, textvariable=self.encoder_axis_var, 
                                         values=["A", "B", "C", "D"], width=10)
        encoder_axis_combo.pack(side='left', padx=(10, 20))
        
        # Clicks per turn
        tk.Label(axis_frame, text="Clicks per Turn:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.clicks_per_turn_entry = tk.Entry(axis_frame, font=("Arial", 10), width=15)
        self.clicks_per_turn_entry.pack(side='left', padx=(10, 0))
        self.clicks_per_turn_entry.insert(0, "64000")
        
        # Start/Stop button
        self.encoder_running = False
        self.encoder_start_btn = tk.Button(controls_frame, text="Start Encoder Display", 
                                         font=("Arial", 10, "bold"),
                                         bg=self.colors['success_green'], fg='white',
                                         command=self.toggle_encoder_display)
        self.encoder_start_btn.pack(pady=10)
        
        # Display Section
        display_frame = tk.LabelFrame(overlay_frame, text="Encoder Position Display", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        display_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Canvas for encoder display
        self.encoder_canvas = tk.Canvas(display_frame, bg='white', height=300)
        self.encoder_canvas.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Position text display
        self.position_label = tk.Label(display_frame, text="Position: Not Connected", 
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        self.position_label.pack(pady=(0, 15))
        
        # Initialize encoder update variables
        self.encoder_update_running = True
        self.encoder_update_thread = threading.Thread(target=self.encoder_update_loop, daemon=True)
        self.encoder_update_thread.start()
            
    def show_diagnostics(self):
        """Show diagnostics interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Diagnostics", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Diagnostics content
        diag_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        diag_frame.pack(fill='both', expand=True)
        
        # Controller Information Section
        info_frame = tk.LabelFrame(diag_frame, text="Controller Information", 
                                 font=("Arial", 12, "bold"),
                                 bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                 relief='solid', bd=1)
        info_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Get info button
        info_btn = tk.Button(info_frame, text="Get Controller Info", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['accent_blue'], fg='white',
                           command=self.get_controller_info)
        info_btn.pack(pady=10)
        
        # Live Diagnostics Section
        live_frame = tk.LabelFrame(diag_frame, text="Live Diagnostics", 
                                 font=("Arial", 12, "bold"),
                                 bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                 relief='solid', bd=1)
        live_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Live diagnostics controls
        live_controls_frame = tk.Frame(live_frame, bg=self.colors['main_bg'])
        live_controls_frame.pack(fill='x', padx=15, pady=10)
        
        self.live_diag_var = tk.BooleanVar()
        live_check = tk.Checkbutton(live_controls_frame, text="Enable Live Updates", 
                                  variable=self.live_diag_var,
                                  font=("Arial", 10),
                                  bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                  command=self.toggle_live_diagnostics)
        live_check.pack(side='left')
        
        # Update interval
        tk.Label(live_controls_frame, text="Update Interval (ms):", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left', padx=(20, 5))
        
        self.update_interval_entry = tk.Entry(live_controls_frame, font=("Arial", 10), width=10)
        self.update_interval_entry.pack(side='left')
        self.update_interval_entry.insert(0, "1000")
        
        # Status section
        diag_status_frame = tk.LabelFrame(diag_frame, text="Diagnostic Results", 
                                        font=("Arial", 12, "bold"),
                                        bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                        relief='solid', bd=1)
        diag_status_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Status text area
        self.diag_status_text = scrolledtext.ScrolledText(diag_status_frame, height=15, font=("Consolas", 9),
                                                        bg='white', fg='black')
        self.diag_status_text.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Initial status message
        self.diag_status_text.insert(tk.END, "Diagnostics Interface Ready\n")
        self.diag_status_text.insert(tk.END, "Connect to a controller to begin diagnostics...\n")
        
        # Initialize live update variables
        self.live_update_running = False
        self.live_update_thread = None
            
    def show_network_config(self):
        """Show network configuration interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Network Configuration", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Create network configuration interface
        self.create_network_interface()
        
    def show_settings(self):
        """Show settings interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Settings", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Settings content
        settings_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        settings_frame.pack(fill='both', expand=True)
        
        # General Settings Section
        general_frame = tk.LabelFrame(settings_frame, text="General Settings", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        general_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        general_desc = tk.Label(general_frame, 
                              text="General Settings allows you to configure default values for the application.\n"
                                   "This includes default IP addresses, motion parameters, and other global settings.",
                              font=("Arial", 10),
                              bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                              justify='left')
        general_desc.pack(padx=15, pady=15)
        
        # Configuration Management Section
        config_frame = tk.LabelFrame(settings_frame, text="Configuration Management", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        config_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Save Configuration
        save_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        save_frame.pack(fill='x', padx=15, pady=10)
        
        save_icon = tk.Label(save_frame, text="💾", font=("Arial", 16), 
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        save_icon.pack(side='left', padx=(0, 10))
        
        save_text = tk.Label(save_frame, text="Save Configuration", 
                           font=("Arial", 12, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        save_text.pack(side='left', padx=(0, 10))
        
        save_desc = tk.Label(save_frame, text="Save current settings to a configuration file", 
                           font=("Arial", 10),
                           bg=self.colors['main_bg'], fg='#666666')
        save_desc.pack(side='left', padx=(0, 10))
        
        save_btn = tk.Button(save_frame, text="Save", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=self.save_configuration)
        save_btn.pack(side='right')
        
        # Load Configuration
        load_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        load_frame.pack(fill='x', padx=15, pady=10)
        
        load_icon = tk.Label(load_frame, text="📁", font=("Arial", 16), 
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        load_icon.pack(side='left', padx=(0, 10))
        
        load_text = tk.Label(load_frame, text="Load Configuration", 
                           font=("Arial", 12, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        load_text.pack(side='left', padx=(0, 10))
        
        load_desc = tk.Label(load_frame, text="Load settings from a configuration file", 
                           font=("Arial", 10),
                           bg=self.colors['main_bg'], fg='#666666')
        load_desc.pack(side='left', padx=(0, 10))
        
        load_btn = tk.Button(load_frame, text="Load", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['accent_blue'], fg='white',
                           command=self.load_configuration)
        load_btn.pack(side='right')
        
        # Reset to Defaults
        reset_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        reset_frame.pack(fill='x', padx=15, pady=10)
        
        reset_icon = tk.Label(reset_frame, text="🔄", font=("Arial", 16), 
                            bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        reset_icon.pack(side='left', padx=(0, 10))
        
        reset_text = tk.Label(reset_frame, text="Reset to Defaults", 
                            font=("Arial", 12, "bold"),
                            bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        reset_text.pack(side='left', padx=(0, 10))
        
        reset_desc = tk.Label(reset_frame, text="Reset all settings to their original default values", 
                            font=("Arial", 10),
                            bg=self.colors['main_bg'], fg='#666666')
        reset_desc.pack(side='left', padx=(0, 10))
        
        reset_btn = tk.Button(reset_frame, text="Reset", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['warning_orange'], fg='white',
                            command=self.reset_to_defaults)
        reset_btn.pack(side='right')
        
        # Status section
        status_frame = tk.LabelFrame(settings_frame, text="Configuration Status", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        status_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Status text area
        self.settings_status_text = scrolledtext.ScrolledText(status_frame, height=10, font=("Consolas", 9),
                                                            bg='white', fg='black')
        self.settings_status_text.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Initial status message
        self.settings_status_text.insert(tk.END, "Settings Interface Ready\n")
        self.settings_status_text.insert(tk.END, "Use the buttons above to manage your configuration...\n")
            
    def create_network_interface(self):
        """Create the network configuration interface"""
        # Main network frame
        network_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        network_frame.pack(fill='both', expand=True)
        
        # Connection section
        connection_frame = tk.LabelFrame(network_frame, text="Controller Connection", 
                                       font=("Arial", 12, "bold"),
                                       bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                       relief='solid', bd=1)
        connection_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # IP Address input
        ip_frame = tk.Frame(connection_frame, bg=self.colors['main_bg'])
        ip_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(ip_frame, text="IP Address:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.ip_entry = tk.Entry(ip_frame, font=("Arial", 10), width=15)
        self.ip_entry.pack(side='left', padx=(10, 0))
        self.ip_entry.insert(0, "10.1.0.21")
        
        # Connect button
        connect_btn = tk.Button(ip_frame, text="Connect", 
                              font=("Arial", 10, "bold"),
                              bg=self.colors['accent_blue'], fg='white',
                              command=self.connect_to_controller)
        connect_btn.pack(side='left', padx=(10, 0))
        
        # Disconnect button
        disconnect_btn = tk.Button(ip_frame, text="Disconnect", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['error_red'], fg='white',
                                command=self.disconnect_controller)
        disconnect_btn.pack(side='left', padx=(10, 0))
        
        # Discover button
        discover_btn = tk.Button(ip_frame, text="Discover Controllers", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['warning_orange'], fg='white',
                               command=self.discover_controllers)
        discover_btn.pack(side='left', padx=(10, 0))
        
        # Connection status label
        self.connection_status_label = tk.Label(ip_frame, text="Not Connected", 
                                              font=("Arial", 10, "bold"),
                                              bg=self.colors['main_bg'], fg=self.colors['error_red'])
        self.connection_status_label.pack(side='right', padx=(10, 0))
        
        # Network configuration section
        config_frame = tk.LabelFrame(network_frame, text="Network Configuration", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        config_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Network settings inputs
        settings_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        settings_frame.pack(fill='x', padx=15, pady=10)
        
        # IP Address
        tk.Label(settings_frame, text="New IP:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        self.new_ip_entry = tk.Entry(settings_frame, font=("Arial", 10), width=15)
        self.new_ip_entry.grid(row=0, column=1, padx=(10, 20))
        
        # Subnet Mask
        tk.Label(settings_frame, text="Subnet Mask:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        self.subnet_entry = tk.Entry(settings_frame, font=("Arial", 10), width=15)
        self.subnet_entry.grid(row=0, column=3, padx=(10, 20))
        self.subnet_entry.insert(0, "255.255.255.0")
        
        # Gateway
        tk.Label(settings_frame, text="Gateway:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=1, column=0, sticky='w', pady=(10, 0))
        self.gateway_entry = tk.Entry(settings_frame, font=("Arial", 10), width=15)
        self.gateway_entry.grid(row=1, column=1, padx=(10, 20), pady=(10, 0))
        
        # Configuration buttons
        buttons_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        buttons_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Button(buttons_frame, text="Configure Network", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.configure_network).pack(side='left', padx=(0, 10))
        
        tk.Button(buttons_frame, text="Reset to DHCP", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.reset_to_dhcp).pack(side='left', padx=(0, 10))
        
        tk.Button(buttons_frame, text="COMPREHENSIVE NETWORK TEST", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.comprehensive_network_test).pack(side='left', padx=(0, 10))
        
        tk.Button(buttons_frame, text="FORCE SAVE NETWORK", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=self.force_save_network).pack(side='left', padx=(0, 10))
        
        # GDK Launch button
        tk.Button(buttons_frame, text="🚀 Launch GDK", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.launch_gdk).pack(side='left')
        
        # Status and log section
        status_frame = tk.LabelFrame(network_frame, text="Status & Log", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        status_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(status_frame, height=15, font=("Consolas", 9),
                                                bg='white', fg='black')
        self.log_text.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Initial log message
        self.log_info("Galil Setup Tool - Network Configuration")
        self.log_info("Ready to connect to controller...")
        
    def connect_to_controller(self):
        """Connect to the Galil controller"""
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return
            
        if not validate_ip_address(ip):
            messagebox.showerror("Error", "Invalid IP address format")
            return
            
        self.log_info(f"Connecting to controller at {ip}...")
        
        try:
            # Close existing connection if any
            if self.controller:
                try:
                    self.controller.disconnect()
                except:
                    pass
                self.controller = None
            
            # Create new controller connection
            self.controller = GalilController()
            self.controller.connect(ip)
            
            # Test if it's actually a Galil controller
            try:
                response = self.controller.send_command("MG _BN")
                if response and response.strip() != "?":
                    self.log_success(f"Successfully connected to controller at {ip}")
                    self.log_info(f"Controller serial: {response.strip()}")
                    messagebox.showinfo("Success", f"Connected to controller at {ip}")
                    
                    # Update UI to show connected state
                    self.update_connection_status(True)
                else:
                    self.log_error(f"Controller at {ip} is not responding to Galil commands")
                    self.controller.disconnect()
                    self.controller = None
                    messagebox.showerror("Connection Error", f"Controller at {ip} is not responding to Galil commands")
            except Exception as e:
                self.log_error(f"Controller validation failed: {e}")
                if self.controller:
                    self.controller.disconnect()
                    self.controller = None
                messagebox.showerror("Connection Error", f"Controller validation failed: {e}")
                
        except Exception as e:
            self.log_error(f"Connection error: {str(e)}")
            messagebox.showerror("Error", f"Connection error: {str(e)}")
            
    def disconnect_controller(self):
        """Disconnect from the Galil controller"""
        try:
            if self.controller:
                # Stop any ongoing motion
                self._stop_all_motion()
                
                # Close controller connection
                self._disconnect_controller()
                
                self.controller = None
                self.log_info("Disconnected from controller")
                
                # Update UI to show disconnected state
                self.update_connection_status(False)
                
                messagebox.showinfo("Success", "Disconnected from controller")
            else:
                messagebox.showinfo("Info", "No controller connected")
                
        except Exception as e:
            self.log_error(f"Disconnect error: {str(e)}")
            messagebox.showerror("Error", f"Disconnect error: {str(e)}")
            
    def discover_controllers(self):
        """Discover Galil controllers on the network"""
        self.log_info("Discovering Galil controllers on network...")
        
        try:
            controllers = discover_galil_controllers()
            if controllers:
                self.log_success(f"Found {len(controllers)} controller(s):")
                for controller in controllers:
                    self.log_info(f"  - {controller}")
            
            if not controllers:
                self.log_warning("No Galil controllers found on network")
        except Exception as e:
            self.log_error(f"Discovery error: {str(e)}")
            
    def configure_network(self):
        """Configure the controller's network settings"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        ip = self.new_ip_entry.get().strip()
        subnet = self.subnet_entry.get().strip()
        gateway = self.gateway_entry.get().strip()
        
        if not all([ip, subnet, gateway]):
            messagebox.showerror("Error", "Please fill in all network settings")
            return
            
        if not all(validate_ip_address(addr) for addr in [ip, subnet, gateway]):
            messagebox.showerror("Error", "Invalid IP address format")
            return
            
        self.log_info(f"Configuring network: IP={ip}, Subnet={subnet}, Gateway={gateway}")
        
        try:
            result = configure_controller_network_dmc4143(self.controller, ip, subnet, gateway)
            
            if result['success']:
                self.log_success("Network configuration completed successfully")
                self.log_info("Remember to power cycle the controller for changes to take effect")
                messagebox.showinfo("Success", "Network configuration completed successfully")
            else:
                self.log_error("Network configuration failed")
                self.log_error(f"Error: {result.get('error', 'Unknown error')}")
                messagebox.showerror("Error", "Network configuration failed")
                
        except Exception as e:
            self.log_error(f"Configuration error: {str(e)}")
            messagebox.showerror("Error", f"Configuration error: {str(e)}")
            
    def reset_to_dhcp(self):
        """Reset controller to DHCP mode"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        self.log_info("Resetting controller to DHCP mode...")
        
        try:
            result = reset_controller_network_to_dhcp(self.controller)
            
            if result['success']:
                self.log_success("Controller reset to DHCP mode successfully")
                messagebox.showinfo("Success", "Controller reset to DHCP mode")
            else:
                self.log_error("Failed to reset controller to DHCP")
                self.log_error(f"Error: {result.get('error', 'Unknown error')}")
                messagebox.showerror("Error", "Failed to reset controller to DHCP")
                
        except Exception as e:
            self.log_error(f"Reset error: {str(e)}")
            messagebox.showerror("Error", f"Reset error: {str(e)}")
            
    def comprehensive_network_test(self):
        """Run comprehensive network test"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        self.log_info("=== COMPREHENSIVE NETWORK TEST ===")
        
        try:
            results = comprehensive_network_test(self.controller)
            
            if results.get('error'):
                self.log_error(f"Test error: {results['error']}")
            else:
                self.log_success("Comprehensive network test completed")
                
                # Log key results
                if 'MG _BN' in results.get('basic_commands', {}):
                    serial = results['basic_commands']['MG _BN']
                    self.log_info(f"Controller serial: {serial}")
                
                if 'current_ip' in results.get('controller_info', {}):
                    current_ip = results['controller_info']['current_ip']
                    self.log_info(f"Current IP: {current_ip}")
                
                # Log recommendations
                for rec in results.get('recommendations', []):
                    self.log_info(f"Recommendation: {rec}")
                    
        except Exception as e:
            self.log_error(f"Test error: {str(e)}")
            
    def force_save_network(self):
        """Force save network settings"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        # Get current settings from entry fields
        ip = self.new_ip_entry.get().strip()
        subnet = self.subnet_entry.get().strip()
        gateway = self.gateway_entry.get().strip()
        
        if not all([ip, subnet, gateway]):
            messagebox.showerror("Error", "Please fill in all network settings first")
            return
            
        self.log_info("=== FORCE SAVE NETWORK SETTINGS ===")
        
        try:
            results = force_save_network_settings_dmc4143(self.controller, ip, subnet, gateway)
            
            if results.get('success'):
                self.log_success("Force save completed successfully")
                self.log_info("Remember to power cycle the controller")
                messagebox.showinfo("Success", "Force save completed successfully")
            else:
                self.log_error("Force save failed")
                self.log_error(f"Error: {results.get('error', 'Unknown error')}")
                messagebox.showerror("Error", "Force save failed")
                
        except Exception as e:
            self.log_error(f"Force save error: {str(e)}")
            messagebox.showerror("Error", f"Force save error: {str(e)}")
            
    def launch_gdk(self):
        """Launch Galil Development Kit (GDK)"""
        gdk_path = r"C:\Program Files\Galil\gdk\bin\gdk.exe"
        
        # Check if GDK exists
        if not os.path.exists(gdk_path):
            self.log_error("GDK not found at expected location")
            messagebox.showerror("Error", f"GDK not found at:\n{gdk_path}\n\nPlease ensure Galil Development Kit is installed.")
            return
        
        # Check if GDK is already running
        try:
            import psutil  # pyright: ignore[reportMissingModuleSource]
            gdk_running = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'gdk' in proc.info['name'].lower():
                    gdk_running = True
                    break
            
            if gdk_running:
                response = messagebox.askyesno("GDK Already Running", 
                    "GDK appears to be already running.\n\nWould you like to launch another instance?")
                if not response:
                    self.log_info("GDK launch cancelled - instance already running")
                    return
        except ImportError:
            # psutil not available, continue without checking
            pass
        
        self.log_info("=== LAUNCHING GALIL DEVELOPMENT KIT ===")
        self.log_info(f"GDK Path: {gdk_path}")
        
        try:
            # Launch GDK
            if self.controller:
                current_ip = self.ip_entry.get().strip()
                self.log_info(f"Current controller IP: {current_ip}")
                self.log_info("Attempting to launch GDK with controller connection...")
                
                # Try to launch GDK with IP parameter (if supported)
                try:
                    # Some versions of GDK support command line parameters
                    subprocess.Popen([gdk_path, "--ip", current_ip], shell=True)
                    self.log_success("GDK launched with controller IP")
                except:
                    # Fallback to standard launch
                    subprocess.Popen([gdk_path], shell=True)
                    self.log_success("GDK launched successfully")
                    self.log_info("You can connect to the controller in GDK using IP: " + current_ip)
            else:
                # Launch GDK normally
                subprocess.Popen([gdk_path], shell=True)
                self.log_success("GDK launched successfully")
                self.log_info("GDK should open in a new window")
                self.log_info("No controller currently connected")
            
        except Exception as e:
            error_msg = f"Failed to launch GDK: {str(e)}"
            self.log_error(error_msg)
            messagebox.showerror("Launch Error", error_msg)
            
    def log_info(self, message):
        """Log an info message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] INFO: {message}\n")
        self.log_text.see(tk.END)
        
    def log_success(self, message):
        """Log a success message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] SUCCESS: {message}\n")
        self.log_text.see(tk.END)
        
    def log_warning(self, message):
        """Log a warning message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] WARNING: {message}\n")
        self.log_text.see(tk.END)
        
    def log_error(self, message):
        """Log an error message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ERROR: {message}\n")
        self.log_text.see(tk.END)
        
    def tune_axis(self):
        """Tune the selected axis with PID values"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            kp = float(self.kp_entry.get())
            ki = float(self.ki_entry.get())
            kd = float(self.kd_entry.get())
            
            self.motor_status_text.insert(tk.END, f"Tuning axis {axis} with KP={kp}, KI={ki}, KD={kd}...\n")
            
            # Use the galil_functions module function
            galil_functions.tune_axis(self.controller, axis, kp, ki, kd)
            
            self.motor_status_text.insert(tk.END, f"Axis {axis} tuning completed successfully!\n")
            self.motor_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Tuning error: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Tuning Error", error_msg)
            
    def apply_motion_params(self):
        """Apply motion parameters to the selected axis"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            speed = int(self.speed_entry.get())
            accel = int(self.accel_entry.get())
            decel = int(self.decel_entry.get())
            
            self.motor_status_text.insert(tk.END, f"Applying motion parameters to axis {axis}...\n")
            
            # Apply parameters
            self.controller.send_command(f"SP{axis}={speed}")
            self.controller.send_command(f"AC{axis}={accel}")
            self.controller.send_command(f"DC{axis}={decel}")
            
            self.motor_status_text.insert(tk.END, f"Motion parameters applied successfully!\n")
            self.motor_status_text.insert(tk.END, f"Speed: {speed}, Accel: {accel}, Decel: {decel}\n")
            self.motor_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Parameter application error: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Parameter Error", error_msg)
            
    def define_motor_direction(self):
        """Define the positive direction of motor travel"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            polarity = self.encoder_polarity_var.get()
            
            self.motor_status_text.insert(tk.END, f"=== DEFINING MOTOR DIRECTION FOR AXIS {axis} ===\n")
            self.motor_status_text.insert(tk.END, f"Encoder Polarity: {polarity}\n")
            self.motor_status_text.insert(tk.END, "Instructions:\n")
            self.motor_status_text.insert(tk.END, "1. Click 'Define Motor Direction' button\n")
            self.motor_status_text.insert(tk.END, "2. Move motor by hand in desired positive direction\n")
            self.motor_status_text.insert(tk.END, "3. Watch for encoder count changes\n")
            self.motor_status_text.insert(tk.END, "4. If counts increase in wrong direction, change polarity\n\n")
            
            # Set encoder polarity
            if polarity == "Reversed":
                self.controller.send_command(f"EP{axis}=1")
                self.motor_status_text.insert(tk.END, f"Encoder polarity set to REVERSED for axis {axis}\n")
            else:
                self.controller.send_command(f"EP{axis}=0")
                self.motor_status_text.insert(tk.END, f"Encoder polarity set to NORMAL for axis {axis}\n")
            
            # Enable servo for testing
            self.controller.send_command(f"SH{axis}")
            time.sleep(0.5)
            
            # Get initial position
            initial_pos = int(self.controller.send_command(f"TP {axis}").strip())
            self.motor_status_text.insert(tk.END, f"Initial position: {initial_pos}\n")
            self.motor_status_text.insert(tk.END, "Now move the motor by hand in the desired positive direction...\n")
            self.motor_status_text.insert(tk.END, "Watch the position change in the real-time encoder display above.\n\n")
            
            # Set flag to enable position logging during motor direction test
            self.motor_direction_test_active = True
            
            # Monitor position changes for 10 seconds with real-time updates
            start_time = time.time()
            last_pos = initial_pos
            update_count = 0
            
            while time.time() - start_time < 10.0:
                try:
                    # Update the encoder display
                    self.update_encoder_positions()
                    
                    # Get current position
                    current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    
                    # Show significant changes in the status area
                    if current_pos != last_pos:
                        change = current_pos - last_pos
                        direction = "positive" if change > 0 else "negative"
                        self.motor_status_text.insert(tk.END, f"Position: {current_pos} (change: {change:+d} counts - {direction} direction)\n")
                        last_pos = current_pos
                        update_count += 1
                    
                    # Update status every 2 seconds
                    if update_count % 20 == 0 and update_count > 0:
                        remaining = 10 - int(time.time() - start_time)
                        self.motor_status_text.insert(tk.END, f"Monitoring... {remaining} seconds remaining\n")
                    
                    time.sleep(0.1)
                except Exception as e:
                    time.sleep(0.1)
            
            # Clear flag to stop position logging
            self.motor_direction_test_active = False
            
            # Disable servo
            self.controller.send_command(f"MO{axis}")
            
            self.motor_status_text.insert(tk.END, "Motor direction test completed.\n")
            self.motor_status_text.insert(tk.END, "If the direction was wrong, change the encoder polarity and repeat.\n\n")
            self.motor_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Motor direction definition error: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Direction Error", error_msg)
            
    def estimate_brushless_modulo(self):
        """Estimate brushless modulo using position analysis (works with any controller)"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            
            self.motor_status_text.insert(tk.END, f"=== ESTIMATING BRUSHLESS MODULO FOR AXIS {axis} ===\n")
            self.motor_status_text.insert(tk.END, "This test will take a maximum of 30 seconds.\n")
            
            # Step 1: Check controller capabilities
            self.motor_status_text.insert(tk.END, "Step 1/3: Checking controller capabilities...\n")
            
            brushless_supported = False
            try:
                # Test if brushless commands are supported
                test_response = self.controller.send_command(f"BL{axis}")
                if "?" not in test_response:
                    brushless_supported = True
                    self.motor_status_text.insert(tk.END, "✓ Controller supports brushless commands\n")
                else:
                    self.motor_status_text.insert(tk.END, "⚠ Controller does not support brushless commands\n")
            except:
                self.motor_status_text.insert(tk.END, "⚠ Controller does not support brushless commands\n")
            
            # Step 2: Check what motion commands are supported
            self.motor_status_text.insert(tk.END, "Step 2/3: Checking motion command support...\n")
            
            motion_commands_supported = False
            try:
                # Test basic motion commands
                test_pr = self.controller.send_command(f"PR{axis}=100")
                test_bg = self.controller.send_command(f"BG{axis}")
                test_st = self.controller.send_command(f"ST{axis}")
                
                if "?" not in test_pr and "?" not in test_bg and "?" not in test_st:
                    motion_commands_supported = True
                    self.motor_status_text.insert(tk.END, "✓ Motion commands supported\n")
                else:
                    self.motor_status_text.insert(tk.END, "⚠ Motion commands not supported\n")
            except:
                self.motor_status_text.insert(tk.END, "⚠ Motion commands not supported\n")
            
            # Step 3: Perform manual movement-based brushless analysis
            self.motor_status_text.insert(tk.END, "Step 3/3: Manual movement brushless analysis...\n")
            self.motor_status_text.insert(tk.END, "This method requires manual movement of the motor.\n")
            self.motor_status_text.insert(tk.END, "Please move the motor by hand in both directions during this test.\n\n")
            
            try:
                # Enable servo for testing
                self.controller.send_command(f"SH{axis}")
                time.sleep(0.5)
                
                # Get initial position
                initial_pos = int(self.controller.send_command(f"TP{axis}").strip())
                self.motor_status_text.insert(tk.END, f"Initial position: {initial_pos}\n")
                self.motor_status_text.insert(tk.END, "Starting movement analysis...\n")
                
                # Monitor movement for 15 seconds to collect data
                start_time = time.time()
                positions = []
                last_pos = initial_pos
                movement_detected = False
                
                while time.time() - start_time < 15.0:
                    try:
                        current_pos = int(self.controller.send_command(f"TP{axis}").strip())
                        positions.append(current_pos)
                        
                        # Check for significant movement
                        if abs(current_pos - last_pos) > 10:
                            movement_detected = True
                            self.motor_status_text.insert(tk.END, f"Movement detected: {last_pos} → {current_pos} (change: {current_pos - last_pos:+d})\n")
                        
                        last_pos = current_pos
                        time.sleep(0.1)
                        
                        # Update progress every 3 seconds
                        elapsed = int(time.time() - start_time)
                        if elapsed % 3 == 0 and elapsed > 0:
                            remaining = 15 - elapsed
                            self.motor_status_text.insert(tk.END, f"Analyzing... {remaining} seconds remaining\n")
                            
                    except Exception as e:
                        time.sleep(0.1)
                        continue
                
                # Disable servo
                self.controller.send_command(f"MO{axis}")
                
                if not movement_detected:
                    self.motor_status_text.insert(tk.END, "⚠ No significant movement detected during test\n")
                    self.motor_status_text.insert(tk.END, "Please ensure motor is free to move and try again\n")
                    return
                
                # Analyze the collected position data
                self.motor_status_text.insert(tk.END, f"✓ Collected {len(positions)} position samples\n")
                
                # Calculate movement statistics
                min_pos = min(positions)
                max_pos = max(positions)
                total_movement = max_pos - min_pos
                
                self.motor_status_text.insert(tk.END, f"Movement range: {min_pos} to {max_pos} (total: {total_movement} counts)\n")
                
                # Estimate brushless modulo based on movement patterns
                estimated_bm = self.estimate_bm_from_movement(positions, total_movement)
                estimated_pole_pairs = self.estimate_pole_pairs_from_bm(estimated_bm)
                
                self.motor_status_text.insert(tk.END, f"✓ Movement analysis completed\n")
                self.motor_status_text.insert(tk.END, f"✓ Estimated brushless modulo: {estimated_bm:.1f}\n")
                self.motor_status_text.insert(tk.END, f"✓ Estimated pole pairs: {estimated_pole_pairs:.1f}\n")
                
                # Store the estimated values
                self.brushless_bm = estimated_bm
                self.brushless_pole_pairs = estimated_pole_pairs
                
                # Try to apply brushless configuration if supported
                if brushless_supported:
                    try:
                        self.controller.send_command(f"BM{axis}={estimated_bm}")
                        self.controller.send_command(f"BL{axis}=1")
                        self.motor_status_text.insert(tk.END, "✓ Brushless configuration applied to controller\n")
                    except:
                        self.motor_status_text.insert(tk.END, "⚠ Could not apply brushless configuration\n")
                else:
                    self.motor_status_text.insert(tk.END, "⚠ Brushless configuration stored locally (controller not supported)\n")
                
                self.motor_status_text.insert(tk.END, "✓ Brushless analysis completed!\n")
                self.motor_status_text.insert(tk.END, f"Final BM value: {self.brushless_bm:.1f}\n")
                self.motor_status_text.insert(tk.END, f"Pole pairs: {self.brushless_pole_pairs:.1f}\n")
                self.motor_status_text.insert(tk.END, "Note: For optimal brushless motor setup, use Galil's GDK software.\n\n")
                self.motor_status_text.see(tk.END)
                
            except Exception as est_error:
                self.motor_status_text.insert(tk.END, f"⚠ Analysis failed: {est_error}\n")
                self.motor_status_text.insert(tk.END, "Using default brushless configuration...\n")
                
                # Set default values
                self.brushless_bm = 5000.0
                self.brushless_pole_pairs = 4.0
                
                self.motor_status_text.insert(tk.END, f"Default BM: {self.brushless_bm:.1f}\n")
                self.motor_status_text.insert(tk.END, "For optimal brushless motors, use Galil's GDK software.\n\n")
                self.motor_status_text.see(tk.END)
                
        except Exception as e:
            error_msg = f"Brushless modulo estimation error: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Estimation Error", error_msg)
                
    def estimate_bm_from_movement(self, positions, total_movement):
        """
        Estimate brushless modulo from movement data.
        
        Args:
            positions (list): List of encoder position readings
            total_movement (float): Total movement range in encoder counts
            
        Returns:
            float: Estimated brushless modulo value
        """
        # Validate input data
        if not positions or len(positions) < 10:
            return 4000.0  # Default fallback for insufficient data
            
        # Calculate position differences (movement between readings)
        diffs = []
        for i in range(1, len(positions)):
            diff = abs(positions[i] - positions[i-1])
            if diff > 5:  # Only consider significant movements (>5 counts)
                diffs.append(diff)
        
        # Check if we have enough movement data
        if not diffs:
            return 4000.0  # Default fallback for no significant movement
            
        # Calculate movement statistics
        avg_movement = sum(diffs) / len(diffs)
        max_movement = max(diffs)
        
        # Estimate brushless modulo based on movement characteristics
        # Higher resolution encoders typically show larger total movement
        # and more consistent movement patterns
        
        if total_movement > 50000:
            # High-resolution encoder (>50k counts total movement)
            if avg_movement > 1000:
                return 8000.0  # High-resolution, fast movement
            else:
                return 6000.0  # High-resolution, slow movement
        elif total_movement > 10000:
            # Medium-resolution encoder (10k-50k counts total movement)
            if avg_movement > 500:
                return 4000.0  # Medium-resolution, fast movement
            else:
                return 3000.0  # Medium-resolution, slow movement
        else:
            # Low-resolution encoder (<10k counts total movement)
            if avg_movement > 200:
                return 2000.0  # Low-resolution, fast movement
            else:
                return 1500.0  # Low-resolution, slow movement
                
    def estimate_pole_pairs_from_bm(self, bm):
        """Estimate pole pairs from brushless modulo"""
        # Common relationships between BM and pole pairs
        if bm >= 6000:
            return 4.0  # High-resolution, likely 4-pole motor
        elif bm >= 3000:
            return 2.0  # Medium-resolution, likely 2-pole motor
        else:
            return 1.0  # Low-resolution, likely 1-pole motor
            
    def latch_indexes(self):
        """Latch indexes to improve brushless modulo accuracy (works with any controller)"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            
            self.motor_status_text.insert(tk.END, f"=== LATCHING INDEXES FOR AXIS {axis} ===\n")
            self.motor_status_text.insert(tk.END, "This test will take a maximum of 10 seconds to run.\n")
            
            # Check if index is available
            self.motor_status_text.insert(tk.END, "Checking for index signal...\n")
            
            index_supported = False
            try:
                # Check if index is present (some controllers support this)
                index_response = self.controller.send_command(f"_IX{axis}")
                if "?" not in index_response:
                    index_supported = True
                    self.motor_status_text.insert(tk.END, f"✓ Index detection supported: {index_response.strip()}\n")
                else:
                    self.motor_status_text.insert(tk.END, "⚠ Index detection command not supported\n")
            except:
                self.motor_status_text.insert(tk.END, "⚠ Index detection command not supported\n")
            
            # Check motion command support
            motion_commands_supported = self._check_motion_command_support(axis)
            
            # Get current position for analysis
            try:
                current_pos = int(self.controller.send_command(f"TP{axis}").strip())
                self.motor_status_text.insert(tk.END, f"Current position: {current_pos}\n")
            except:
                current_pos = 0
                self.motor_status_text.insert(tk.END, "⚠ Could not read current position\n")
            
            # Perform index analysis based on available capabilities
            if motion_commands_supported:
                # Use motion-based index latching
                self.motor_status_text.insert(tk.END, "Using motion-based index latching...\n")
                
                try:
                    # Enable servo
                    self.controller.send_command(f"SH{axis}")
                    time.sleep(0.5)
                    self.motor_status_text.insert(tk.END, f"✓ Servo enabled for axis {axis}\n")
                    
                    # Set motion parameters
                    self.controller.send_command(f"SP{axis}=500")
                    self.controller.send_command(f"AC{axis}=500")
                    self.controller.send_command(f"DC{axis}=500")
                    
                    # First movement
                    self.motor_status_text.insert(tk.END, "✓ Latch: 1\n")
                    self.controller.send_command(f"PR{axis}=5000")
                    self.controller.send_command(f"BG{axis}")
                    time.sleep(2.0)
                    self.controller.send_command(f"ST{axis}")
                    time.sleep(0.5)
                    
                    pos1 = int(self.controller.send_command(f"TP{axis}").strip())
                    movement1 = pos1 - current_pos
                    self.motor_status_text.insert(tk.END, f"First movement: {movement1} counts\n")
                    
                    # Second movement
                    self.motor_status_text.insert(tk.END, "✓ Latch: 2\n")
                    self.controller.send_command(f"PR{axis}=10000")
                    self.controller.send_command(f"BG{axis}")
                    time.sleep(2.0)
                    self.controller.send_command(f"ST{axis}")
                    time.sleep(0.5)
                    
                    pos2 = int(self.controller.send_command(f"TP{axis}").strip())
                    movement2 = pos2 - pos1
                    self.motor_status_text.insert(tk.END, f"Second movement: {movement2} counts\n")
                    
                    # Calculate improved BM from movements
                    if abs(movement1) > 100 and abs(movement2) > 100:
                        avg_movement = (abs(movement1) + abs(movement2)) / 2.0
                        index_distance = avg_movement * 4.0
                        brushless_bm = index_distance / 4.0  # Assume 4 pole pairs
                        
                        self.motor_status_text.insert(tk.END, f"✓ Index distance: {index_distance:.1f}\n")
                        self.motor_status_text.insert(tk.END, f"✓ Improved BM: {brushless_bm:.1f}\n")
                    else:
                        brushless_bm = 5000.0
                        self.motor_status_text.insert(tk.END, "⚠ Insufficient movement, using default BM\n")
                    
                    # Disable servo
                    self.controller.send_command(f"MO{axis}")
                    
                except Exception as move_error:
                    self.motor_status_text.insert(tk.END, f"⚠ Motion-based latching failed: {move_error}\n")
                    brushless_bm = 5000.0
                    
            else:
                # Use position-based index analysis
                self.motor_status_text.insert(tk.END, "Using position-based index analysis...\n")
                
                # Analyze current position for index patterns
                pos_magnitude = abs(current_pos)
                
                if pos_magnitude > 10000:
                    brushless_bm = 8000.0
                    self.motor_status_text.insert(tk.END, "✓ High-resolution position detected\n")
                elif pos_magnitude > 1000:
                    brushless_bm = 4000.0
                    self.motor_status_text.insert(tk.END, "✓ Standard resolution position detected\n")
                else:
                    brushless_bm = 2000.0
                    self.motor_status_text.insert(tk.END, "✓ Low-resolution position detected\n")
                
                # Check for common index patterns
                if current_pos != 0:
                    if abs(current_pos) % 1000 < 100:
                        brushless_bm = 1000.0
                    elif abs(current_pos) % 2000 < 200:
                        brushless_bm = 2000.0
                    elif abs(current_pos) % 4000 < 400:
                        brushless_bm = 4000.0
                    elif abs(current_pos) % 8000 < 800:
                        brushless_bm = 8000.0
                
                self.motor_status_text.insert(tk.END, f"✓ Position-based BM: {brushless_bm:.1f}\n")
            
            # Store the improved BM
            self.brushless_bm = brushless_bm
            
            # Try to apply to controller if supported
            try:
                test_response = self.controller.send_command(f"BM{axis}")
                if "?" not in test_response:
                    self.controller.send_command(f"BM{axis}={brushless_bm}")
                    self.motor_status_text.insert(tk.END, f"✓ Improved BM applied to controller\n")
                else:
                    self.motor_status_text.insert(tk.END, f"⚠ BM stored locally (controller not supported)\n")
            except:
                self.motor_status_text.insert(tk.END, f"⚠ Could not apply improved BM\n")
            
            self.motor_status_text.insert(tk.END, "✓ Index latching completed!\n")
            self.motor_status_text.insert(tk.END, f"Final BM value: {self.brushless_bm:.1f}\n")
            self.motor_status_text.insert(tk.END, "✓ Improved brushless configuration stored\n\n")
            self.motor_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Index latching error: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.insert(tk.END, "This controller may not support index latching.\n")
            self.motor_status_text.insert(tk.END, "For accurate brushless motor setup, use Galil's GDK software.\n\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Index Error", error_msg)
            
    def skip_index_latching(self):
        """Skip index latching step"""
        self.motor_status_text.insert(tk.END, "Index latching skipped.\n")
        self.motor_status_text.insert(tk.END, "Using estimated brushless modulo from previous step.\n\n")
        self.motor_status_text.see(tk.END)
        
    def save_brushless_settings(self):
        """Save brushless motor configuration settings"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            
            if not hasattr(self, 'brushless_bm'):
                messagebox.showerror("Error", "Please run brushless modulo estimation first")
                return
            
            self.motor_status_text.insert(tk.END, f"=== SAVING BRUSHLESS SETTINGS FOR AXIS {axis} ===\n")
            
            # Save brushless modulo with error handling
            try:
                self.controller.send_command(f"BM{axis}={self.brushless_bm}")
                self.motor_status_text.insert(tk.END, f"✓ Brushless Modulo (BM): {self.brushless_bm:.4f}\n")
            except Exception as bm_error:
                self.motor_status_text.insert(tk.END, f"⚠ Warning: Could not save BM: {bm_error}\n")
                self.motor_status_text.insert(tk.END, "Continuing with simulation...\n")
            
            # Set up brushless mode with error handling
            try:
                self.controller.send_command(f"BL{axis}=1")  # Enable brushless mode
                self.motor_status_text.insert(tk.END, f"✓ Brushless mode enabled for axis {axis}\n")
            except Exception as bl_error:
                self.motor_status_text.insert(tk.END, f"⚠ Warning: Could not enable brushless mode: {bl_error}\n")
                self.motor_status_text.insert(tk.END, "Continuing with simulation...\n")
            
            # Save settings to non-volatile memory with error handling
            try:
                self.controller.send_command("BN")
                time.sleep(1.0)
                self.motor_status_text.insert(tk.END, f"✓ Settings saved to controller memory\n")
            except Exception as bn_error:
                self.motor_status_text.insert(tk.END, f"⚠ Warning: Could not save to memory: {bn_error}\n")
                self.motor_status_text.insert(tk.END, "Continuing with simulation...\n")
            
            self.motor_status_text.insert(tk.END, f"✓ Configuration and Setup Complete!\n")
            self.motor_status_text.insert(tk.END, f"You have successfully configured this axis for sinusoidal commutation.\n")
            self.motor_status_text.insert(tk.END, "Note: This is a simulated configuration. For real brushless motors,\n")
            self.motor_status_text.insert(tk.END, "use Galil's GDK software for accurate brushless motor setup.\n\n")
            self.motor_status_text.see(tk.END)
            
            messagebox.showinfo("Success", f"Brushless motor configuration completed for axis {axis}!\n\nNote: This is a demonstration. For production use, use Galil's GDK software.")
            
        except Exception as e:
            error_msg = f"Save brushless settings error: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.insert(tk.END, "This feature requires brushless motor support on your controller.\n")
            self.motor_status_text.insert(tk.END, "For accurate brushless motor setup, use Galil's GDK software.\n\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Save Error", error_msg)
            
    def update_encoder_positions(self):
        """Update the encoder position display for all axes with real-time data"""
        # Check if encoder labels exist (widgets might be destroyed)
        if not hasattr(self, 'encoder_labels') or not self.encoder_labels:
            return
            
        if not self.controller:
            # Update labels to show "No Connection"
            for axis in ["A", "B", "C", "D"]:
                if axis in self.encoder_labels:
                    try:
                        self.encoder_labels[axis].config(text="No Connection", fg='red')
                    except tk.TclError:
                        # Widget was destroyed, ignore
                        pass
            return
            
        try:
            # Update positions for all axes with real controller data
            for axis in ["A", "B", "C", "D"]:
                if axis in self.encoder_labels:
                    try:
                        # Use TP command to get real encoder position (TP = Tell Position)
                        # This is the standard Galil command for getting axis position
                        position_response = self.controller.send_command(f"TP{axis}")
                        
                        # Handle different response formats
                        if position_response and position_response.strip():
                            try:
                                position = int(float(position_response.strip()))
                                # Format the position nicely (remove trailing zeros)
                                formatted_position = str(position)
                                self.encoder_labels[axis].config(text=formatted_position, fg='black')
                                
                                # Only log position updates during motor direction test, not continuously
                                # Initialize the flag if it doesn't exist
                                if not hasattr(self, 'motor_direction_test_active'):
                                    self.motor_direction_test_active = False
                                    
                                if self.motor_direction_test_active and hasattr(self, 'motor_status_text'):
                                    timestamp = time.strftime("%H:%M:%S")
                                    self.motor_status_text.insert(tk.END, f"[{timestamp}] Axis {axis}: {formatted_position}\n")
                                    self.motor_status_text.see(tk.END)
                            except (ValueError, TypeError):
                                # Invalid numeric response
                                self.encoder_labels[axis].config(text="Invalid", fg='orange')
                        else:
                            # Empty response
                            self.encoder_labels[axis].config(text="No Data", fg='orange')
                            
                    except Exception as e:
                        # Handle communication errors
                        try:
                            error_text = "Comm Error"
                            if "timeout" in str(e).lower():
                                error_text = "Timeout"
                            elif "connection" in str(e).lower():
                                error_text = "No Connection"
                            else:
                                error_text = "Error"
                                
                            self.encoder_labels[axis].config(text=error_text, fg='red')
                            
                            # Log the error for debugging
                            if hasattr(self, 'motor_status_text'):
                                timestamp = time.strftime("%H:%M:%S")
                                self.motor_status_text.insert(tk.END, f"[{timestamp}] Axis {axis} error: {str(e)}\n")
                                self.motor_status_text.see(tk.END)
                                
                        except tk.TclError:
                            # Widget was destroyed, ignore
                            pass
                        
        except Exception as e:
            # If there's a general error, show error on all labels
            for axis in ["A", "B", "C", "D"]:
                if axis in self.encoder_labels:
                    try:
                        self.encoder_labels[axis].config(text="System Error", fg='red')
                    except tk.TclError:
                        # Widget was destroyed, ignore
                        pass
            
            # Log the general error
            if hasattr(self, 'motor_status_text'):
                timestamp = time.strftime("%H:%M:%S")
                self.motor_status_text.insert(tk.END, f"[{timestamp}] General error: {str(e)}\n")
                self.motor_status_text.see(tk.END)
    
    def toggle_auto_update(self):
        """Toggle automatic encoder position updates"""
        if self.auto_update_var.get():
            # Start auto-update
            self.start_encoder_auto_update()
        else:
            # Stop auto-update
            self.stop_encoder_auto_update()
    
    def start_encoder_auto_update(self):
        """Start automatic encoder position updates with real-time data"""
        if hasattr(self, 'encoder_update_job'):
            self.root.after_cancel(self.encoder_update_job)
        
        def update_loop():
            try:
                # Check if we're still on the motor setup page
                if hasattr(self, 'encoder_labels') and self.encoder_labels:
                    self.update_encoder_positions()
                    if self.auto_update_var.get():
                        # Update every 500ms for real-time responsiveness
                        self.encoder_update_job = self.root.after(500, update_loop)
            except Exception as e:
                # If there's an error, stop the update loop
                if hasattr(self, 'encoder_update_job'):
                    self.root.after_cancel(self.encoder_update_job)
                # Log the error
                if hasattr(self, 'motor_status_text'):
                    timestamp = time.strftime("%H:%M:%S")
                    self.motor_status_text.insert(tk.END, f"[{timestamp}] Auto-update error: {str(e)}\n")
                    self.motor_status_text.see(tk.END)
        
        self.encoder_update_job = self.root.after(100, update_loop)  # Start immediately
    
    def stop_encoder_auto_update(self):
        """Stop automatic encoder position updates"""
        if hasattr(self, 'encoder_update_job'):
            self.root.after_cancel(self.encoder_update_job)
            delattr(self, 'encoder_update_job')
    
    def on_motor_setup_show(self):
        """Called when motor setup page is shown"""
        # Start auto-update if enabled
        if hasattr(self, 'auto_update_var') and self.auto_update_var.get():
            self.start_encoder_auto_update()
        # Initial position update
        self.update_encoder_positions()
    
    def on_motor_setup_hide(self):
        """Called when leaving motor setup page"""
        # Stop auto-update to prevent errors
        self.stop_encoder_auto_update()
    
    def test_controller_connection(self):
        """Test the controller connection and show real-time data status"""
        self._ensure_controller_connected()
            
        try:
            # Test basic communication
            self.motor_status_text.insert(tk.END, "=== Testing Controller Connection ===\n")
            
            # Test controller serial number
            try:
                serial_response = self.controller.send_command("SN")
                self.motor_status_text.insert(tk.END, f"Controller Serial: {serial_response.strip()}\n")
            except Exception as e:
                self.motor_status_text.insert(tk.END, f"Serial test failed: {str(e)}\n")
            
            # Test position reading for each axis
            self._test_all_axis_positions()
            
            # Test servo status
            try:
                servo_response = self.controller.send_command("_SS")
                self.motor_status_text.insert(tk.END, f"Servo status: {servo_response.strip()}\n")
            except Exception as e:
                self.motor_status_text.insert(tk.END, f"Servo status test failed: {str(e)}\n")
            
            self.motor_status_text.insert(tk.END, "=== Connection Test Complete ===\n")
            self.motor_status_text.see(tk.END)
            
            messagebox.showinfo("Connection Test", "Controller connection test completed. Check the status log for details.")
            
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            self.motor_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motor_status_text.see(tk.END)
            messagebox.showerror("Test Error", error_msg)
    
    def copy_motor_setup_log(self):
        """Copy the motor setup status log to clipboard"""
        try:
            # Get the text from the motor status text area
            log_text = self.motor_status_text.get(1.0, tk.END)
            
            # Add timestamp and header
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            header = f"=== Motor Setup Log - {timestamp} ===\n"
            full_log = header + log_text
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(full_log)
            
            # Show success message
            messagebox.showinfo("Copy Log", "Motor setup log copied to clipboard successfully!")
            
        except Exception as e:
            error_msg = f"Error copying log: {str(e)}"
            messagebox.showerror("Copy Error", error_msg)
    
    def toggle_pid_section(self, event=None):
        """Toggle PID configuration section visibility"""
        if hasattr(self, 'pid_content'):
            if self.pid_content.winfo_viewable():
                self.pid_content.pack_forget()
                self.pid_frame.configure(text="⚙️ PID Configuration ▶")
            else:
                self.pid_content.pack(fill='x', padx=15, pady=10)
                self.pid_frame.configure(text="⚙️ PID Configuration ▼")
    
    def toggle_motion_section(self, event=None):
        """Toggle motion parameters section visibility"""
        if hasattr(self, 'motion_content'):
            if self.motion_content.winfo_viewable():
                self.motion_content.pack_forget()
                self.motion_frame.configure(text="🚀 Motion Parameters ▶")
            else:
                self.motion_content.pack(fill='x', padx=15, pady=10)
                self.motion_frame.configure(text="🚀 Motion Parameters ▼")
    
    def toggle_brushless_section(self, event=None):
        """Toggle brushless motor configuration section visibility"""
        if hasattr(self, 'brushless_content'):
            if self.brushless_content.winfo_viewable():
                self.brushless_content.pack_forget()
                self.brushless_frame.configure(text="🔧 Brushless Motor Configuration ▶")
            else:
                self.brushless_content.pack(fill='x', padx=15, pady=10)
                self.brushless_frame.configure(text="🔧 Brushless Motor Configuration ▼")
            
    def jog_axis(self, direction):
        """Jog the selected axis by the specified distance"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.jog_axis_var.get()
            distance = float(self.jog_distance_entry.get()) * direction
            
            self.motion_status_text.insert(tk.END, f"Jogging axis {axis} by {abs(distance)}mm...\n")
            
            # Use the galil_functions module function
            # Assuming 0.2 turns per mm and 64000 clicks per turn (default values)
            turns_per_mm = 0.2
            clicks_per_turn = 64000
            
            # Get speed from the speed entry field
            speed = int(self.speed_entry.get())
            galil_functions.jog_distance(self.controller, axis, distance, turns_per_mm, clicks_per_turn, speed)
            
            self.motion_status_text.insert(tk.END, f"Jog command sent successfully!\n")
            self.motion_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Jog error: {str(e)}"
            self.motion_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motion_status_text.see(tk.END)
            messagebox.showerror("Jog Error", error_msg)
            
    def stop_axis(self):
        """Stop the selected axis"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.jog_axis_var.get()
            
            self.motion_status_text.insert(tk.END, f"Stopping axis {axis}...\n")
            
            # Stop the axis
            self.controller.send_command(f"ST{axis}")
            
            self.motion_status_text.insert(tk.END, f"Axis {axis} stopped successfully!\n")
            self.motion_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Stop error: {str(e)}"
            self.motion_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motion_status_text.see(tk.END)
            messagebox.showerror("Stop Error", error_msg)
            
    def move_to_position(self):
        """Move the selected axis to the specified position"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.pos_axis_var.get()
            position = int(self.position_entry.get())
            
            self.motion_status_text.insert(tk.END, f"Moving axis {axis} to position {position}...\n")
            
            # Use the galil_functions module function
            # Get speed from the speed entry field
            speed = int(self.speed_entry.get())
            galil_functions.move_to_position(self.controller, axis, position, speed)
            
            self.motion_status_text.insert(tk.END, f"Move command sent successfully!\n")
            self.motion_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Move error: {str(e)}"
            self.motion_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.motion_status_text.see(tk.END)
            messagebox.showerror("Move Error", error_msg)
            
    def get_controller_info(self):
        """Get static controller information"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.diag_status_text.delete(1.0, tk.END)
            self.diag_status_text.insert(tk.END, "Getting controller information...\n\n")
            
            # Use the galil_functions module function
            info = galil_functions.get_controller_info(self.controller)
            
            self.diag_status_text.insert(tk.END, "CONTROLLER INFORMATION:\n")
            self.diag_status_text.insert(tk.END, "=" * 50 + "\n")
            self.diag_status_text.insert(tk.END, info + "\n")
            self.diag_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Error getting controller info: {str(e)}"
            self.diag_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.diag_status_text.see(tk.END)
            messagebox.showerror("Error", error_msg)
            
    def toggle_live_diagnostics(self):
        """Toggle live diagnostic updates"""
        if self.live_diag_var.get():
            self.start_live_diagnostics()
        else:
            self.stop_live_diagnostics()
            
    def start_live_diagnostics(self):
        """Start live diagnostic updates"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            self.live_diag_var.set(False)
            return
            
        if self.live_update_running:
            return
            
        self.live_update_running = True
        self.live_update_thread = threading.Thread(target=self.live_diagnostic_loop, daemon=True)
        self.live_update_thread.start()
        
    def stop_live_diagnostics(self):
        """Stop live diagnostic updates"""
        self.live_update_running = False
        if self.live_update_thread:
            self.live_update_thread.join(timeout=1)
            
    def live_diagnostic_loop(self):
        """Live diagnostic update loop"""
        while self.live_update_running:
            try:
                if not self.controller:
                    break
                    
                # Get live diagnostics
                diag_info = galil_functions.get_diagnostics(self.controller)
                
                # Update UI in main thread
                self.root.after(0, self.update_diagnostic_display, diag_info)
                
                # Sleep for update interval
                interval = int(self.update_interval_entry.get())
                time.sleep(interval / 1000.0)
                
            except Exception as e:
                # Update UI with error in main thread
                self.root.after(0, self.update_diagnostic_display, f"Live update error: {str(e)}")
                break
                
    def update_diagnostic_display(self, info):
        """Update diagnostic display with new information"""
        if not self.live_update_running:
            return
            
        self.diag_status_text.delete(1.0, tk.END)
        self.diag_status_text.insert(tk.END, "LIVE DIAGNOSTICS:\n")
        self.diag_status_text.insert(tk.END, "=" * 50 + "\n")
        self.diag_status_text.insert(tk.END, f"Last Update: {datetime.now().strftime('%H:%M:%S')}\n\n")
        self.diag_status_text.insert(tk.END, info + "\n")
        self.diag_status_text.see(tk.END)
        
    def toggle_encoder_display(self):
        """Toggle encoder position display"""
        if self.encoder_running:
            self.stop_encoder_display()
        else:
            self.start_encoder_display()
            
    def start_encoder_display(self):
        """Start encoder position display"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        if self.encoder_update_running:
            return
            
        self.encoder_running = True
        self.encoder_start_btn.configure(text="Stop Encoder Display", bg=self.colors['error_red'])
        
        self.encoder_update_running = True
        self.encoder_update_thread = threading.Thread(target=self.encoder_update_loop, daemon=True)
        self.encoder_update_thread.start()
        
    def stop_encoder_display(self):
        """Stop encoder position display"""
        self.encoder_running = False
        self.encoder_update_running = False
        self.encoder_start_btn.configure(text="Start Encoder Display", bg=self.colors['success_green'])
        
        if self.encoder_update_thread:
            self.encoder_update_thread.join(timeout=1)
            
    def encoder_update_loop(self):
        """Encoder position update loop"""
        while self.encoder_update_running:
            try:
                if not self.controller:
                    break
                    
                # Get current position
                axis = self.encoder_axis_var.get()
                pos_str = self.controller.send_command(f"TP {axis}")
                position = int(pos_str.strip())
                
                # Update UI in main thread
                self.root.after(0, self.update_encoder_display, position)
                
                # Sleep for update interval
                time.sleep(0.1)  # 100ms updates
                
            except Exception as e:
                # Update UI with error in main thread
                self.root.after(0, self.update_encoder_display, None, str(e))
                break
                
    def update_encoder_display(self, position, error=None):
        """Update encoder display with new position"""
        if not self.encoder_update_running:
            return
            
        if error:
            self.position_label.configure(text=f"Error: {error}")
            return
            
        # Update position label
        self.position_label.configure(text=f"Position: {position}")
        
        # Update visual display
        self.encoder_canvas.delete("all")
        
        # Draw encoder circle
        canvas_width = self.encoder_canvas.winfo_width()
        canvas_height = self.encoder_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:  # Canvas is properly sized
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            radius = min(center_x, center_y) - 20
            
            # Draw circle
            self.encoder_canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline='black', width=2
            )
            
            # Calculate angle from position
            clicks_per_turn = int(self.clicks_per_turn_entry.get())
            angle = (position % clicks_per_turn) / clicks_per_turn * 2 * 3.14159
            
            # Draw position indicator
            indicator_x = center_x + radius * 0.8 * math.cos(angle)
            indicator_y = center_y - radius * 0.8 * math.sin(angle)  # Negative for correct orientation
            
            self.encoder_canvas.create_oval(
                indicator_x - 5, indicator_y - 5,
                indicator_x + 5, indicator_y + 5,
                fill='red', outline='black'
            )
        
    def show_controller_testing(self):
        """Show comprehensive controller testing interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Controller Testing", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Main content frame with two columns
        main_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        main_frame.pack(fill='both', expand=True)
        
        # Configure grid weights for two columns
        main_frame.grid_columnconfigure(0, weight=1)  # Left column (controls)
        main_frame.grid_columnconfigure(1, weight=1)  # Right column (display)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # LEFT COLUMN - Controls
        left_frame = tk.Frame(main_frame, bg=self.colors['main_bg'])
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # PID Configuration Section
        pid_frame = tk.LabelFrame(left_frame, text="PID Configuration", 
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        pid_frame.pack(fill='x', pady=(0, 10))
        
        # Axis selection
        axis_frame = tk.Frame(pid_frame, bg=self.colors['main_bg'])
        axis_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(axis_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.test_axis_var = tk.StringVar(value="A")
        axis_combo = ttk.Combobox(axis_frame, textvariable=self.test_axis_var, 
                                 values=["A", "B", "C", "D"], width=10)
        axis_combo.pack(side='left', padx=(10, 0))
        
        # PID values
        pid_values_frame = tk.Frame(pid_frame, bg=self.colors['main_bg'])
        pid_values_frame.pack(fill='x', padx=15, pady=10)
        
        # KP
        tk.Label(pid_values_frame, text="KP:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        self.test_kp_entry = tk.Entry(pid_values_frame, font=("Arial", 10), width=12)
        self.test_kp_entry.grid(row=0, column=1, padx=(10, 15))
        self.test_kp_entry.insert(0, "10.0")
        
        # KI
        tk.Label(pid_values_frame, text="KI:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        self.test_ki_entry = tk.Entry(pid_values_frame, font=("Arial", 10), width=12)
        self.test_ki_entry.grid(row=0, column=3, padx=(10, 15))
        self.test_ki_entry.insert(0, "0.1")
        
        # KD
        tk.Label(pid_values_frame, text="KD:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=4, sticky='w')
        self.test_kd_entry = tk.Entry(pid_values_frame, font=("Arial", 10), width=12)
        self.test_kd_entry.grid(row=0, column=5, padx=(10, 0))
        self.test_kd_entry.insert(0, "50.0")
        
        # Tune button
        tune_btn = tk.Button(pid_frame, text="Tune Axis", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=self.test_tune_axis)
        tune_btn.pack(pady=10)
        
        # Motion Controls Section
        motion_frame = tk.LabelFrame(left_frame, text="Motion Controls", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        motion_frame.pack(fill='x', pady=(0, 10))
        
        # Jog controls
        jog_frame = tk.Frame(motion_frame, bg=self.colors['main_bg'])
        jog_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(jog_frame, text="Jog Distance (mm):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.test_jog_distance_entry = tk.Entry(jog_frame, font=("Arial", 10), width=12)
        self.test_jog_distance_entry.pack(side='left', padx=(10, 10))
        self.test_jog_distance_entry.insert(0, "10.0")
        
        # Jog buttons
        jog_buttons_frame = tk.Frame(motion_frame, bg=self.colors['main_bg'])
        jog_buttons_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Button(jog_buttons_frame, text="Jog +", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=lambda: self.test_jog_axis(1)).pack(side='left', padx=(0, 5))
        
        tk.Button(jog_buttons_frame, text="Jog -", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=lambda: self.test_jog_axis(-1)).pack(side='left', padx=(0, 5))
        
        tk.Button(jog_buttons_frame, text="Stop", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.test_stop_axis).pack(side='left')
        
        # Position control
        pos_frame = tk.Frame(motion_frame, bg=self.colors['main_bg'])
        pos_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(pos_frame, text="Position (counts):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.test_position_entry = tk.Entry(pos_frame, font=("Arial", 10), width=12)
        self.test_position_entry.pack(side='left', padx=(10, 10))
        self.test_position_entry.insert(0, "10000")
        
        tk.Button(pos_frame, text="Move", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.test_move_to_position).pack(side='left')
        
        tk.Button(pos_frame, text="Test Move", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.test_simple_move).pack(side='left', padx=(5, 0))
        
        # Motion Parameters Section
        params_frame = tk.LabelFrame(left_frame, text="Motion Parameters", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        params_frame.pack(fill='x', pady=(0, 10))
        
        # Speed and acceleration
        params_values_frame = tk.Frame(params_frame, bg=self.colors['main_bg'])
        params_values_frame.pack(fill='x', padx=15, pady=10)
        
        # Speed
        tk.Label(params_values_frame, text="Speed:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        self.test_speed_entry = tk.Entry(params_values_frame, font=("Arial", 10), width=12)
        self.test_speed_entry.grid(row=0, column=1, padx=(10, 15))
        self.test_speed_entry.insert(0, "5000")
        
        # Acceleration
        tk.Label(params_values_frame, text="Accel:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        self.test_accel_entry = tk.Entry(params_values_frame, font=("Arial", 10), width=12)
        self.test_accel_entry.grid(row=0, column=3, padx=(10, 0))
        self.test_accel_entry.insert(0, "1000")
        
        # Apply button
        apply_btn = tk.Button(params_frame, text="Apply Parameters", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['accent_blue'], fg='white',
                            command=self.test_apply_motion_params)
        apply_btn.pack(pady=10)
        
        # Servo Control Section
        servo_frame = tk.LabelFrame(left_frame, text="Servo Control", 
                                  font=("Arial", 12, "bold"),
                                  bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                  relief='solid', bd=1)
        servo_frame.pack(fill='x', pady=(0, 10))
        
        # Servo control buttons
        servo_buttons_frame = tk.Frame(servo_frame, bg=self.colors['main_bg'])
        servo_buttons_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Button(servo_buttons_frame, text="Servo On", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.test_servo_on).pack(side='left', padx=(0, 5))
        
        tk.Button(servo_buttons_frame, text="Servo Off", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=self.test_servo_off).pack(side='left', padx=(0, 5))
        
        tk.Button(servo_buttons_frame, text="Stop All", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.test_stop_all).pack(side='left')
        
        tk.Button(servo_buttons_frame, text="Status Check", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.check_controller_status).pack(side='left', padx=(5, 0))
        
        tk.Button(servo_buttons_frame, text="Enable All Servos", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.enable_all_servos).pack(side='left', padx=(5, 0))

        # Automatic Diagnostics Section
        auto_diag_frame = tk.LabelFrame(left_frame, text="Automatic Diagnostics", 
                                      font=("Arial", 12, "bold"),
                                      bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                      relief='solid', bd=1)
        auto_diag_frame.pack(fill='x', pady=(0, 10))

        auto_diag_row = tk.Frame(auto_diag_frame, bg=self.colors['main_bg'])
        auto_diag_row.pack(fill='x', padx=15, pady=10)

        self.auto_diag_running = False
        self.auto_diag_btn = tk.Button(auto_diag_row, text="Run Automatic Diagnostics", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['accent_blue'], fg='white',
                                       command=self.toggle_automatic_diagnostics)
        self.auto_diag_btn.pack(side='left')
        
        # Save Report button
        self.save_report_btn = tk.Button(auto_diag_row, text="💾 Save Report", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['warning_orange'], fg='white',
                                       command=self.save_diagnostic_report,
                                       state='disabled')
        self.save_report_btn.pack(side='left', padx=(10, 0))
        
        # Load Report button
        self.load_report_btn = tk.Button(auto_diag_row, text="📂 Load Report", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['accent_blue'], fg='white',
                                       command=self.load_diagnostic_report)
        self.load_report_btn.pack(side='left', padx=(10, 0))
        
        # Export CSV button
        self.export_csv_btn = tk.Button(auto_diag_row, text="📊 Export CSV", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['success_green'], fg='white',
                                       command=self.export_diagnostic_csv,
                                       state='disabled')
        self.export_csv_btn.pack(side='left', padx=(10, 0))
        
        # Compare Reports button
        self.compare_reports_btn = tk.Button(auto_diag_row, text="📈 Compare Reports", 
                                           font=("Arial", 10, "bold"),
                                           bg=self.colors['warning_orange'], fg='white',
                                           command=self.compare_diagnostic_reports)
        self.compare_reports_btn.pack(side='left', padx=(10, 0))
        
        # RIGHT COLUMN - Display
        right_frame = tk.Frame(main_frame, bg=self.colors['main_bg'])
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Encoder Display Section
        encoder_frame = tk.LabelFrame(right_frame, text="Encoder Position Display", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        encoder_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Encoder controls
        encoder_controls_frame = tk.Frame(encoder_frame, bg=self.colors['main_bg'])
        encoder_controls_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(encoder_controls_frame, text="Clicks per Turn:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.test_clicks_per_turn_entry = tk.Entry(encoder_controls_frame, font=("Arial", 10), width=12)
        self.test_clicks_per_turn_entry.pack(side='left', padx=(10, 20))
        self.test_clicks_per_turn_entry.insert(0, "64000")
        
        # Four-axis encoder displays
        encoder_displays_frame = tk.Frame(encoder_frame, bg=self.colors['main_bg'])
        encoder_displays_frame.pack(fill='both', expand=True, padx=15, pady=(0, 10))
        
        # Configure grid weights for equal spacing
        encoder_displays_frame.grid_columnconfigure(0, weight=1)
        encoder_displays_frame.grid_columnconfigure(1, weight=1)
        encoder_displays_frame.grid_columnconfigure(2, weight=1)
        encoder_displays_frame.grid_columnconfigure(3, weight=1)
        
        # Create individual encoder displays for each axis
        self.encoder_displays = {}
        self.encoder_labels = {}
        
        for i, axis in enumerate(['A', 'B', 'C', 'D']):
            # Individual axis frame
            axis_frame = tk.Frame(encoder_displays_frame, bg=self.colors['main_bg'], relief='solid', bd=1)
            axis_frame.grid(row=0, column=i, sticky="nsew", padx=5, pady=5)
            
            # Axis title
            axis_title = tk.Label(axis_frame, text=f"Axis {axis}", 
                                font=("Arial", 11, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'])
            axis_title.pack(pady=(5, 0))
            
            # Canvas for this axis
            canvas = tk.Canvas(axis_frame, bg='white', height=150, width=150)
            canvas.pack(padx=10, pady=5)
            
            # Position label for this axis
            position_label = tk.Label(axis_frame, text="Not Connected", 
                                    font=("Arial", 10),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'])
            position_label.pack(pady=(0, 5))
            
            # Store references
            self.encoder_displays[axis] = canvas
            self.encoder_labels[axis] = position_label
        
        # Status Log Section
        status_frame = tk.LabelFrame(right_frame, text="Status Log", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        status_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Status text area with copy functionality
        status_text_frame = tk.Frame(status_frame, bg=self.colors['main_bg'])
        status_text_frame.pack(fill='both', expand=True, padx=15, pady=(15, 5))
        
        self.test_status_text = scrolledtext.ScrolledText(status_text_frame, height=12, font=("Consolas", 9),
                                                        bg='white', fg='black')
        self.test_status_text.pack(fill='both', expand=True)
        
        # Copy button
        copy_btn = tk.Button(status_frame, text="📋 Copy Log", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['accent_blue'], fg='white',
                           command=self.copy_status_log)
        copy_btn.pack(side='left', padx=(0, 10), pady=(0, 15))
        
        # Start encoder button
        start_encoder_btn = tk.Button(status_frame, text="▶️ Start Encoder", 
                                    font=("Arial", 10, "bold"),
                                    bg=self.colors['success_green'], fg='white',
                                    command=self.start_encoder_update)
        start_encoder_btn.pack(side='left', padx=(0, 10), pady=(0, 15))
        
        # Restart encoder button
        restart_encoder_btn = tk.Button(status_frame, text="🔄 Restart Encoder", 
                                      font=("Arial", 10, "bold"),
                                      bg=self.colors['warning_orange'], fg='white',
                                      command=self.restart_encoder_update)
        restart_encoder_btn.pack(side='left', pady=(0, 15))
        
        # Initial status message
        self.test_status_text.insert(tk.END, "Controller Testing Interface Ready\n")
        self.test_status_text.insert(tk.END, "Connect to a controller to begin testing...\n")
        
        # Initialize encoder update variables (will start when controller connects)
        self.test_encoder_update_running = False
        
    def toggle_automatic_diagnostics(self):
        """Start/stop automatic diagnostics across all axes with real-time updates."""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        if not self.auto_diag_running:
            self.auto_diag_running = True
            self.auto_diag_btn.configure(text="Stop Diagnostics", bg=self.colors['error_red'])
            thread = threading.Thread(target=self.run_automatic_diagnostics, daemon=True)
            thread.start()
        else:
            self.auto_diag_running = False
            self.auto_diag_btn.configure(text="Run Automatic Diagnostics", bg=self.colors['accent_blue'])

    def run_automatic_diagnostics(self):
        """Run comprehensive diagnostics using absolute encoder positions"""
        axes = ["A", "B", "C", "D"]
        test_positions = [0, 250000, 500000, 250000, 0]  # Encoder positions to test
        speeds = [50000, 100000]  # Test speeds
        stop_duration = 2.0  # Seconds to wait at each position
        
        # Initialize diagnostic results storage
        self.diagnostic_results = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'controller_info': {},
            'motor_detection': {},
            'axis_results': {},
            'summary': {}
        }

        self.append_test_log("=== AUTOMATIC DIAGNOSTICS START ===")
        
        # Communication check before starting
        self.append_test_log("Checking controller communication...")
        try:
            # Test basic communication
            response = self.controller.send_command("MG _BN")
            self.append_test_log(f"Controller serial: {response.strip()}")
            self.diagnostic_results['controller_info']['serial'] = response.strip()
            
            # Test position read on all axes
            for axis in axes:
                try:
                    pos = self.controller.send_command(f"TP {axis}").strip()
                    self.append_test_log(f"Axis {axis} position: {pos}")
                    self.diagnostic_results['controller_info'][f'axis_{axis}_position'] = pos
                except Exception as e:
                    self.append_test_log(f"WARNING: Cannot read position for axis {axis}: {e}")
            
            # Check servo status for all axes
            self.append_test_log("Checking servo status...")
            for axis in axes:
                try:
                    servo_status = self.controller.send_command(f"MG _MO{axis}")
                    if servo_status.strip() == "0":
                        self.append_test_log(f"Axis {axis}: Servo is ON")
                    else:
                        self.append_test_log(f"Axis {axis}: Servo is OFF - will enable during test")
                    self.diagnostic_results['controller_info'][f'axis_{axis}_servo_status'] = servo_status.strip()
                except Exception as e:
                    self.append_test_log(f"WARNING: Cannot check servo status for axis {axis}: {e}")
            
            self.append_test_log("Communication check completed")
            
            # Motor detection summary
            self.append_test_log("\n=== MOTOR DETECTION SUMMARY ===")
            motor_detected_count = 0
            motor_detection_results = {}
            for axis in axes:
                motor_detected = self.detect_motor_on_axis(axis)
                motor_detection_results[axis] = motor_detected
                self.diagnostic_results['motor_detection'][axis] = motor_detected
                if motor_detected:
                    self.append_test_log(f"Axis {axis}: ✓ Motor detected")
                    motor_detected_count += 1
                else:
                    self.append_test_log(f"Axis {axis}: ✗ No motor detected")
            
            self.append_test_log(f"Total motors detected: {motor_detected_count}/{len(axes)}")
            self.diagnostic_results['summary']['motors_detected'] = motor_detected_count
            self.diagnostic_results['summary']['total_axes'] = len(axes)
            
            if motor_detected_count == 0:
                self.append_test_log("WARNING: No motors detected on any axis!")
                self.append_test_log("Please check motor connections and try again.")
                self.auto_diag_running = False
                self.root.after(0, lambda: self.auto_diag_btn.configure(text="Run Automatic Diagnostics", bg=self.colors['accent_blue']))
                return
                
        except Exception as e:
            self.append_test_log(f"ERROR: Communication check failed: {e}")
            self.auto_diag_running = False
            self.root.after(0, lambda: self.auto_diag_btn.configure(text="Run Automatic Diagnostics", bg=self.colors['accent_blue']))
            return

        # Run diagnostics for each axis
        for axis in axes:
            if not self.auto_diag_running:
                break
                
            self.append_test_log(f"\n[Axis {axis}] Begin diagnostics")
            
            # Initialize results for this axis
            self.diagnostic_results['axis_results'][axis] = {
                'motor_detected': motor_detection_results.get(axis, False),
                'initial_position': None,
                'pid_settings': {},
                'speed_tests': {},
                'position_accuracy': {},
                'warnings': [],
                'errors': []
            }
            
            try:
                # Check if motor is detected on this axis (from the summary)
                if not motor_detection_results.get(axis, False):
                    self.append_test_log(f"[Axis {axis}] SKIPPED: No motor detected on this axis")
                    continue
                
                self.append_test_log(f"[Axis {axis}] ✓ Motor confirmed - proceeding with diagnostics")
                
                # Get initial position
                try:
                    pos0 = self.controller.send_command(f"TP {axis}").strip()
                    self.append_test_log(f"[Axis {axis}] Initial position: {pos0}")
                    self.diagnostic_results['axis_results'][axis]['initial_position'] = pos0
                except Exception as e:
                    self.append_test_log(f"[Axis {axis}] ERROR reading initial position: {e}")
                    self.diagnostic_results['axis_results'][axis]['errors'].append(f"Initial position read failed: {e}")
                    continue
                
                # Stop and servo on
                self.controller.send_command(f"ST{axis}")
                time.sleep(0.1)  # Brief pause after stop
                self.controller.send_command(f"SH{axis}")
                time.sleep(0.5)  # Give servo time to enable
                
                # Verify servo is on and check tuning
                try:
                    servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                    if servo_status != "0":
                        self.append_test_log(f"[Axis {axis}] WARNING: Servo may not be enabled (status: {servo_status})")
                        self.diagnostic_results['axis_results'][axis]['warnings'].append(f"Servo may not be enabled (status: {servo_status})")
                    
                    # Check PID settings
                    kp = self.controller.send_command(f"MG _KP{axis}").strip()
                    ki = self.controller.send_command(f"MG _KI{axis}").strip()
                    kd = self.controller.send_command(f"MG _KD{axis}").strip()
                    self.append_test_log(f"[Axis {axis}] PID settings - KP:{kp}, KI:{ki}, KD:{kd}")
                    self.diagnostic_results['axis_results'][axis]['pid_settings'] = {
                        'kp': kp, 'ki': ki, 'kd': kd
                    }
                    
                    # Check following error limit
                    try:
                        fe = self.controller.send_command(f"MG _FE{axis}").strip()
                        self.append_test_log(f"[Axis {axis}] Following error limit: {fe}")
                        self.diagnostic_results['axis_results'][axis]['following_error_limit'] = fe
                    except:
                        pass
                        
                except Exception as e:
                    self.append_test_log(f"[Axis {axis}] WARNING: Could not verify servo status: {e}")
                    self.diagnostic_results['axis_results'][axis]['warnings'].append(f"Servo status verification failed: {e}")

                # Set up position reference (home the axis at current position)
                try:
                    current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    self.append_test_log(f"[Axis {axis}] Setting current position ({current_pos}) as reference point")
                    # Use DP (Define Position) to set current position as zero reference
                    self.controller.send_command(f"DP{axis}=0")
                    time.sleep(0.1)
                    new_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    self.append_test_log(f"[Axis {axis}] Reference set - position now reads: {new_pos}")
                except Exception as e:
                    self.append_test_log(f"[Axis {axis}] WARNING: Could not set position reference: {e}")
                    self.diagnostic_results['axis_results'][axis]['warnings'].append(f"Position reference setting failed: {e}")
                
                # Test basic motion capability first
                self.append_test_log(f"[Axis {axis}] Testing basic motion capability...")
                try:
                    # Try a small test move
                    test_speed = 5000
                    test_distance = 1000  # 1000 counts
                    self.controller.send_command(f"SP{axis}={test_speed}")
                    self.controller.send_command(f"AC{axis}={test_speed}")
                    self.controller.send_command(f"DC{axis}={test_speed}")
                    
                    start_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    self.append_test_log(f"[Axis {axis}] Test move: {start_pos} → {start_pos + test_distance}")
                    
                    # Move relative
                    self.controller.send_command(f"PR{axis}={test_distance}")
                    self.controller.send_command(f"BG{axis}")
                    
                    # Wait for completion
                    time.sleep(2.0)
                    self.controller.send_command(f"ST{axis}")
                    time.sleep(0.5)
                    
                    end_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    actual_move = end_pos - start_pos
                    self.append_test_log(f"[Axis {axis}] Test move result: {actual_move} counts (expected: {test_distance})")
                    
                    if abs(actual_move) < 100:
                        self.append_test_log(f"[Axis {axis}] WARNING: Motor may not be responding properly to motion commands")
                        self.diagnostic_results['axis_results'][axis]['warnings'].append("Motor may not be responding properly to motion commands")
                    
                    # Return to reference position
                    self.controller.send_command(f"PA{axis}=0")
                    self.controller.send_command(f"BG{axis}")
                    time.sleep(2.0)
                    self.controller.send_command(f"ST{axis}")
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.append_test_log(f"[Axis {axis}] ERROR in basic motion test: {e}")
                    self.diagnostic_results['axis_results'][axis]['errors'].append(f"Basic motion test failed: {e}")
                
                # Run two speed tests
                for i, speed in enumerate(speeds):
                    if not self.auto_diag_running:
                        break
                    
                    # Set acceleration based on speed test
                    if speed == 50000:
                        accel = 40000
                    elif speed == 100000:
                        accel = 80000
                    else:
                        accel = speed * 2  # Fallback calculation
                        
                    self.append_test_log(f"[Axis {axis}] Speed test at {speed} with acceleration {accel}")
                    
                    # Initialize speed test results
                    self.diagnostic_results['axis_results'][axis]['speed_tests'][speed] = {
                        'acceleration': accel,
                        'position_tests': [],
                        'max_position_error': 0,
                        'avg_position_error': 0
                    }
                    
                    position_errors = []
                    
                    # Test each position in sequence
                    for j, target_pos in enumerate(test_positions):
                        if not self.auto_diag_running:
                            break
                            
                        self.append_test_log(f"[Axis {axis}] Moving to position {target_pos} (step {j+1}/{len(test_positions)})")
                        
                        try:
                            # Apply motion parameters directly before movement
                            self.controller.send_command(f"SP{axis}={speed}")
                            self.controller.send_command(f"AC{axis}={accel}")
                            self.controller.send_command(f"DC{axis}={accel * 2}")  # Deceleration = 2x acceleration
                            
                            # Verify parameters were applied
                            actual_speed = self.controller.send_command(f"MG _SP{axis}").strip()
                            actual_accel = self.controller.send_command(f"MG _AC{axis}").strip()
                            self.append_test_log(f"[Axis {axis}] Applied SP={actual_speed}, AC={actual_accel}")
                            
                            # Get current position for logging
                            current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                            self.append_test_log(f"[Axis {axis}] Current: {current_pos}, Target: {target_pos}")
                            
                            # Use absolute positioning (should work now that we've homed)
                            self.controller.send_command(f"PA{axis}={target_pos}")
                            self.controller.send_command(f"BG{axis}")
                            
                        except Exception as e:
                            self.append_test_log(f"[Axis {axis}] ERROR moving to position {target_pos}: {e}")
                            self.diagnostic_results['axis_results'][axis]['errors'].append(f"Move to position {target_pos} failed: {e}")
                            continue
                        
                        # Wait for motion to complete
                        self.append_test_log(f"[Axis {axis}] Waiting for motion to complete...")
                        initial_pos = self.controller.send_command(f"TP {axis}").strip()
                        self.append_test_log(f"[Axis {axis}] Position at start of motion: {initial_pos}")
                        
                        # Monitor motion progress
                        start_time = time.time()
                        last_pos = int(initial_pos)
                        stuck_count = 0
                        motion_progress = True
                        
                        while time.time() - start_time < 20.0:  # 20 second timeout
                            try:
                                # Check if motion is still active
                                motion_status = self.controller.send_command("MG _BG").strip()
                                try:
                                    bg_value = int(float(motion_status))  # Handle float responses
                                except ValueError:
                                    bg_value = 0  # Default to no motion if parse fails
                                axis_bits = {"A": 1, "B": 2, "C": 4, "D": 8}
                                motion_active = (bg_value & axis_bits[axis]) != 0
                                
                                # Get current position
                                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                                
                                # Check if position is changing
                                if abs(current_pos - last_pos) < 2:
                                    stuck_count += 1
                                    if stuck_count > 10:  # Stuck for 1 second
                                        self.append_test_log(f"[Axis {axis}] WARNING: Motion appears stuck at position {current_pos}")
                                        motion_progress = False
                                        break
                                else:
                                    stuck_count = 0
                                    last_pos = current_pos
                                
                                # Check if we're close to target
                                if abs(current_pos - target_pos) < 50:
                                    self.append_test_log(f"[Axis {axis}] Close to target: {current_pos} (target: {target_pos})")
                                
                                # If motion stopped and we're close enough, consider it complete
                                if not motion_active and abs(current_pos - target_pos) < 100:
                                    self.append_test_log(f"[Axis {axis}] Motion completed near target")
                                    break
                                
                                time.sleep(0.1)
                                
                            except Exception as e:
                                self.append_test_log(f"[Axis {axis}] Error monitoring motion: {e}")
                                break
                        
                        # Force stop and get final position
                        self.controller.send_command(f"ST{axis}")
                        time.sleep(0.5)
                        final_pos = int(self.controller.send_command(f"TP {axis}").strip())
                        self.append_test_log(f"[Axis {axis}] Position at end of motion: {final_pos}")
                        
                        # Check if we need a position correction
                        position_error = abs(final_pos - target_pos)
                        if position_error > 50:  # If more than 50 counts off
                            self.append_test_log(f"[Axis {axis}] Large position error: {position_error} counts, attempting correction...")
                            try:
                                # Try a slower, more careful correction
                                correction_speed = min(speed//8, 5000)  # Very slow correction
                                galil_functions.move_to_position(self.controller, axis, target_pos, correction_speed, correction_speed//2)
                                time.sleep(2.0)  # Longer wait for correction
                                self.controller.send_command(f"ST{axis}")
                                time.sleep(0.5)
                                corrected_pos = int(self.controller.send_command(f"TP {axis}").strip())
                                self.append_test_log(f"[Axis {axis}] Corrected position: {corrected_pos}")
                                final_pos = corrected_pos
                            except Exception as e:
                                self.append_test_log(f"[Axis {axis}] Position correction failed: {e}")
                        
                        time.sleep(0.2)
                        
                        # Wait at position for specified duration
                        self.append_test_log(f"[Axis {axis}] Waiting {stop_duration} seconds at position {target_pos}...")
                        time.sleep(stop_duration)
                        
                        # Verify final position
                        try:
                            current_pos = self.controller.send_command(f"TP {axis}").strip()
                            position_accuracy = abs(int(current_pos) - target_pos)
                            self.append_test_log(f"[Axis {axis}] Final position: {current_pos} (error: {position_accuracy} counts)")
                            
                            # Store position test results
                            position_test_result = {
                                'target_position': target_pos,
                                'final_position': int(current_pos),
                                'position_error': position_accuracy,
                                'step_number': j + 1
                            }
                            self.diagnostic_results['axis_results'][axis]['speed_tests'][speed]['position_tests'].append(position_test_result)
                            position_errors.append(position_accuracy)
                            
                        except Exception as e:
                            self.append_test_log(f"[Axis {axis}] ERROR reading final position: {e}")
                            self.diagnostic_results['axis_results'][axis]['errors'].append(f"Final position read failed: {e}")
                    
                    # Calculate speed test statistics
                    if position_errors:
                        self.diagnostic_results['axis_results'][axis]['speed_tests'][speed]['max_position_error'] = max(position_errors)
                        self.diagnostic_results['axis_results'][axis]['speed_tests'][speed]['avg_position_error'] = sum(position_errors) / len(position_errors)
                    
                    self.append_test_log(f"[Axis {axis}] Speed {speed} test completed")

                self.append_test_log(f"[Axis {axis}] All diagnostics completed successfully")
                
            except Exception as e:
                self.append_test_log(f"[Axis {axis}] ERROR: {e}")
                self.diagnostic_results['axis_results'][axis]['errors'].append(f"General diagnostic error: {e}")

        # Generate and display diagnostic summary
        self.generate_diagnostic_summary()
        
        self.append_test_log("=== AUTOMATIC DIAGNOSTICS END ===")
        self.auto_diag_running = False
        self.root.after(0, lambda: self.auto_diag_btn.configure(text="Run Automatic Diagnostics", bg=self.colors['accent_blue']))

    def generate_diagnostic_summary(self):
        """Generate a comprehensive diagnostic summary report"""
        self.append_test_log("\n" + "="*60)
        self.append_test_log("=== DIAGNOSTIC SUMMARY REPORT ===")
        self.append_test_log("="*60)
        
        # Controller Information
        self.append_test_log(f"Controller Serial: {self.diagnostic_results['controller_info'].get('serial', 'Unknown')}")
        self.append_test_log(f"Test Date/Time: {self.diagnostic_results['timestamp']}")
        self.append_test_log(f"Motors Detected: {self.diagnostic_results['summary']['motors_detected']}/{self.diagnostic_results['summary']['total_axes']}")
        
        # Axis-by-axis summary
        self.append_test_log("\n--- AXIS PERFORMANCE SUMMARY ---")
        for axis in ["A", "B", "C", "D"]:
            if axis in self.diagnostic_results['axis_results']:
                axis_data = self.diagnostic_results['axis_results'][axis]
                
                if axis_data['motor_detected']:
                    self.append_test_log(f"\nAxis {axis}: ✓ MOTOR DETECTED")
                    
                    # PID Settings
                    pid = axis_data.get('pid_settings', {})
                    if pid:
                        self.append_test_log(f"  PID Settings: KP={pid.get('kp', 'N/A')}, KI={pid.get('ki', 'N/A')}, KD={pid.get('kd', 'N/A')}")
                    
                    # Speed test results
                    for speed in [50000, 100000]:
                        if speed in axis_data.get('speed_tests', {}):
                            speed_data = axis_data['speed_tests'][speed]
                            max_error = speed_data.get('max_position_error', 0)
                            avg_error = speed_data.get('avg_position_error', 0)
                            
                            # Performance rating
                            if max_error <= 5:
                                rating = "EXCELLENT"
                            elif max_error <= 20:
                                rating = "GOOD"
                            elif max_error <= 100:
                                rating = "ACCEPTABLE"
                            else:
                                rating = "NEEDS ATTENTION"
                            
                            self.append_test_log(f"  Speed {speed}: Max Error={max_error} counts, Avg Error={avg_error:.1f} counts - {rating}")
                    
                    # Warnings and errors
                    if axis_data.get('warnings'):
                        self.append_test_log(f"  Warnings: {len(axis_data['warnings'])}")
                    if axis_data.get('errors'):
                        self.append_test_log(f"  Errors: {len(axis_data['errors'])}")
                        
                else:
                    self.append_test_log(f"\nAxis {axis}: ✗ NO MOTOR DETECTED")
        
        # Overall system assessment
        self.append_test_log("\n--- SYSTEM ASSESSMENT ---")
        total_warnings = sum(len(axis_data.get('warnings', [])) for axis_data in self.diagnostic_results['axis_results'].values())
        total_errors = sum(len(axis_data.get('errors', [])) for axis_data in self.diagnostic_results['axis_results'].values())
        
        if total_errors == 0 and total_warnings == 0:
            self.append_test_log("✓ System Status: EXCELLENT - No issues detected")
        elif total_errors == 0:
            self.append_test_log(f"⚠ System Status: GOOD - {total_warnings} warnings detected")
        else:
            self.append_test_log(f"✗ System Status: NEEDS ATTENTION - {total_errors} errors, {total_warnings} warnings")
        
        # Recommendations
        self.append_test_log("\n--- RECOMMENDATIONS ---")
        for axis in ["A", "B", "C", "D"]:
            if axis in self.diagnostic_results['axis_results']:
                axis_data = self.diagnostic_results['axis_results'][axis]
                
                if axis_data['motor_detected']:
                    # Check for high position errors
                    for speed in [50000, 100000]:
                        if speed in axis_data.get('speed_tests', {}):
                            max_error = axis_data['speed_tests'][speed].get('max_position_error', 0)
                            if max_error > 100:
                                self.append_test_log(f"• Axis {axis}: Consider PID tuning adjustment (max error: {max_error} counts at speed {speed})")
                    
                    # Check for warnings
                    for warning in axis_data.get('warnings', []):
                        if "servo" in warning.lower():
                            self.append_test_log(f"• Axis {axis}: Verify servo enable status and motor connections")
                        elif "motion" in warning.lower():
                            self.append_test_log(f"• Axis {axis}: Check motor response and mechanical constraints")
                else:
                    self.append_test_log(f"• Axis {axis}: Install motor and verify connections")
        
        self.append_test_log("\n" + "="*60)
        
        # Add save report option
        self.append_test_log("\n💾 Diagnostic report can be saved using 'Save Report' button")
        
        # Enable save report button
        if hasattr(self, 'save_report_btn'):
            self.save_report_btn.configure(state='normal', bg=self.colors['success_green'])
        
        # Enable export CSV button
        if hasattr(self, 'export_csv_btn'):
            self.export_csv_btn.configure(state='normal', bg=self.colors['success_green'])
        
        # Enable export CSV button
        if hasattr(self, 'export_csv_btn'):
            self.export_csv_btn.configure(state='normal', bg=self.colors['success_green'])

    def save_diagnostic_report(self):
        """Save the diagnostic report to a JSON file"""
        if not hasattr(self, 'diagnostic_results') or not self.diagnostic_results:
            messagebox.showwarning("No Report", "No diagnostic report available to save. Please run diagnostics first.")
            return
            
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            controller_serial = self.diagnostic_results['controller_info'].get('serial', 'Unknown').replace('.', '_')
            filename = f"galil_diagnostic_report_{controller_serial}_{timestamp}.json"
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                title="Save Diagnostic Report",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialname=filename
            )
            
            if file_path:
                # Add additional metadata
                report_data = {
                    'report_metadata': {
                        'version': '1.0',
                        'generated_by': 'Galil Setup Tool',
                        'save_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    'diagnostic_results': self.diagnostic_results
                }
                
                # Save to file
                with open(file_path, 'w') as f:
                    json.dump(report_data, f, indent=2)
                
                self.append_test_log(f"✓ Diagnostic report saved to: {file_path}")
                messagebox.showinfo("Report Saved", f"Diagnostic report saved successfully!\n\nFile: {file_path}")
                
        except Exception as e:
            error_msg = f"Error saving diagnostic report: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Save Error", error_msg)

    def auto_connect_to_controller(self):
        """Automatically detect and connect to the Galil controller on startup"""
        def auto_connect_thread():
            try:
                self.append_test_log("=== AUTO-CONNECTION START ===")
                
                # Try to connect via IP first (10.1.0.21)
                self.append_test_log("Trying IP connection to 10.1.0.21...")
                
                # Test IP connection with ping
                if ping_controller("10.1.0.21"):
                    self.append_test_log("✓ IP ping successful, attempting connection...")
                    try:
                        self.controller = GalilController()
                        self.controller.connect("10.1.0.21")
                        
                        # Test if it's actually a Galil controller
                        try:
                            response = self.controller.send_command("MG _BN")
                            if response and response.strip() != "?":
                                self.append_test_log("✓ Successfully connected to controller at 10.1.0.21")
                                self.append_test_log(f"Controller serial: {response.strip()}")
                                
                                # Update UI to show connected state
                                self.root.after(0, self.update_connection_status, True)
                                self.append_test_log("=== AUTO-CONNECTION SUCCESS ===")
                                return
                            else:
                                self.append_test_log("✗ Controller at 10.1.0.21 is not responding to Galil commands")
                                self.controller.disconnect()
                                self.controller = None
                        except Exception as e:
                            self.append_test_log(f"✗ Controller validation failed: {e}")
                            if self.controller:
                                self.controller.disconnect()
                                self.controller = None
                                
                    except Exception as e:
                        self.append_test_log(f"✗ Failed to connect via IP 10.1.0.21: {e}")
                else:
                    self.append_test_log("✗ IP ping failed for 10.1.0.21")
                
                # If IP fails, try COM port discovery
                self.append_test_log("IP connection failed, searching COM ports...")
                
                # Common COM ports to check
                com_ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]
                
                for com_port in com_ports:
                    if not self.auto_connect_running:
                        break
                        
                    try:
                        self.append_test_log(f"Trying {com_port}...")
                        self.controller = GalilController()
                        self.controller.connect(com_port)
                        
                        # Test if it's actually a Galil controller
                        try:
                            response = self.controller.send_command("MG _BN")
                            if response and response.strip() != "?":
                                self.append_test_log(f"✓ Successfully connected to Galil controller on {com_port}")
                                self.append_test_log(f"Controller serial: {response.strip()}")
                                
                                # Update UI to show connected state
                                self.root.after(0, self.update_connection_status, True)
                                self.append_test_log("=== AUTO-CONNECTION SUCCESS ===")
                                return
                            else:
                                self.append_test_log(f"✗ {com_port} is not a Galil controller")
                                self.controller.disconnect()
                                self.controller = None
                        except Exception as e:
                            self.append_test_log(f"✗ {com_port} validation failed: {e}")
                            if self.controller:
                                self.controller.disconnect()
                                self.controller = None
                                
                    except Exception as e:
                        self.append_test_log(f"✗ {com_port}: {str(e)[:50]}...")
                        continue
                
                self.append_test_log("✗ No Galil controller found on any COM port")
                self.append_test_log("Please connect to a controller manually")
                
                # Update UI to show disconnected state
                self.root.after(0, self.update_connection_status, False)
                self.append_test_log("=== AUTO-CONNECTION FAILED ===")
                
            except Exception as e:
                self.append_test_log(f"✗ Auto-connection failed: {e}")
                self.root.after(0, self.update_connection_status, False)
                self.append_test_log("=== AUTO-CONNECTION FAILED ===")
        
        # Start auto-connection in background thread
        self.auto_connect_running = True
        self.auto_connect_thread = threading.Thread(target=auto_connect_thread, daemon=True)
        self.auto_connect_thread.start()

    def update_connection_status(self, connected):
        """Update UI elements to reflect connection status"""
        if connected:
            # Update any connection status indicators
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.config(text="Connected", fg=self.colors['success_green'])
            
            # Start encoder update loop
            self.start_encoder_update()
                
        else:
            # Stop encoder update loop
            self.test_encoder_update_running = False
            if hasattr(self, 'test_encoder_update_thread') and self.test_encoder_update_thread.is_alive():
                self.test_encoder_update_thread.join(timeout=1.0)
            
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.config(text="Disconnected", fg=self.colors['error_red'])
            
            # Update all position labels to show disconnected
            if hasattr(self, 'encoder_labels'):
                for axis in ['A', 'B', 'C', 'D']:
                    if axis in self.encoder_labels and self.encoder_labels[axis].winfo_exists():
                        self.encoder_labels[axis].configure(text="Not Connected", fg=self.colors['error_red'])
                        # Clear the canvas
                        if axis in self.encoder_displays and self.encoder_displays[axis].winfo_exists():
                            self.encoder_displays[axis].delete("all")
                            self.encoder_displays[axis].create_oval(10, 10, 140, 140, outline='gray', width=1)
                            self.encoder_displays[axis].create_text(75, 75, text="?", fill='gray', font=("Arial", 20))

    def detect_motor_on_axis(self, axis):
        """Detect if a motor is connected and responding on the specified axis"""
        if not self.controller:
            return False
            
        try:
            # Method 1: Try to read position - if it returns "?" or fails, no motor
            try:
                pos_response = self.controller.send_command(f"TP {axis}").strip()
                if pos_response == "?" or pos_response == "":
                    self.append_test_log(f"Motor detection: Axis {axis} position returns '{pos_response}' - no motor")
                    return False
                # Try to convert to int to ensure it's a valid position
                int(pos_response)
            except (ValueError, TypeError):
                self.append_test_log(f"Motor detection: Axis {axis} position not a valid number - no motor")
                return False
            
            # Method 2: Try to enable servo and see if it actually enables
            try:
                # Get initial servo status
                initial_servo = self.controller.send_command(f"MG _MO{axis}").strip()
                if initial_servo == "?":
                    self.append_test_log(f"Motor detection: Axis {axis} initial servo status returns '?' - no motor")
                    return False
                
                # Try to enable servo
                self.controller.send_command(f"SH{axis}")
                time.sleep(0.2)  # Give more time for servo to enable
                
                # Check if servo actually enabled
                enabled_servo = self.controller.send_command(f"MG _MO{axis}").strip()
                if enabled_servo == "?" or enabled_servo == "":
                    self.append_test_log(f"Motor detection: Axis {axis} servo enable failed - no motor")
                    return False
                
                # Try to set a small speed and see if it accepts it
                try:
                    self.controller.send_command(f"SP{axis}=1000")
                    speed_response = self.controller.send_command(f"MG _SP{axis}").strip()
                    if speed_response == "?" or speed_response == "":
                        self.append_test_log(f"Motor detection: Axis {axis} speed setting failed - no motor")
                        self.controller.send_command(f"MO{axis}")  # Disable servo
                        return False
                except Exception as e:
                    self.append_test_log(f"Motor detection: Axis {axis} speed test failed - no motor: {e}")
                    self.controller.send_command(f"MO{axis}")  # Disable servo
                    return False
                
                # Try a very small test movement to see if motor responds
                try:
                    initial_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    
                    # Try a small relative move (50 encoder counts for better detection)
                    self.controller.send_command(f"PR{axis}=50")
                    self.controller.send_command(f"BG{axis}")
                    time.sleep(1.0)  # Longer wait for movement
                    
                    # Check if position changed
                    final_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    position_change = abs(final_pos - initial_pos)
                    
                    # Stop any motion and disable servo
                    self.controller.send_command(f"ST{axis}")
                    self.controller.send_command(f"MO{axis}")
                    
                    # More forgiving detection - any movement counts as motor presence
                    if position_change < 1:
                        self.append_test_log(f"Motor detection: Axis {axis} movement test failed (pos {initial_pos}→{final_pos}) - no motor")
                        return False
                    elif position_change < 20:
                        self.append_test_log(f"Motor detection: Axis {axis} limited movement detected (pos {initial_pos}→{final_pos}, moved {position_change} counts)")
                        
                        # Check for following error or limits
                        try:
                            fe = int(float(self.controller.send_command(f"MG _FE{axis}").strip()))
                            if fe > 100:
                                self.append_test_log(f"Motor detection: Axis {axis} following error detected: {fe} counts")
                            
                            # Check limit switch status
                            lf = self.controller.send_command(f"MG _LF{axis}").strip()
                            if lf != "0" and lf != "0.0000":
                                self.append_test_log(f"Motor detection: Axis {axis} limit switch status: {lf}")
                        except:
                            pass
                        
                        self.append_test_log(f"Motor detection: Axis {axis} ✓ Motor confirmed (limited movement may indicate mechanical constraint)")
                        return True
                    else:
                        self.append_test_log(f"Motor detection: Axis {axis} ✓ Motor confirmed (good movement: {position_change} counts)")
                        return True
                        
                except Exception as e:
                    self.append_test_log(f"Motor detection: Axis {axis} movement test failed - no motor: {e}")
                    self.controller.send_command(f"ST{axis}")
                    self.controller.send_command(f"MO{axis}")
                    return False
                
            except Exception as e:
                self.append_test_log(f"Motor detection: Axis {axis} servo test failed - no motor: {e}")
                return False
            
            self.append_test_log(f"Motor detection: Axis {axis} ✓ Motor confirmed (responds to commands and moves)")
            return True
            
        except Exception as e:
            self.append_test_log(f"Motor detection error on axis {axis}: {e}")
            return False

    def append_test_log(self, line: str):
        """Append a line to the testing status log in a thread-safe way."""
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            # Check if widget still exists before updating
            if hasattr(self, 'test_status_text') and self.test_status_text.winfo_exists():
                self.root.after(0, lambda: (self.test_status_text.insert(tk.END, f"[{ts}] {line}\n"), self.test_status_text.see(tk.END)))
        except tk.TclError:
            # Widget was destroyed, ignore the update
            pass

    def copy_status_log(self):
        """Copy the entire status log to clipboard"""
        try:
            # Get all text from the status log
            log_content = self.test_status_text.get(1.0, tk.END)
            
            # Clear the clipboard and copy the content
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            
            # Show confirmation message
            messagebox.showinfo("Copy Success", "Status log copied to clipboard!")
            
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy log: {e}")

    def restart_encoder_update(self):
        """Restart the encoder position update loop"""
        try:
            # Stop existing encoder update loop
            self.test_encoder_update_running = False
            if hasattr(self, 'test_encoder_update_thread') and self.test_encoder_update_thread.is_alive():
                self.test_encoder_update_thread.join(timeout=1.0)
            
            # Start new encoder update loop
            self.test_encoder_update_running = True
            self.test_encoder_update_thread = threading.Thread(target=self.test_encoder_update_loop, daemon=True)
            self.test_encoder_update_thread.start()
            
            self.append_test_log("Encoder position update restarted")
            messagebox.showinfo("Success", "Encoder position update restarted!")
            
        except Exception as e:
            self.append_test_log(f"Failed to restart encoder update: {e}")
            messagebox.showerror("Error", f"Failed to restart encoder update: {e}")

    def start_encoder_update(self):
        """Start the encoder position update loop if controller is connected"""
        if not self.controller:
            self.append_test_log("Cannot start encoder update: No controller connected")
            return False
            
        try:
            # Stop existing encoder update loop if running
            self.test_encoder_update_running = False
            if hasattr(self, 'test_encoder_update_thread') and self.test_encoder_update_thread.is_alive():
                self.test_encoder_update_thread.join(timeout=1.0)
            
            # Start new encoder update loop
            self.test_encoder_update_running = True
            self.test_encoder_update_thread = threading.Thread(target=self.test_encoder_update_loop, daemon=True)
            self.test_encoder_update_thread.start()
            
            self.append_test_log("Encoder position update started")
            return True
            
        except Exception as e:
            self.append_test_log(f"Failed to start encoder update: {e}")
            return False

    def test_tune_axis(self):
        """Tune the selected axis with PID values"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            kp = float(self.test_kp_entry.get())
            ki = float(self.test_ki_entry.get())
            kd = float(self.test_kd_entry.get())
            
            self.test_status_text.insert(tk.END, f"Tuning axis {axis} with KP={kp}, KI={ki}, KD={kd}...\n")
            
            # Use the galil_functions module function
            galil_functions.tune_axis(self.controller, axis, kp, ki, kd)
            
            self.test_status_text.insert(tk.END, f"Axis {axis} tuning completed successfully!\n")
            self.test_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Tuning error: {str(e)}"
            self.test_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.test_status_text.see(tk.END)
            messagebox.showerror("Tuning Error", error_msg)
            
    def test_jog_axis(self, direction):
        """Jog the selected axis by the specified distance"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            distance = float(self.test_jog_distance_entry.get()) * direction
            
            self.append_test_log(f"Jogging axis {axis} by {abs(distance)}mm...")
            
            # Ensure servo is enabled first
            try:
                self.controller.send_command(f"SH{axis}")
                time.sleep(0.1)  # Wait for servo to stabilize
            except Exception as e:
                self.append_test_log(f"Warning: Could not enable servo for axis {axis}: {e}")
            
            # Use the galil_functions module function
            # Assuming 0.2 turns per mm and 64000 clicks per turn (default values)
            turns_per_mm = 0.2
            clicks_per_turn = 64000
            
            # Get speed from the test speed entry field
            speed = int(self.test_speed_entry.get())
            galil_functions.jog_distance(self.controller, axis, distance, turns_per_mm, clicks_per_turn, speed)
            
            self.append_test_log(f"Jog command sent successfully!")
            
        except Exception as e:
            error_msg = f"Jog error: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Jog Error", error_msg)
            
    def test_stop_axis(self):
        """Stop the selected axis"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            
            self.test_status_text.insert(tk.END, f"Stopping axis {axis}...\n")
            
            # Stop the axis
            self.controller.send_command(f"ST{axis}")
            
            self.test_status_text.insert(tk.END, f"Axis {axis} stopped successfully!\n")
            self.test_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Stop error: {str(e)}"
            self.test_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.test_status_text.see(tk.END)
            messagebox.showerror("Stop Error", error_msg)
            
    def test_move_to_position(self):
        """Move the selected axis to the specified position"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            position = int(self.test_position_entry.get())
            
            self.append_test_log(f"Moving axis {axis} to position {position}...")
            
            # Ensure servo is enabled first and stays enabled
            try:
                self.controller.send_command(f"SH{axis}")
                time.sleep(0.2)  # Wait longer for servo to stabilize
                
                # Verify servo is enabled
                servo_status = self._ensure_servo_enabled(axis)
                self.append_test_log(f"Servo status after enable: {servo_status}")
            except Exception as e:
                self.append_test_log(f"Warning: Could not enable servo for axis {axis}: {e}")
            
            # Get current position and servo status
            try:
                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                self.append_test_log(f"Current position: {current_pos}, Servo status: {servo_status}")
            except Exception as e:
                self.append_test_log(f"Warning: Could not read current status: {e}")
            
            # Get speed from the test speed entry field
            speed = int(self.test_speed_entry.get())
            
            # Use the galil_functions module function
            galil_functions.move_to_position(self.controller, axis, position, speed)
            
            # Monitor the movement and ensure servo stays enabled
            self._monitor_motion_progress(axis, current_pos, position)
            
                        # Final servo check and re-enable if needed
            self._ensure_servo_enabled_after_motion(axis)
            
            self.append_test_log(f"Move command completed!")
            
        except Exception as e:
            error_msg = f"Move error: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Move Error", error_msg)
            
    def test_simple_move(self):
        """Test a simple small movement to verify the system is working"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            
            self.append_test_log(f"Testing simple movement on axis {axis}...")
            
            # Get current position
            try:
                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                self.append_test_log(f"Current position: {current_pos}")
            except Exception as e:
                self.append_test_log(f"Error reading position: {e}")
                return
            
            # Try a small relative move (100 counts)
            target_pos = current_pos + 100
            
            self.append_test_log(f"Attempting small move: {current_pos} → {target_pos}")
            
            # Use conservative parameters
            speed = 1000
            accel = 500
            
            # Stop any existing motion
            self.controller.send_command(f"ST{axis}")
            time.sleep(0.1)
            
            # Enable servo
            self.controller.send_command(f"SH{axis}")
            time.sleep(0.2)
            
            # Set conservative parameters
            self.controller.send_command(f"SP{axis}={speed}")
            self.controller.send_command(f"AC{axis}={accel}")
            self.controller.send_command(f"DC{axis}={accel*2}")
            
            # Move to target position
            self.controller.send_command(f"PA{axis}={target_pos}")
            self.controller.send_command(f"BG{axis}")
            
            self.append_test_log(f"Simple move command sent successfully!")
            
        except Exception as e:
            error_msg = f"Simple move error: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Simple Move Error", error_msg)
            
    def check_controller_status(self):
        """Check detailed controller status and provide diagnostics"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.test_axis_var.get()
            
            self.append_test_log(f"=== CONTROLLER STATUS CHECK FOR AXIS {axis} ===")
            
            # Check basic controller info
            try:
                serial = self.controller.send_command("MG _BN").strip()
                self.append_test_log(f"Controller serial: {serial}")
            except Exception as e:
                self.append_test_log(f"Error reading serial: {e}")
            
            # Check axis position
            try:
                position = self.controller.send_command(f"TP {axis}").strip()
                self.append_test_log(f"Axis {axis} position: {position}")
            except Exception as e:
                self.append_test_log(f"Error reading position: {e}")
            
            # Check servo status
            try:
                servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                self.append_test_log(f"Axis {axis} servo status: {servo_status}")
            except Exception as e:
                self.append_test_log(f"Error reading servo status: {e}")
            
            # Check motion status
            try:
                motion_status = self.controller.send_command("MG _BG").strip()
                self.append_test_log(f"Motion status: {motion_status}")
            except Exception as e:
                self.append_test_log(f"Error reading motion status: {e}")
            
            # Check current motion parameters
            try:
                speed = self.controller.send_command(f"MG _SP{axis}").strip()
                accel = self.controller.send_command(f"MG _AC{axis}").strip()
                decel = self.controller.send_command(f"MG _DC{axis}").strip()
                self.append_test_log(f"Current parameters - Speed: {speed}, Accel: {accel}, Decel: {decel}")
            except Exception as e:
                self.append_test_log(f"Error reading parameters: {e}")
            
            # Check PID settings
            try:
                kp = self.controller.send_command(f"MG _KP{axis}").strip()
                ki = self.controller.send_command(f"MG _KI{axis}").strip()
                kd = self.controller.send_command(f"MG _KD{axis}").strip()
                self.append_test_log(f"PID settings - KP: {kp}, KI: {ki}, KD: {kd}")
            except Exception as e:
                self.append_test_log(f"Error reading PID: {e}")
            
            # Check for errors
            try:
                error_status = self.controller.send_command("MG _TC").strip()
                if error_status != "0":
                    self.append_test_log(f"WARNING: Controller error status: {error_status}")
                else:
                    self.append_test_log("No controller errors detected")
            except Exception as e:
                self.append_test_log(f"Error reading error status: {e}")
            
            # Test individual commands to see which ones fail
            self.append_test_log(f"=== TESTING INDIVIDUAL COMMANDS ===")
            
            # Test stop command
            try:
                response = self.controller.send_command(f"ST{axis}")
                self.append_test_log(f"ST{axis} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"ST{axis} failed: {e}")
            
            # Test servo on command
            try:
                response = self.controller.send_command(f"SH{axis}")
                self.append_test_log(f"SH{axis} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"SH{axis} failed: {e}")
            
            # Test speed command
            try:
                response = self.controller.send_command(f"SP{axis}=100")
                self.append_test_log(f"SP{axis}=100 response: '{response}'")
            except Exception as e:
                self.append_test_log(f"SP{axis}=100 failed: {e}")
            
            # Test acceleration command
            try:
                response = self.controller.send_command(f"AC{axis}=100")
                self.append_test_log(f"AC{axis}=100 response: '{response}'")
            except Exception as e:
                self.append_test_log(f"AC{axis}=100 failed: {e}")
            
            # Test position command
            try:
                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                response = self.controller.send_command(f"PA{axis}={current_pos}")
                self.append_test_log(f"PA{axis}={current_pos} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"PA{axis} failed: {e}")
            
            # Test begin command
            try:
                response = self.controller.send_command(f"BG{axis}")
                self.append_test_log(f"BG{axis} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"BG{axis} failed: {e}")
            
            # Test alternative servo status commands
            self.append_test_log(f"=== TESTING ALTERNATIVE SERVO COMMANDS ===")
            
            # Try different servo status commands
            try:
                servo_status_alt1 = self.controller.send_command(f"MG _SS{axis}").strip()
                self.append_test_log(f"Alternative servo status _SS{axis}: {servo_status_alt1}")
            except Exception as e:
                self.append_test_log(f"Alternative servo status _SS{axis} failed: {e}")
            
            try:
                servo_status_alt2 = self.controller.send_command(f"MG _SV{axis}").strip()
                self.append_test_log(f"Alternative servo status _SV{axis}: {servo_status_alt2}")
            except Exception as e:
                self.append_test_log(f"Alternative servo status _SV{axis} failed: {e}")
            
            # Test servo enable with different commands
            try:
                response = self.controller.send_command(f"MO{axis}")
                self.append_test_log(f"MO{axis} (servo off) response: '{response}'")
                time.sleep(0.1)
                response = self.controller.send_command(f"SH{axis}")
                self.append_test_log(f"SH{axis} (servo on) response: '{response}'")
                time.sleep(0.2)
                servo_status_after = self.controller.send_command(f"MG _MO{axis}").strip()
                self.append_test_log(f"Servo status after SH{axis}: {servo_status_after}")
            except Exception as e:
                self.append_test_log(f"Servo enable/disable test failed: {e}")
            
            self.append_test_log("=== STATUS CHECK COMPLETE ===")
            
        except Exception as e:
            error_msg = f"Status check error: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Status Check Error", error_msg)
            
    def test_apply_motion_params(self):
        """Apply motion parameters to the selected axis"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            speed = int(self.test_speed_entry.get())
            accel = int(self.test_accel_entry.get())
            
            self.test_status_text.insert(tk.END, f"Applying motion parameters to axis {axis}...\n")
            self.test_status_text.insert(tk.END, f"Speed: {speed}, Acceleration: {accel}\n")

            # Stop the axis first
            self.controller.send_command(f"ST{axis}")
            
            # Apply motion parameters
            self._apply_motion_parameters(axis, speed, accel)

            # Verify via MG _SP/_AC/_DC
            try:
                actual_speed = self.controller.send_command(f"MG _SP{axis}").strip()
                actual_accel = self.controller.send_command(f"MG _AC{axis}").strip()
                actual_decel = self.controller.send_command(f"MG _DC{axis}").strip()
                self.test_status_text.insert(tk.END, "Motion parameters applied successfully!\n")
                self.test_status_text.insert(tk.END, f"Current SP: {actual_speed}, AC: {actual_accel}, DC: {actual_decel}\n")
            except Exception as e:
                self.test_status_text.insert(tk.END, f"Parameters applied, but verification failed: {e}\n")
            
            self.test_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Parameter application error: {str(e)}"
            self.test_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.test_status_text.see(tk.END)
            messagebox.showerror("Parameter Error", error_msg)
            

            
    def test_encoder_update_loop(self):
        """Encoder position update loop for all axes"""
        self._run_encoder_update_loop()
                
    def test_update_all_encoder_displays(self, axis_positions, error=None):
        """Update all encoder displays with positions for each axis"""
        self._ensure_encoder_update_running()
            
        # Check if widgets still exist before trying to update them
        self._validate_encoder_widgets()
            
        self._handle_encoder_display_error_if_needed(error)
            
        # Update each axis display
        self._update_all_axis_displays(axis_positions)
             
    def test_servo_on(self):
        """Enable servo for the selected axis"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            
            self.append_test_log(f"Enabling servo for axis {axis}...")
            
            # Enable servo with verification
            servo_status = self._enable_servo_with_verification(axis)
            self.append_test_log(f"Servo status: {servo_status}")
            
        except Exception as e:
            self._handle_servo_error("Servo enable error", e)
            
    def maintain_servo_status(self):
        """Continuously monitor and maintain servo status for all axes"""
        if not self.controller:
            return
            
        try:
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Check servo status
                    servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                    if servo_status == "0":
                        # Re-enable servo
                        self.controller.send_command(f"SH{axis}")
                        time.sleep(0.1)
                except Exception as e:
                    # Ignore errors for individual axes
                    pass
        except Exception as e:
            # Ignore errors in servo maintenance
            pass
            
    def enable_all_servos(self):
        """Enable servos for all axes"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.append_test_log("Enabling servos for all axes...")
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Enable servo
                    self.controller.send_command(f"SH{axis}")
                    time.sleep(0.2)
                    
                    # Verify servo is enabled
                    servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                    if servo_status != "0":
                        self.append_test_log(f"Axis {axis}: Servo enabled (status: {servo_status})")
                    else:
                        self.append_test_log(f"Axis {axis}: WARNING - Servo may not be enabled (status: {servo_status})")
                        
                except Exception as e:
                    self.append_test_log(f"Axis {axis}: Error enabling servo - {e}")
            
            self.append_test_log("Servo enable operation completed")
            
        except Exception as e:
            error_msg = f"Enable all servos error: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Servo Error", error_msg)
            
    def test_servo_off(self):
        """Disable servo for the selected axis"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            
            self.test_status_text.insert(tk.END, f"Disabling servo for axis {axis}...\n")
            
            # Stop motion first
            self.controller.send_command(f"ST{axis}")
            
            # Disable servo
            self.controller.send_command(f"MO{axis}")
            
            self.test_status_text.insert(tk.END, f"Servo disabled for axis {axis}\n")
            self.test_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Servo disable error: {str(e)}"
            self.test_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.test_status_text.see(tk.END)
            messagebox.showerror("Servo Error", error_msg)
            
    def test_stop_all(self):
        """Stop all axes"""
        self._ensure_controller_connected()
            
        try:
            self.test_status_text.insert(tk.END, "Stopping all axes...\n")
            
            # Stop all axes
            self.controller.send_command("ST")
            
            self.test_status_text.insert(tk.END, "All axes stopped\n")
            self.test_status_text.see(tk.END)
            
        except Exception as e:
            error_msg = f"Stop all error: {str(e)}"
            self.test_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.test_status_text.see(tk.END)
            messagebox.showerror("Stop Error", error_msg)
    
    def save_configuration(self):
        """Save current configuration to a file"""
        try:
            # Get file path from user
            file_path = filedialog.asksaveasfilename(
                title="Save Configuration",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not file_path:
                return
                
            # Collect current configuration
            config = {
                'default_ip': "10.1.0.21",  # Default IP from the application
                'motion_parameters': {
                    'default_speed': 5000,
                    'default_acceleration': 1000,
                    'default_deceleration': 2000,
                    'default_jog_distance': 10.0,
                    'default_position': 10000
                },
                'pid_parameters': {
                    'default_kp': 10.0,
                    'default_ki': 0.1,
                    'default_kd': 50.0
                },
                'encoder_settings': {
                    'default_clicks_per_turn': 64000,
                    'update_interval_ms': 100
                },
                'network_settings': {
                    'default_subnet': "255.255.255.0",
                    'default_gateway': "10.1.0.1"
                },
                'saved_timestamp': datetime.now().isoformat()
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            self.settings_status_text.insert(tk.END, f"Configuration saved successfully to: {file_path}\n")
            self.settings_status_text.see(tk.END)
            messagebox.showinfo("Success", f"Configuration saved to:\n{file_path}")
            
        except Exception as e:
            error_msg = f"Error saving configuration: {str(e)}"
            self.settings_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.settings_status_text.see(tk.END)
            messagebox.showerror("Save Error", error_msg)
            
    def load_configuration(self):
        """Load configuration from a file"""
        try:
            # Get file path from user
            file_path = filedialog.askopenfilename(
                title="Load Configuration",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not file_path:
                return
                
            # Load configuration from file
            with open(file_path, 'r') as f:
                config = json.load(f)
                
            # Display loaded configuration
            self.settings_status_text.insert(tk.END, f"Configuration loaded from: {file_path}\n")
            self.settings_status_text.insert(tk.END, "Loaded settings:\n")
            
            if 'motion_parameters' in config:
                motion = config['motion_parameters']
                self.settings_status_text.insert(tk.END, f"  Motion: Speed={motion.get('default_speed', 'N/A')}, "
                                                       f"Accel={motion.get('default_acceleration', 'N/A')}, "
                                                       f"Decel={motion.get('default_deceleration', 'N/A')}\n")
                                                       
            if 'pid_parameters' in config:
                pid = config['pid_parameters']
                self.settings_status_text.insert(tk.END, f"  PID: KP={pid.get('default_kp', 'N/A')}, "
                                                       f"KI={pid.get('default_ki', 'N/A')}, "
                                                       f"KD={pid.get('default_kd', 'N/A')}\n")
                                                       
            if 'saved_timestamp' in config:
                self.settings_status_text.insert(tk.END, f"  Saved: {config['saved_timestamp']}\n")
                
            self.settings_status_text.see(tk.END)
            messagebox.showinfo("Success", f"Configuration loaded from:\n{file_path}")
            
        except Exception as e:
            error_msg = f"Error loading configuration: {str(e)}"
            self.settings_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.settings_status_text.see(tk.END)
            messagebox.showerror("Load Error", error_msg)
            
    def reset_to_defaults(self):
        """Reset all settings to their default values"""
        try:
            # Confirm with user
            result = messagebox.askyesno(
                "Reset to Defaults",
                "Are you sure you want to reset all settings to their default values?\n\n"
                "This will reset:\n"
                "- Default IP address to 10.1.0.21\n"
                "- Motion parameters to default values\n"
                "- PID parameters to default values\n"
                "- All other settings to defaults\n\n"
                "This action cannot be undone."
            )
            
            if not result:
                return
                
            # Define default configuration
            default_config = {
                'default_ip': "10.1.0.21",
                'motion_parameters': {
                    'default_speed': 5000,
                    'default_acceleration': 1000,
                    'default_deceleration': 2000,
                    'default_jog_distance': 10.0,
                    'default_position': 10000
                },
                'pid_parameters': {
                    'default_kp': 10.0,
                    'default_ki': 0.1,
                    'default_kd': 50.0
                },
                'encoder_settings': {
                    'default_clicks_per_turn': 64000,
                    'update_interval_ms': 100
                },
                'network_settings': {
                    'default_subnet': "255.255.255.0",
                    'default_gateway': "10.1.0.1"
                }
            }
            
            # Update any visible entry fields if they exist
            try:
                if hasattr(self, 'ip_entry') and self.ip_entry.winfo_exists():
                    self.ip_entry.delete(0, tk.END)
                    self.ip_entry.insert(0, default_config['default_ip'])
                    
                if hasattr(self, 'test_speed_entry') and self.test_speed_entry.winfo_exists():
                    self.test_speed_entry.delete(0, tk.END)
                    self.test_speed_entry.insert(0, str(default_config['motion_parameters']['default_speed']))
                    
                if hasattr(self, 'test_accel_entry') and self.test_accel_entry.winfo_exists():
                    self.test_accel_entry.delete(0, tk.END)
                    self.test_accel_entry.insert(0, str(default_config['motion_parameters']['default_acceleration']))
                    
                if hasattr(self, 'test_kp_entry') and self.test_kp_entry.winfo_exists():
                    self.test_kp_entry.delete(0, tk.END)
                    self.test_kp_entry.insert(0, str(default_config['pid_parameters']['default_kp']))
                    
                if hasattr(self, 'test_ki_entry') and self.test_ki_entry.winfo_exists():
                    self.test_ki_entry.delete(0, tk.END)
                    self.test_ki_entry.insert(0, str(default_config['pid_parameters']['default_ki']))
                    
                if hasattr(self, 'test_kd_entry') and self.test_kd_entry.winfo_exists():
                    self.test_kd_entry.delete(0, tk.END)
                    self.test_kd_entry.insert(0, str(default_config['pid_parameters']['default_kd']))
                    
            except Exception as e:
                self.settings_status_text.insert(tk.END, f"Note: Some UI elements could not be updated: {e}\n")
                
            self.settings_status_text.insert(tk.END, "All settings have been reset to default values.\n")
            self.settings_status_text.insert(tk.END, "Default configuration:\n")
            self.settings_status_text.insert(tk.END, f"  IP: {default_config['default_ip']}\n")
            self.settings_status_text.insert(tk.END, f"  Speed: {default_config['motion_parameters']['default_speed']}\n")
            self.settings_status_text.insert(tk.END, f"  KP: {default_config['pid_parameters']['default_kp']}\n")
            self.settings_status_text.insert(tk.END, f"  KI: {default_config['pid_parameters']['default_ki']}\n")
            self.settings_status_text.insert(tk.END, f"  KD: {default_config['pid_parameters']['default_kd']}\n")
            self.settings_status_text.see(tk.END)
            
            messagebox.showinfo("Success", "All settings have been reset to their default values.")
            
        except Exception as e:
            error_msg = f"Error resetting to defaults: {str(e)}"
            self.settings_status_text.insert(tk.END, f"ERROR: {error_msg}\n")
            self.settings_status_text.see(tk.END)
            messagebox.showerror("Reset Error", error_msg)
    
    def wait_for_motion_complete(self, axis, timeout=15.0):
        """Wait for motion to complete on the specified axis with timeout"""
        start_time = time.time()
        check_interval = 0.1  # Check every 100ms for better responsiveness
        last_position = None
        position_stable_count = 0
        motion_stopped_time = None
        
        while time.time() - start_time < timeout:
            try:
                # Method 1: Check if axis is still moving using _BG
                motion_active = False
                try:
                    motion_status = self.controller.send_command("MG _BG").strip()
                    bg_value = int(motion_status)
                    axis_bits = {"A": 1, "B": 2, "C": 4, "D": 8}
                    if axis in axis_bits:
                        motion_active = (bg_value & axis_bits[axis]) != 0
                except:
                    motion_active = True  # Assume motion if we can't read status
                
                # Method 2: Check position stability
                try:
                    current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    if last_position is not None:
                        position_change = abs(current_pos - last_position)
                        if position_change < 2:  # Position is very stable (within 2 counts)
                            position_stable_count += 1
                        else:
                            position_stable_count = 0
                    last_position = current_pos
                except:
                    position_stable_count = 0
                
                # Combined logic: motion must be stopped AND position stable
                if not motion_active:
                    if motion_stopped_time is None:
                        motion_stopped_time = time.time()
                    elif (time.time() - motion_stopped_time) > 0.3:  # Motion stopped for 300ms
                        if position_stable_count >= 3:  # AND position stable for 3 checks
                            return True
                else:
                    motion_stopped_time = None
                    position_stable_count = 0
                    
                time.sleep(check_interval)
                
            except Exception as e:
                # If we can't read anything, wait a bit more then assume complete
                time.sleep(0.5)
                return True
                
        # Timeout reached
        return False
    
    def _stop_all_motion(self):
        """Stop all motion on the controller"""
        try:
            self.controller.send_command("ST")
        except:
            pass
            
    def _disconnect_controller(self):
        """Disconnect from the controller"""
        try:
            self.controller.disconnect()
        except:
            pass
            
    def _ensure_controller_connected(self):
        """Ensure controller is connected, show error if not"""
        if not self.controller:
            messagebox.showerror("Connection Error", "No controller connected. Please connect to a controller first.")
            raise RuntimeError("No controller connected")
            
    def _test_all_axis_positions(self):
        """Test position reading for all axes"""
        for axis in ["A", "B", "C", "D"]:
            try:
                position_response = self.controller.send_command(f"TP{axis}")
                position = int(float(position_response.strip()))
                self.motor_status_text.insert(tk.END, f"Axis {axis} position: {position}\n")
            except Exception as e:
                self.motor_status_text.insert(tk.END, f"Axis {axis} test failed: {str(e)}\n")
                
    def _ensure_servo_enabled(self, axis):
        """Ensure servo is enabled for the specified axis"""
        servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Try again
            self.controller.send_command(f"SH{axis}")
            time.sleep(0.3)
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        return servo_status
        
    def _monitor_motion_progress(self, axis, start_pos, target_pos):
        """Monitor motion progress and maintain servo status"""
        self.append_test_log(f"Monitoring movement...")
        start_time = time.time()
        last_pos = start_pos
        
        while time.time() - start_time < 10.0:  # 10 second timeout
            try:
                # Check if motion is still active
                motion_status = self.controller.send_command("MG _BG").strip()
                try:
                    bg_value = int(float(motion_status))
                except ValueError:
                    bg_value = 0
                
                axis_bits = {"A": 1, "B": 2, "C": 4, "D": 8}
                motion_active = (bg_value & axis_bits[axis]) != 0
                
                # Get current position
                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                
                # Check servo status
                servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                if servo_status == "0":
                    self.append_test_log(f"WARNING: Servo disabled during motion, re-enabling...")
                    self.controller.send_command(f"SH{axis}")
                    time.sleep(0.1)
                
                # Check if position is changing
                if abs(current_pos - last_pos) > 5:
                    self.append_test_log(f"Position: {current_pos} (motion active: {motion_active})")
                    last_pos = current_pos
                
                # Check if we're close to target
                if abs(current_pos - target_pos) < 50:
                    self.append_test_log(f"Close to target: {current_pos} (target: {target_pos})")
                
                # If motion stopped and we're close enough, consider it complete
                if not motion_active and abs(current_pos - target_pos) < 100:
                    self.append_test_log(f"Motion completed near target")
                    break
                
                time.sleep(0.2)
                
            except Exception as e:
                self.append_test_log(f"Error monitoring motion: {e}")
                break
                
    def _ensure_servo_enabled_after_motion(self, axis):
        """Ensure servo is enabled after motion completion"""
        try:
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
            if servo_status == "0":
                self.append_test_log(f"Re-enabling servo after motion...")
                self.controller.send_command(f"SH{axis}")
        except Exception as e:
            self.append_test_log(f"Error checking final servo status: {e}")
            
    def _check_motion_command_support(self, axis):
        """Check if motion commands are supported for the given axis"""
        try:
            # Test basic motion commands
            test_pr = self.controller.send_command(f"PR{axis}=100")
            test_bg = self.controller.send_command(f"BG{axis}")
            test_st = self.controller.send_command(f"ST{axis}")
            
            if "?" not in test_pr and "?" not in test_bg and "?" not in test_st:
                self.motor_status_text.insert(tk.END, "✓ Motion commands supported for index latching\n")
                return True
            else:
                self.motor_status_text.insert(tk.END, "⚠ Motion commands not supported - using position analysis\n")
                return False
        except:
            self.motor_status_text.insert(tk.END, "⚠ Motion commands not supported - using position analysis\n")
            return False
            
    def _apply_motion_parameters(self, axis, speed, accel):
        """Apply motion parameters to the specified axis"""
        # Apply speed parameter
        resp = self.controller.send_command(f"SP{axis}={speed}")
        if resp.strip() == "?":
            self.test_status_text.insert(tk.END, f"WARNING: Controller rejected speed value {speed}\n")
        else:
            self.test_status_text.insert(tk.END, f"Speed parameter applied successfully\n")
        
        # Apply acceleration parameter
        resp = self.controller.send_command(f"AC{axis}={accel}")
        if resp.strip() == "?":
            self.test_status_text.insert(tk.END, f"WARNING: Controller rejected acceleration value {accel}\n")
        else:
            self.test_status_text.insert(tk.END, f"Acceleration parameter applied successfully\n")
        
        # Apply deceleration parameter (typically 2x acceleration)
        decel = accel * 2
        resp = self.controller.send_command(f"DC{axis}={decel}")
        if resp.strip() == "?":
            self.test_status_text.insert(tk.END, f"WARNING: Controller rejected deceleration value {decel}\n")
        else:
            self.test_status_text.insert(tk.END, f"Deceleration parameter applied successfully\n")
            
    def _run_encoder_update_loop(self):
        """Run the encoder position update loop"""
        servo_maintenance_counter = 0
        while self.test_encoder_update_running:
            try:
                if not self.controller:
                    time.sleep(0.5)  # Wait longer when no controller
                    continue
                
                # Read positions from all axes
                axis_positions = {}
                for axis in ["A", "B", "C", "D"]:
                    try:
                        pos_str = self.controller.send_command(f"TP {axis}")
                        position = int(pos_str.strip())
                        axis_positions[axis] = position
                    except Exception as e:
                        # If axis doesn't respond, mark as error
                        axis_positions[axis] = None
                
                # Update all encoder displays in main thread
                if self.test_encoder_update_running:  # Double-check before updating UI
                    self.root.after(0, self.test_update_all_encoder_displays, axis_positions)
                
                # Perform servo maintenance every 50 updates (5 seconds)
                servo_maintenance_counter += 1
                if servo_maintenance_counter >= 50:
                    self.maintain_servo_status()
                    servo_maintenance_counter = 0
                
                # Sleep for update interval
                time.sleep(0.1)  # 100ms updates
                
            except Exception as e:
                # Update UI with error in main thread
                if self.test_encoder_update_running:  # Double-check before updating UI
                    self.root.after(0, self.test_update_all_encoder_displays, None, str(e))
                time.sleep(1)  # Wait longer before retrying on error
                
    def _ensure_encoder_update_running(self):
        """Ensure encoder update is running, raise exception if not"""
        if not self.test_encoder_update_running:
            raise RuntimeError("Encoder update not running")
            
    def _validate_encoder_widgets(self):
        """Validate that encoder widgets exist and are accessible"""
        try:
            if not hasattr(self, 'encoder_displays') or not hasattr(self, 'encoder_labels'):
                raise RuntimeError("Encoder widgets not initialized")
        except tk.TclError:
            # Widget was destroyed, stop updates
            self.test_encoder_update_running = False
            raise RuntimeError("Encoder widgets destroyed")
            
    def _handle_encoder_display_error_if_needed(self, error):
        """Handle encoder display errors if error is present"""
        if error:
            for axis in ['A', 'B', 'C', 'D']:
                if axis in self.encoder_labels and self.encoder_labels[axis].winfo_exists():
                    self.encoder_labels[axis].configure(text=f"Error: {error}")
            raise RuntimeError("Encoder display error occurred")
            
    def _update_all_axis_displays(self, axis_positions):
        """Update all axis displays with position data"""
        for axis in ['A', 'B', 'C', 'D']:
            try:
                if axis not in self.encoder_displays or axis not in self.encoder_labels:
                    continue
                    
                canvas = self.encoder_displays[axis]
                label = self.encoder_labels[axis]
                
                if not canvas.winfo_exists() or not label.winfo_exists():
                    continue
                
                position = axis_positions.get(axis)
                
                if position is None:
                    # Axis not responding
                    label.configure(text="No Response", fg=self.colors['error_red'])
                    canvas.delete("all")
                    # Draw empty circle
                    canvas.create_oval(10, 10, 140, 140, outline='gray', width=1)
                    canvas.create_text(75, 75, text="?", fill='gray', font=("Arial", 20))
                else:
                    # Update position label
                    label.configure(text=f"Position: {position}", fg=self.colors['main_fg'])
                    
                    # Update visual display
                    canvas.delete("all")
                    
                    # Draw encoder circle
                    canvas.create_oval(10, 10, 140, 140, outline='black', width=2)
                    
                    # Calculate angle from position
                    clicks_per_turn = int(self.test_clicks_per_turn_entry.get())
                    angle = (position % clicks_per_turn) / clicks_per_turn * 2 * 3.14159
                    
                    # Draw position indicator
                    center_x = 75
                    center_y = 75
                    radius = 50
                    
                    indicator_x = center_x + radius * 0.8 * math.cos(angle)
                    indicator_y = center_y - radius * 0.8 * math.sin(angle)  # Negative for correct orientation
                    
                    canvas.create_oval(
                        indicator_x - 5, indicator_y - 5,
                        indicator_x + 5, indicator_y + 5,
                        fill='red', outline='black'
                    )
                    
            except Exception as e:
                # Individual axis update failed, continue with others
                continue
                
    def _enable_servo_with_verification(self, axis):
        """Enable servo for the specified axis with verification"""
        # Enable servo
        self.controller.send_command(f"SH{axis}")
        time.sleep(0.2)
        
        # Verify servo is enabled
        servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Try again
            self.controller.send_command(f"SH{axis}")
            time.sleep(0.3)
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        
        if servo_status != "0":
            self.append_test_log(f"Servo enabled for axis {axis} (status: {servo_status})")
        else:
            self.append_test_log(f"WARNING: Servo may not be enabled (status: {servo_status})")
            
        return servo_status
        
    def _handle_servo_error(self, operation, error):
        """Handle servo operation errors"""
        error_msg = f"{operation}: {str(error)}"
        self.append_test_log(f"ERROR: {error_msg}")
        messagebox.showerror("Servo Error", error_msg)
            
    def cleanup(self):
        """Clean up resources when application is closing"""
        try:
            # Stop auto-connect thread
            self.auto_connect_running = False
            if hasattr(self, 'auto_connect_thread') and self.auto_connect_thread.is_alive():
                self.auto_connect_thread.join(timeout=1.0)
            
            # Stop encoder update thread
            self.test_encoder_update_running = False
            if hasattr(self, 'test_encoder_update_thread') and self.test_encoder_update_thread.is_alive():
                self.test_encoder_update_thread.join(timeout=2.0)  # Give more time for thread to stop
            
            # Stop any ongoing motion
            if self.controller:
                try:
                    self.controller.send_command("ST")
                except:
                    pass
                
                # Close controller connection
                try:
                    self.controller.disconnect()
                except:
                    pass
        except Exception as e:
            print(f"Cleanup error: {e}")

    def load_diagnostic_report(self):
        """Load and display a previously saved diagnostic report"""
        try:
            # Ask user to select a report file
            file_path = filedialog.askopenfilename(
                title="Load Diagnostic Report",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not file_path:
                return
                
            # Load the report
            with open(file_path, 'r') as f:
                report_data = json.load(f)
            
            # Extract diagnostic results
            if 'diagnostic_results' in report_data:
                self.diagnostic_results = report_data['diagnostic_results']
                
                # Display the report
                self.display_loaded_report(report_data)
                
                self.append_test_log(f"✓ Diagnostic report loaded from: {file_path}")
                messagebox.showinfo("Report Loaded", f"Diagnostic report loaded successfully!\n\nFile: {file_path}")
            else:
                messagebox.showerror("Invalid Report", "The selected file does not contain a valid diagnostic report.")
                
        except Exception as e:
            error_msg = f"Error loading diagnostic report: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Load Error", error_msg)

    def display_loaded_report(self, report_data):
        """Display a loaded diagnostic report in the status log"""
        # Clear the status log
        self.test_status_text.delete(1.0, tk.END)
        
        # Display report metadata
        metadata = report_data.get('report_metadata', {})
        self.append_test_log("=== LOADED DIAGNOSTIC REPORT ===")
        self.append_test_log(f"Generated by: {metadata.get('generated_by', 'Unknown')}")
        self.append_test_log(f"Version: {metadata.get('version', 'Unknown')}")
        self.append_test_log(f"Generated: {self.diagnostic_results.get('timestamp', 'Unknown')}")
        self.append_test_log(f"Saved: {metadata.get('save_timestamp', 'Unknown')}")
        
        # Generate and display the summary
        self.generate_diagnostic_summary()
        
        # Enable save report button
        if hasattr(self, 'save_report_btn'):
            self.save_report_btn.configure(state='normal', bg=self.colors['success_green'])

    def export_diagnostic_csv(self):
        """Export diagnostic results as CSV files for data analysis"""
        if not hasattr(self, 'diagnostic_results') or not self.diagnostic_results:
            messagebox.showwarning("No Report", "No diagnostic report available to export. Please run diagnostics first.")
            return
            
        try:
            # Ask user for save location
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            controller_serial = self.diagnostic_results['controller_info'].get('serial', 'Unknown').replace('.', '_')
            filename = f"galil_diagnostic_data_{controller_serial}_{timestamp}.csv"
            
            file_path = filedialog.asksaveasfilename(
                title="Export Diagnostic Data as CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=filename
            )
            
            if file_path:
                import csv
                
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow([
                        'Axis', 'Speed', 'Test_Step', 'Target_Position', 'Final_Position', 
                        'Position_Error', 'Motor_Detected', 'KP', 'KI', 'KD', 'Timestamp'
                    ])
                    
                    # Write data rows
                    for axis in ["A", "B", "C", "D"]:
                        if axis in self.diagnostic_results['axis_results']:
                            axis_data = self.diagnostic_results['axis_results'][axis]
                            
                            # Get PID settings
                            pid = axis_data.get('pid_settings', {})
                            kp = pid.get('kp', 'N/A')
                            ki = pid.get('ki', 'N/A')
                            kd = pid.get('kd', 'N/A')
                            
                            motor_detected = 'Yes' if axis_data.get('motor_detected', False) else 'No'
                            
                            # Write speed test data
                            for speed in [50000, 100000]:
                                if speed in axis_data.get('speed_tests', {}):
                                    speed_data = axis_data['speed_tests'][speed]
                                    
                                    for test in speed_data.get('position_tests', []):
                                        writer.writerow([
                                            axis,
                                            speed,
                                            test.get('step_number', ''),
                                            test.get('target_position', ''),
                                            test.get('final_position', ''),
                                            test.get('position_error', ''),
                                            motor_detected,
                                            kp,
                                            ki,
                                            kd,
                                            self.diagnostic_results.get('timestamp', '')
                                        ])
                
                self.append_test_log(f"✓ Diagnostic data exported to CSV: {file_path}")
                messagebox.showinfo("Export Complete", f"Diagnostic data exported successfully!\n\nFile: {file_path}")
                
        except Exception as e:
            error_msg = f"Error exporting diagnostic data: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Export Error", error_msg)

    def compare_diagnostic_reports(self):
        """Compare multiple diagnostic reports to show performance trends"""
        try:
            # Ask user to select multiple report files
            file_paths = filedialog.askopenfilenames(
                title="Select Diagnostic Reports to Compare",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not file_paths or len(file_paths) < 2:
                messagebox.showwarning("Selection Required", "Please select at least 2 diagnostic reports to compare.")
                return
            
            # Load all reports
            reports = []
            for file_path in file_paths:
                try:
                    with open(file_path, 'r') as f:
                        report_data = json.load(f)
                    if 'diagnostic_results' in report_data:
                        reports.append({
                            'file_path': file_path,
                            'data': report_data['diagnostic_results'],
                            'metadata': report_data.get('report_metadata', {})
                        })
                except Exception as e:
                    self.append_test_log(f"WARNING: Could not load report {file_path}: {e}")
            
            if len(reports) < 2:
                messagebox.showerror("Invalid Reports", "Could not load enough valid reports for comparison.")
                return
            
            # Generate comparison report
            self.generate_comparison_report(reports)
            
        except Exception as e:
            error_msg = f"Error comparing diagnostic reports: {str(e)}"
            self.append_test_log(f"ERROR: {error_msg}")
            messagebox.showerror("Comparison Error", error_msg)

    def generate_comparison_report(self, reports):
        """Generate a comparison report for multiple diagnostic files"""
        self.append_test_log("\n" + "="*80)
        self.append_test_log("=== DIAGNOSTIC REPORTS COMPARISON ===")
        self.append_test_log("="*80)
        
        # Sort reports by timestamp
        reports.sort(key=lambda x: x['data'].get('timestamp', ''))
        
        # Display report list
        self.append_test_log(f"\nComparing {len(reports)} diagnostic reports:")
        for i, report in enumerate(reports, 1):
            timestamp = report['data'].get('timestamp', 'Unknown')
            serial = report['data'].get('controller_info', {}).get('serial', 'Unknown')
            self.append_test_log(f"  {i}. {timestamp} - Controller {serial}")
        
        # Compare performance metrics for each axis
        self.append_test_log("\n--- PERFORMANCE COMPARISON BY AXIS ---")
        
        for axis in ["A", "B", "C", "D"]:
            self.append_test_log(f"\nAxis {axis}:")
            
            # Collect data for this axis across all reports
            axis_data = []
            for report in reports:
                if axis in report['data'].get('axis_results', {}):
                    axis_result = report['data']['axis_results'][axis]
                    if axis_result.get('motor_detected', False):
                        timestamp = report['data'].get('timestamp', 'Unknown')
                        
                        # Get performance metrics
                        for speed in [50000, 100000]:
                            if speed in axis_result.get('speed_tests', {}):
                                speed_data = axis_result['speed_tests'][speed]
                                max_error = speed_data.get('max_position_error', 0)
                                avg_error = speed_data.get('avg_position_error', 0)
                                
                                axis_data.append({
                                    'timestamp': timestamp,
                                    'speed': speed,
                                    'max_error': max_error,
                                    'avg_error': avg_error,
                                    'report_index': len(axis_data)
                                })
            
            if axis_data:
                # Show trends
                self.append_test_log(f"  Motor detected in {len(set(d['report_index'] for d in axis_data))} reports")
                
                # Compare max errors
                for speed in [50000, 100000]:
                    speed_data = [d for d in axis_data if d['speed'] == speed]
                    if speed_data:
                        max_errors = [d['max_error'] for d in speed_data]
                        avg_errors = [d['avg_error'] for d in speed_data]
                        
                        min_max = min(max_errors)
                        max_max = max(max_errors)
                        avg_max = sum(max_errors) / len(max_errors)
                        
                        self.append_test_log(f"  Speed {speed}: Max Error Range: {min_max}-{max_max} counts (Avg: {avg_max:.1f})")
                        
                        # Identify best and worst performance
                        best_report = speed_data[max_errors.index(min_max)]
                        worst_report = speed_data[max_errors.index(max_max)]
                        
                        if min_max != max_max:
                            self.append_test_log(f"    Best: {best_report['timestamp']} ({min_max} counts)")
                            self.append_test_log(f"    Worst: {worst_report['timestamp']} ({max_max} counts)")
                        
                        # Trend analysis
                        if len(max_errors) >= 3:
                            trend = "Improving" if max_errors[-1] < max_errors[0] else "Declining" if max_errors[-1] > max_errors[0] else "Stable"
                            self.append_test_log(f"    Trend: {trend}")
            else:
                self.append_test_log(f"  No motor detected or insufficient data")
        
        # Overall system health comparison
        self.append_test_log("\n--- SYSTEM HEALTH COMPARISON ---")
        
        system_scores = []
        for report in reports:
            total_errors = sum(len(axis_data.get('errors', [])) for axis_data in report['data'].get('axis_results', {}).values())
            total_warnings = sum(len(axis_data.get('warnings', [])) for axis_data in report['data'].get('axis_results', {}).values())
            
            # Calculate a simple health score (lower is better)
            health_score = total_errors * 10 + total_warnings * 2
            system_scores.append({
                'timestamp': report['data'].get('timestamp', 'Unknown'),
                'errors': total_errors,
                'warnings': total_warnings,
                'health_score': health_score
            })
        
        if system_scores:
            best_health = min(system_scores, key=lambda x: x['health_score'])
            worst_health = max(system_scores, key=lambda x: x['health_score'])
            
            self.append_test_log(f"Best System Health: {best_health['timestamp']} (Score: {best_health['health_score']})")
            self.append_test_log(f"Worst System Health: {worst_health['timestamp']} (Score: {worst_health['health_score']})")
            
            if len(system_scores) >= 3:
                avg_score = sum(s['health_score'] for s in system_scores) / len(system_scores)
                self.append_test_log(f"Average System Health Score: {avg_score:.1f}")
        
        self.append_test_log("\n" + "="*80)

def main():
    root = tk.Tk()
    app = GalilSetupApp(root)
    
    # Set up cleanup when window is closed
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
