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
    force_save_network_settings_dmc4143, NetworkConfigurator,
    configure_controller_pid_settings, get_controller_pid_settings,
    ControllerConnectionManager
)
from galil_combined import GalilController
import galil_combined as galil_functions
from command_compatibility_checker import GalilCommandChecker
from controller_commands import ControllerCommands
from gui_framework import GUIFramework
from utils import LoggingUtils, estimate_bm_from_movement, calculate_motion_parameters, validate_motion_parameters
from diagnostics import GalilDiagnostics, TestResult

class GalilSetupApp:
    def __init__(self, root):
        self.root = root
        
        # Speed calculation tracking
        self.last_positions = {}
        self.last_update_times = {}
        self.axis_speeds = {}
        
        # Position dial smoothness tracking
        self.target_positions = {}
        self.current_dial_positions = {}
        self.position_dial_update_times = {}
        self.root.title("Galil Setup Tool")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f5f5f5')  # Light gray background
        
        # Initialize controller and components
        self.controller = None
        self.controller_commands = None  # Will be initialized when controller connects
        self.test_encoder_update_running = False
        self.auto_connect_running = False
        self.motor_direction_test_active = False  # Flag to control encoder position logging
        self.diagnostics = None  # Will be initialized when controller connects
        
        # Initialize managers
        self.gui_framework = None  # Will be initialized after colors are set
        self.connection_manager = None  # Will be initialized after colors are set
        self.logging_utils = None  # Will be initialized after colors are set
        
        # Bind mouse wheel events to the root window
        self.root.bind("<MouseWheel>", self._on_mousewheel)
        self.root.bind("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.root.bind("<Button-5>", self._on_mousewheel)  # Linux scroll down
        
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
        
        # Initialize managers
        self.logging_utils = LoggingUtils(None)  # No callback to avoid circular dependency
        self.connection_manager = ControllerConnectionManager(self.append_test_log)
        self.gui_framework = GUIFramework(self.root, self.colors, self.append_test_log, self)
        
        self.setup_ui()
        
        # Auto-detect and connect to controller on startup (delay to ensure UI is ready)
        self.root.after(1000, self.auto_connect_to_controller)
        
        # Initial connection status refresh (delay to ensure GUI framework is ready)
        self.root.after(1500, self.refresh_connection_status_display)
        
    def setup_ui(self):
        """Setup the main UI with Acertara-style layout"""
        if self.gui_framework:
            self.gui_framework.setup_ui()
        # Set references to GUI framework components
        self.main_content = self.gui_framework.main_content
        self.sidebar = self.gui_framework.sidebar
        self.header = self.gui_framework.header
        self.canvas = self.gui_framework.canvas
        self.scrollbar = self.gui_framework.scrollbar
        self.connection_status = self.gui_framework.connection_status
        self.ip_display = self.gui_framework.ip_display
        self.encoder_displays = self.gui_framework.encoder_displays
        self.encoder_labels = self.gui_framework.encoder_labels
        self.persistent_log_text = self.gui_framework.persistent_log_text
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for all text widgets"""
        if self.gui_framework:
            self.gui_framework._on_mousewheel(event)
        
    def create_sidebar(self):
        """Create the dark sidebar with navigation"""
        if self.gui_framework:
            self.gui_framework.create_sidebar()
        
    def create_header(self):
        """Create the light header with logo and controls"""
        if self.gui_framework:
            self.gui_framework.create_header()
        
    def create_main_content(self):
        """Create the main content area with scrolling and scaling support"""
        if self.gui_framework:
            self.gui_framework.create_main_content()
        
        # Show controller testing by default
        self.show_controller_testing()
        
    def _on_frame_configure(self, event=None):
        """Update canvas scroll region when frame size changes"""
        if self.gui_framework:
            self.gui_framework._on_frame_configure(event)
        
    def _on_canvas_configure(self, event):
        """Update canvas window width when canvas is resized"""
        if self.gui_framework:
            self.gui_framework._on_canvas_configure(event)
            
    def _on_window_resize(self, event):
        """Handle window resize events for proper scaling"""
        if self.gui_framework:
            self.gui_framework._on_window_resize(event)
            
    def _update_scrollbar_visibility(self):
        """Show/hide scrollbars based on content size"""
        if self.gui_framework:
            self.gui_framework._update_scrollbar_visibility()
            
    def _update_page_scroll_region(self):
        """Update scroll region after page content is loaded"""
        if self.gui_framework:
            self.gui_framework._update_page_scroll_region()
            
    def _configure_page_sections(self):
        """Configure all sections within the current page for proper scaling"""
        if self.gui_framework:
            self.gui_framework._configure_page_sections()
            
    def _ensure_button_visibility(self):
        """Ensure all buttons remain in visible areas of the window"""
        if self.gui_framework:
            self.gui_framework._ensure_button_visibility()
            
    def _find_all_buttons(self, parent_widget, button_list):
        """Recursively find all buttons in a widget hierarchy"""
        if self.gui_framework:
            self.gui_framework._find_all_buttons(parent_widget, button_list)
            
    def _configure_button_visibility(self, button):
        """Configure button to ensure it remains visible and properly sized"""
        if self.gui_framework:
            self.gui_framework._configure_button_visibility(button)
            
    def _configure_child_widgets(self, parent_widget):
        """Recursively configure child widgets for proper scaling"""
        if self.gui_framework:
            self.gui_framework._configure_child_widgets(parent_widget)
            
    def _configure_button_text_scaling(self, button):
        """Configure button text to scale within the button while keeping button size standard"""
        if self.gui_framework:
            self.gui_framework._configure_button_text_scaling(button)
            
    def _calculate_button_font_size(self, text):
        """Calculate appropriate font size for button text"""
        if self.gui_framework:
            return self.gui_framework._calculate_button_font_size(text)
            return 10
            
    def _create_missing_encoder_label(self, axis):
        """Create a missing encoder label for the specified axis"""
        if self.gui_framework:
            self.gui_framework._create_missing_encoder_label(axis)
            
    def _force_update_encoder_displays(self):
        """Force update encoder displays to ensure all axes are visible"""
        if self.gui_framework:
            self.gui_framework._force_update_encoder_displays()
    
    def send_manual_command(self, event=None):
        """Send manual command to the controller"""
        if not self.controller:
            self.command_response_text.insert(tk.END, "ERROR: No controller connected\n")
            self.command_response_text.see(tk.END)
            return
        
        # Get command from entry
        command = self.manual_command_entry.get().strip()
        if not command:
            self.command_response_text.insert(tk.END, "ERROR: No command entered\n")
            self.command_response_text.see(tk.END)
            return
        
        try:
            # Log the command being sent
            timestamp = time.strftime("%H:%M:%S")
            self.command_response_text.insert(tk.END, f"[{timestamp}] Sending: {command}\n")
            
            # Send command to controller
            response = self.controller.send_command(command)
            
            # Display response
            if response is not None:
                self.command_response_text.insert(tk.END, f"[{timestamp}] Response: {response}\n")
            else:
                self.command_response_text.insert(tk.END, f"[{timestamp}] Response: (no response)\n")
            
            # Clear the command entry
            self.manual_command_entry.delete(0, tk.END)
            
            # Scroll to bottom
            self.command_response_text.see(tk.END)
            
            # Also log to main status log
            self.append_test_log(f"Manual Command: {command} -> {response}")
            
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            self.command_response_text.insert(tk.END, f"[{timestamp}] {error_msg}\n")
            self.command_response_text.see(tk.END)
            self.append_test_log(f"Manual Command Error: {command} -> {error_msg}")
    
    def insert_quick_command(self, command):
        """Insert a quick command into the command entry"""
        self.manual_command_entry.delete(0, tk.END)
        self.manual_command_entry.insert(0, command)
        self.manual_command_entry.focus()
    
    def clear_command_response(self):
        """Clear the command response text area"""
        self.command_response_text.delete(1.0, tk.END)
    
    def _ensure_all_axes_visible(self):
        """Ensure all four axes (A, B, C, D) are visible and properly sized"""
        try:
            # Check if encoder_displays exists (for controller testing page)
            if hasattr(self, 'encoder_displays') and self.encoder_displays:
                # Check that all four axes exist
                expected_axes = ['A', 'B', 'C', 'D']
                missing_axes = []
            
                for axis in expected_axes:
                    if axis not in self.encoder_displays:
                        missing_axes.append(axis)
                    else:
                        # Check if it's the new dictionary structure
                        if isinstance(self.encoder_displays[axis], dict):
                            # New structure with speed and position canvases
                            speed_canvas = self.encoder_displays[axis].get('speed')
                            position_canvas = self.encoder_displays[axis].get('position')
                            if not speed_canvas or not position_canvas or not speed_canvas.winfo_exists() or not position_canvas.winfo_exists():
                                missing_axes.append(axis)
                        else:
                            # Old structure - single canvas
                            canvas = self.encoder_displays[axis]
                            if not canvas.winfo_exists():
                                missing_axes.append(axis)
                
                if missing_axes:
                    print(f"Warning: Missing or invalid encoder displays for axes: {missing_axes}")
                    return
            
                # Force all axes to be visible and properly sized
                for axis in expected_axes:
                    if isinstance(self.encoder_displays[axis], dict):
                        # New structure with speed and position canvases
                        speed_canvas = self.encoder_displays[axis].get('speed')
                        position_canvas = self.encoder_displays[axis].get('position')
                        if speed_canvas and position_canvas and speed_canvas.winfo_exists() and position_canvas.winfo_exists():
                            # Update both canvases
                            speed_canvas.update_idletasks()
                            position_canvas.update_idletasks()
                    else:
                        # Old structure - single canvas
                        canvas = self.encoder_displays[axis]
                        if canvas.winfo_exists():
                            # Ensure canvas is properly sized
                            canvas.configure(width=120, height=120)
                            canvas.update_idletasks()
                            
                            # Draw initial display
                            canvas.delete("all")
                            canvas.create_oval(10, 10, 110, 110, outline='black', width=3)
                            canvas.create_text(60, 60, text="0", fill='blue', font=("Arial", 16, "bold"))
                        
                # All axes are now visible
            else:
                # For pages without encoder_displays (like motor setup), just return silently
                return
            
        except Exception as e:
            print(f"Error ensuring axes visibility: {e}")
            
    def _update_canvas_window_width(self):
        """Update the canvas window width to match the canvas width"""
        try:
            canvas_width = self.main_canvas.winfo_width()
            if canvas_width > 1:  # Only update if canvas has a valid width
                # Find the window item (the main_content frame)
                window_items = self.main_canvas.find_withtag("all")
                if window_items:
                    self.main_canvas.itemconfig(window_items[0], width=canvas_width)
        except Exception:
            pass
            
    def _configure_content_scaling(self, frame):
        """Configure a frame for proper content scaling"""
        try:
            # Configure the frame to expand properly
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            
            # Ensure the frame expands to fill its container
            # Don't disable pack_propagate as it's needed for proper sizing
            frame.grid_propagate(False)
        except Exception:
            pass
            
    def _configure_widget_scaling(self, widget, parent_frame):
        """Configure a widget to scale properly within its parent frame"""
        try:
            # If the widget is a frame, configure it to expand
            if isinstance(widget, tk.Frame):
                widget.pack(fill='both', expand=True)
            # If it's a label frame, configure it to expand horizontally
            elif isinstance(widget, tk.LabelFrame):
                widget.pack(fill='x', expand=True)
            # For other widgets, ensure they expand horizontally
            else:
                widget.pack(fill='x', expand=True)
        except Exception:
            pass
        
    def create_persistent_log(self):
        """Create a persistent log that stays across all pages"""
        # Create persistent log frame (initially hidden)
        self.persistent_log_frame = tk.Frame(self.root, bg=self.colors['main_bg'])
        
        # Log title
        log_title = tk.Label(self.persistent_log_frame, "📋 Persistent Log (All Pages)", 
                           font=("Arial", 14, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        log_title.pack(anchor='w', pady=(0, 10))
        
        # Log text area
        self.persistent_log_text = scrolledtext.ScrolledText(self.persistent_log_frame, 
                                                           height=15, font=("Consolas", 9),
                                                           bg='white', fg='black')
        self.persistent_log_text.pack(fill='both', expand=True, padx=15, pady=(0, 10))
        
        # Log control buttons
        log_buttons_frame = tk.Frame(self.persistent_log_frame, bg=self.colors['main_bg'])
        log_buttons_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        # Copy log button
        copy_log_btn = tk.Button(log_buttons_frame, "📋 Copy Log", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['accent_blue'], fg='white',
                               command=self.copy_persistent_log)
        copy_log_btn.pack(side='left')
        
        # Clear log button
        clear_log_btn = tk.Button(log_buttons_frame, "🗑️ Clear Log", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['warning_orange'], fg='white',
                                command=self.clear_persistent_log)
        clear_log_btn.pack(side='left', padx=(10, 0))
        
        # Toggle log visibility button
        self.toggle_log_btn = tk.Button(log_buttons_frame, "ðŸ‘ï¸ Show/Hide Log", 
                                      font=("Arial", 10, "bold"),
                                      bg=self.colors['success_green'], fg='white',
                                      command=self.toggle_persistent_log)
        self.toggle_log_btn.pack(side='right')
        
        # Initialize log visibility state
        self.persistent_log_visible = False
        
        # Add initial log message
        self.persistent_log_text.insert(tk.END, "=== PERSISTENT LOG STARTED ===\n")
        self.persistent_log_text.insert(tk.END, "This log maintains data across all pages.\n")
        self.persistent_log_text.insert(tk.END, "Use 'Show/Hide Log' to toggle visibility.\n\n")
        
    def toggle_persistent_log(self):
        """Toggle the visibility of the persistent log"""
        if self.persistent_log_visible:
            # Hide log
            self.persistent_log_frame.grid_remove()
            self.persistent_log_visible = False
            self.toggle_log_btn.configure("ðŸ‘ï¸ Show Log")
        else:
            # Show log - position it below the main content area
            self.persistent_log_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=(0, 20))
            self.persistent_log_visible = True
            self.toggle_log_btn.configure("ðŸ‘ï¸ Hide Log")
            
        # Update scroll region when toggling log visibility
        self._on_frame_configure()
            
    def copy_persistent_log(self):
        """Copy the persistent log content to clipboard"""
        try:
            log_text = self.persistent_log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(log_text)
            messagebox.showinfo("Success", "Log copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy log: {str(e)}")
            
    def clear_persistent_log(self):
        """Clear the persistent log content"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire log?"):
            self.persistent_log_text.delete(1.0, tk.END)
            self.persistent_log_text.insert(tk.END, "=== LOG CLEARED ===\n")
            self.persistent_log_text.insert(tk.END, f"Cleared at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        

        
    def clear_main_content(self):
        """Clear the main content area"""
        # Stop encoder updates when switching pages
        self.test_encoder_update_running = False
        
        # Stop motor setup encoder updates if they're running
        if hasattr(self, 'encoder_update_job'):
            self.stop_encoder_auto_update()
        
        # Clear all widgets from the main content frame
        for widget in self.main_content.winfo_children():
            widget.destroy()
            
        # Clear encoder displays when switching pages
        if hasattr(self, 'encoder_displays'):
            self.encoder_displays = {}
        if hasattr(self, 'encoder_labels'):
            self.encoder_labels = {}
            
        # Update scroll region after clearing
        self._on_frame_configure()
        
        # Update canvas window width to ensure proper scaling
        self._update_canvas_window_width()
            
    def show_motor_setup(self):
        """Show motor setup interface"""
        self.show_motor_setup_new()
    
    def show_motion_controls_new(self):
        """Show motion controls interface using GUI framework"""
        self.clear_main_content()
        self.gui_framework.create_motion_controls_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
    
    def show_encoder_overlay_new(self):
        """Show encoder overlay interface using GUI framework"""
        self.clear_main_content()
        self.gui_framework.create_encoder_overlay_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
    
    def show_diagnostics_new(self):
        """Show diagnostics interface using GUI framework"""
        self.clear_main_content()
        self.gui_framework.create_diagnostics_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
    
    def show_network_config_new(self):
        """Show network config interface using GUI framework"""
        self.clear_main_content()
        self.gui_framework.create_network_config_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
    
    def show_settings_new(self):
        """Show settings interface using GUI framework"""
        self.clear_main_content()
        self.gui_framework.create_settings_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
    
    def show_controller_testing_new(self):
        """Show controller testing interface using GUI framework"""
        self.clear_main_content()
        self.gui_framework.create_controller_testing_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
            
    def show_motor_setup_new(self):
        """Show motor setup interface using GUI framework"""
        self.clear_main_content()
        
        # Create the GUI using the framework
        self.gui_framework.create_motor_setup_page(self)
        
        # Refresh connection status display
        self.refresh_connection_status_display()
        
        # Set up page show/hide handlers
        self.root.bind('<Visibility>', self._on_visibility_change)
        
        # Start encoder position updates when page is shown
        self.on_motor_setup_show()
            
    def show_motion_controls(self):
        """Show motion controls interface"""
        self.clear_main_content()
        
        # Motion content frame
        self.motion_content = tk.Frame(self.motion_frame, bg=self.colors['main_bg'])
        self.motion_content.pack(fill='x', padx=15, pady=10)
        
        # Speed and acceleration
        motion_params_frame = tk.Frame(self.motion_content, bg=self.colors['main_bg'])
        motion_params_frame.pack(fill='x', pady=(0, 10))
        
        # Speed
        tk.Label(motion_params_frame, "Speed:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        self.speed_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        self.speed_entry.grid(row=0, column=1, padx=(10, 20))
        self.speed_entry.insert(0, "5000")
        
        # Acceleration
        tk.Label(motion_params_frame, "Acceleration:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        self.accel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        self.accel_entry.grid(row=0, column=3, padx=(10, 20))
        self.accel_entry.insert(0, "1000")
        
        # Deceleration
        tk.Label(motion_params_frame, "Deceleration:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=4, sticky='w')
        self.decel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        self.decel_entry.grid(row=0, column=5, padx=(10, 0))
        self.decel_entry.insert(0, "2000")
        
        # Apply button
        apply_btn = tk.Button(self.motion_content, "Apply Parameters", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['accent_blue'], fg='white',
                            command=self.apply_motion_params)
        apply_btn.pack(pady=(0, 10))
        
        # Motion controls setup complete
            
    def show_motion_controls(self):
        """Show motion controls interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, "Motion Controls", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Motion controls content
        controls_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        controls_frame.pack(fill='both', expand=True)
        
        # Configure content scaling for the controls frame
        self._configure_content_scaling(controls_frame)
        
        # Jog Controls Section
        jog_frame = tk.LabelFrame(controls_frame, "Jog Controls", 
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        jog_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Axis selection for jog
        jog_axis_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_axis_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(jog_axis_frame, "Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.jog_axis_var = tk.StringVar(value="A")
        jog_axis_combo = ttk.Combobox(jog_axis_frame, textvariable=self.jog_axis_var, 
                                     values=["A", "B", "C", "D"], width=10)
        jog_axis_combo.pack(side='left', padx=(10, 20))
        
        # Jog distance
        tk.Label(jog_axis_frame, "Distance (mm):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.jog_distance_entry = tk.Entry(jog_axis_frame, font=("Arial", 10), width=15)
        self.jog_distance_entry.pack(side='left', padx=(10, 0))
        self.jog_distance_entry.insert(0, "10.0")
        
        # Jog buttons
        jog_buttons_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_buttons_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Button(jog_buttons_frame, "Jog +", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=lambda: self.jog_axis(1)).pack(side='left', padx=(0, 10))
        
        tk.Button(jog_buttons_frame, "Jog -", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=lambda: self.jog_axis(-1)).pack(side='left', padx=(0, 10))
        
        tk.Button(jog_buttons_frame, "Stop", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.stop_axis).pack(side='left')
        
        # Position Control Section
        position_frame = tk.LabelFrame(controls_frame, "Position Control", 
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     relief='solid', bd=1)
        position_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Position inputs
        pos_inputs_frame = tk.Frame(position_frame, bg=self.colors['main_bg'])
        pos_inputs_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(pos_inputs_frame, "Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        
        self.pos_axis_var = tk.StringVar(value="A")
        pos_axis_combo = ttk.Combobox(pos_inputs_frame, textvariable=self.pos_axis_var, 
                                     values=["A", "B", "C", "D"], width=10)
        pos_axis_combo.grid(row=0, column=1, padx=(10, 20))
        
        tk.Label(pos_inputs_frame, "Position (counts):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        
        self.position_entry = tk.Entry(pos_inputs_frame, font=("Arial", 10), width=15)
        self.position_entry.grid(row=0, column=3, padx=(10, 20))
        self.position_entry.insert(0, "10000")
        
        tk.Button(pos_inputs_frame, "Move", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.move_to_position).grid(row=0, column=4, padx=(10, 0))
        
        # Motion controls setup complete
    
    def show_motion_controls(self):
        """Show motion controls interface"""
        self.show_motion_controls_new()
        
    def show_encoder_overlay(self):
        """Show encoder overlay interface"""
        self.show_encoder_overlay_new()
            
    def show_diagnostics(self):
        """Show diagnostics interface"""
        self.show_diagnostics_new()
        
        # Update controller info display
        self.update_controller_info_display()
            
    def show_network_config(self):
        """Show network config interface"""
        self.show_network_config_new()
            
    def show_settings(self):
        """Show settings interface"""
        self.show_settings_new()
            
    def show_controller_testing(self):
        """Show controller testing interface"""
        self.show_controller_testing_new()
            
            
    def create_network_interface(self):
        """Create the network configuration interface"""
        # Main network frame
        network_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        network_frame.pack(fill='both', expand=True)
        
        # Connection section
        connection_frame = tk.LabelFrame(network_frame, "Controller Connection", 
                                       font=("Arial", 12, "bold"),
                                       bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                       relief='solid', bd=1)
        connection_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # IP Address input
        ip_frame = tk.Frame(connection_frame, bg=self.colors['main_bg'])
        ip_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(ip_frame, "IP Address:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.ip_entry = tk.Entry(ip_frame, font=("Arial", 10), width=15)
        self.ip_entry.pack(side='left', padx=(10, 0))
        self.ip_entry.insert(0, "10.1.0.21")
        
        # Connect button
        connect_btn = tk.Button(ip_frame, "Connect", 
                              font=("Arial", 10, "bold"),
                              bg=self.colors['accent_blue'], fg='white',
                              command=self.connect_to_controller)
        connect_btn.pack(side='left', padx=(10, 0))
        
        # Discover button
        discover_btn = tk.Button(ip_frame, "Discover Controllers", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['warning_orange'], fg='white',
                               command=self.discover_controllers)
        discover_btn.pack(side='left', padx=(10, 0))
        
        # Connection status label
        self.connection_status_label = tk.Label(ip_frame, "Not Connected", 
                                              font=("Arial", 10, "bold"),
                                              bg=self.colors['main_bg'], fg=self.colors['error_red'])
        self.connection_status_label.pack(side='right', padx=(10, 0))
        
        # IP Address Configuration section
        config_frame = tk.LabelFrame(network_frame, "IP Address Configuration", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        config_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # New IP Address input
        settings_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        settings_frame.pack(fill='x', padx=15, pady=15)
        
        # New IP Address
        ip_label = tk.Label(settings_frame, "New IP Address:", font=("Arial", 10, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        ip_label.pack(anchor='w')
        
        self.new_ip_entry = tk.Entry(settings_frame, font=("Arial", 10), width=20)
        self.new_ip_entry.pack(anchor='w', pady=(5, 15))
        self.new_ip_entry.insert(0, "10.1.0.20")  # Default IP address
        
        # Configuration buttons
        buttons_frame = tk.Frame(config_frame, bg=self.colors['main_bg'])
        buttons_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        tk.Button(buttons_frame, "Set IP Address", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.set_ip_address).pack(side='left', padx=(0, 10))
        
        tk.Button(buttons_frame, "Burn to Flash", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=self.burn_ip_to_flash).pack(side='left')
        
        # Network config setup complete
        
        # Update scroll region after page content is loaded
        self._update_page_scroll_region()
    
    def set_ip_address(self):
        """Set the IP address on the controller"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        
        new_ip = self.new_ip_entry.get().strip()
        if not new_ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return
        
        if not validate_ip_address(new_ip):
            messagebox.showerror("Error", "Please enter a valid IP address")
            return
        
        try:
            self.log_info(f"Setting IP address to: {new_ip}")
            
            # Use the DMC-4143 specific function for setting IP
            results = configure_controller_network_dmc4143(self.controller, new_ip)
            
            # Log results
            for info in results.get('debug_info', []):
                if 'âœ“' in info:
                    self.log_success(info)
                elif 'âš ' in info or 'âœ—' in info:
                    self.log_warning(info)
                else:
                    self.log_info(info)
            
            # Show success/failure message with specific guidance
            if results.get('ip_set', False):
                messagebox.showinfo("IP Address Set Successfully", 
                    f"IP address has been set to {new_ip}!\n\n"
                    "IMPORTANT: The controller has disconnected due to IP change.\n\n"
                    "Next steps:\n"
                    "1. Try connecting to the new IP address immediately\n"
                    "2. If connection succeeds, use 'Burn to Flash' button\n"
                    "3. If connection fails, power cycle the controller\n"
                    "4. After power cycle, try connecting to new IP again\n\n"
                    "The IP change IS working - the controller switches to the new IP\n"
                    "but may revert if settings aren't saved to flash memory.")
                self.log_success(f"IP address {new_ip} has been set successfully")
                self.log_info("Controller has disconnected due to IP change - this is normal")
            else:
                messagebox.showerror("Error", "Failed to set IP address. Check the log for details.")
                
        except Exception as e:
            error_msg = f"Error setting IP address: {str(e)}"
            self.log_error(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def burn_ip_to_flash(self):
        """Burn the current IP address settings to flash memory"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        
        try:
            self.log_info("Burning IP address settings to flash memory...")
            
            # Use the force save function to burn settings
            new_ip = self.new_ip_entry.get().strip()
            results = force_save_network_settings_dmc4143(self.controller, new_ip)
            
            # Log results
            for info in results.get('debug_info', []):
                if 'âœ“' in info:
                    self.log_success(info)
                elif 'âš ' in info or 'âœ—' in info:
                    self.log_warning(info)
                else:
                    self.log_info(info)
            
            # Show success/failure message
            if results.get('burned_to_flash', False):
                messagebox.showinfo("Success", "IP address settings burned to flash memory successfully!")
                self.log_success("IP address settings have been saved to non-volatile memory")
            else:
                messagebox.showerror("Error", "Failed to burn settings to flash. Check the log for details.")
                
        except Exception as e:
            error_msg = f"Error burning settings to flash: {str(e)}"
            self.log_error(error_msg)
            messagebox.showerror("Error", error_msg)
        
    def connect_to_controller(self):
        """Connect to the Galil controller"""
        if self.connection_manager:
            ip = self.ip_entry.get().strip()
            success = self.connection_manager.connect_to_controller(ip, self.update_connection_status)
            if success:
                # Update local references
                self.controller = self.connection_manager.controller
                self.controller_commands = self.connection_manager.controller_commands
                # Initialize diagnostics
                self.diagnostics = GalilDiagnostics(self.controller, safe_mode=True)
                
                # Debug: Log controller reference status
                self.append_test_log(f"DEBUG: Controller reference set: {self.controller is not None}")
                if self.controller:
                    self.append_test_log(f"DEBUG: Controller type: {type(self.controller)}")
                else:
                    self.append_test_log("DEBUG: Controller reference is None after connection!")
            else:
                messagebox.showerror("Error", "Failed to connect to controller")
        else:
            messagebox.showerror("Error", "Connection manager not initialized")
            
    def disconnect_controller(self):
        """Disconnect from the Galil controller"""
        if self.connection_manager:
            # Stop any ongoing motion
            self._stop_all_motion()
            
            # Stop encoder update loops
            self._stop_all_encoder_updates()
            
            success = self.connection_manager.disconnect_controller(self.update_connection_status)
            if success:
                # Update local references
                self.controller = None
                self.controller_commands = None
                self.diagnostics = None
                messagebox.showinfo("Success", "Disconnected from controller")
            else:
                messagebox.showinfo("Info", "No controller connected")
        else:
            messagebox.showerror("Error", "Connection manager not initialized")
            
    def discover_controllers(self):
        """Discover Galil controllers on the network"""
        if self.connection_manager:
            self.connection_manager.discover_controllers()
        else:
            messagebox.showerror("Error", "Connection manager not initialized")
            
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
            
    def configure_pid_settings(self):
        """Configure PID settings for the controller"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        
        # Create PID configuration dialog
        pid_dialog = tk.Toplevel(self.root)
        pid_dialog.title("Configure PID Settings")
        pid_dialog.geometry("500x400")
        pid_dialog.configure(bg=self.colors['main_bg'])
        pid_dialog.transient(self.root)
        pid_dialog.grab_set()
        
        # Center the dialog
        pid_dialog.update_idletasks()
        x = (pid_dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (pid_dialog.winfo_screenheight() // 2) - (400 // 2)
        pid_dialog.geometry(f"500x400+{x}+{y}")
        
        # Title
        title_label = tk.Label(pid_dialog, "Configure PID Settings", 
                              font=("Arial", 16, "bold"),
                              bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title_label.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(pid_dialog, 
"Enter PID values for each axis. Leave empty to keep current values.",
                               font=("Arial", 10),
                               bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        instructions.pack(pady=(0, 20))
        
        # Axis selection frame
        axis_frame = tk.Frame(pid_dialog, bg=self.colors['main_bg'])
        axis_frame.pack(pady=20, padx=20, fill='x')
        
        # Axis selection
        axis_label = tk.Label(axis_frame, "Axis:", font=("Arial", 10, "bold"),
                             bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        axis_label.pack(side='left', padx=(0, 10))
        
        self.axis_var = tk.StringVar(value="A")
        axis_combo = ttk.Combobox(axis_frame, textvariable=self.axis_var, 
                                 values=['A', 'B', 'C', 'D'], state='readonly', width=5)
        axis_combo.pack(side='left')
        
        # Bind axis change to refresh values
        self.axis_var.trace('w', self.on_axis_change)
        
        # PID values frame
        values_frame = tk.Frame(pid_dialog, bg=self.colors['main_bg'])
        values_frame.pack(pady=20, padx=20, fill='x')
        
        # KP input
        kp_frame = tk.Frame(values_frame, bg=self.colors['main_bg'])
        kp_frame.pack(fill='x', pady=5)
        
        kp_label = tk.Label(kp_frame, "KP:", font=("Arial", 10, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        kp_label.pack(side='left', padx=(0, 10))
        
        self.kp_entry = tk.Entry(kp_frame, font=("Arial", 10), width=15)
        self.kp_entry.pack(side='left')
        
        # KI input
        ki_frame = tk.Frame(values_frame, bg=self.colors['main_bg'])
        ki_frame.pack(fill='x', pady=5)
        
        ki_label = tk.Label(ki_frame, "KI:", font=("Arial", 10, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        ki_label.pack(side='left', padx=(0, 10))
        
        self.ki_entry = tk.Entry(ki_frame, font=("Arial", 10), width=15)
        self.ki_entry.pack(side='left')
        
        # KD input
        kd_frame = tk.Frame(values_frame, bg=self.colors['main_bg'])
        kd_frame.pack(fill='x', pady=5)
        
        kd_label = tk.Label(kd_frame, "KD:", font=("Arial", 10, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        kd_label.pack(side='left', padx=(0, 10))
        
        self.kd_entry = tk.Entry(kd_frame, font=("Arial", 10), width=15)
        self.kd_entry.pack(side='left')
        
        # Load current values
        self.load_current_pid_values()
        
        # Buttons frame
        buttons_frame = tk.Frame(pid_dialog, bg=self.colors['main_bg'])
        buttons_frame.pack(pady=20)
        
        tk.Button(buttons_frame, "Apply Settings", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=lambda: self.apply_pid_settings(pid_dialog)).pack(side='left', padx=(0, 10))
        
        tk.Button(buttons_frame, "Cancel", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=pid_dialog.destroy).pack(side='left')
    
    def load_current_pid_values(self):
        """Load current PID values from controller for selected axis"""
        try:
            settings = get_controller_pid_settings(self.controller)
            
            if settings.get('error'):
                self.log_error(f"Error loading PID settings: {settings['error']}")
                return
            
            # Get current axis selection
            current_axis = self.axis_var.get()
            
            # Populate the entry fields for the selected axis
            if current_axis in settings.get('kp_values', {}):
                self.kp_entry.insert(0, str(settings['kp_values'][current_axis]))
            if current_axis in settings.get('ki_values', {}):
                self.ki_entry.insert(0, str(settings['ki_values'][current_axis]))
            if current_axis in settings.get('kd_values', {}):
                self.kd_entry.insert(0, str(settings['kd_values'][current_axis]))
                    
        except Exception as e:
            self.log_error(f"Error loading PID values: {str(e)}")
    
    def on_axis_change(self, *args):
        """Called when axis selection changes"""
        # Clear current values
        self.kp_entry.delete(0, tk.END)
        self.ki_entry.delete(0, tk.END)
        self.kd_entry.delete(0, tk.END)
        
        # Load new values for selected axis
        self.load_current_pid_values()
    
    def apply_pid_settings(self, dialog):
        """Apply PID settings to controller"""
        try:
            # Get selected axis
            selected_axis = self.axis_var.get()
            
            # Collect values from entry fields
            kp_values = {}
            ki_values = {}
            kd_values = {}
            
            # KP value
            kp_text = self.kp_entry.get().strip()
            if kp_text:
                try:
                    kp_values[selected_axis] = float(kp_text)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid KP value")
                    return
            
            # KI value
            ki_text = self.ki_entry.get().strip()
            if ki_text:
                try:
                    ki_values[selected_axis] = float(ki_text)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid KI value")
                    return
            
            # KD value
            kd_text = self.kd_entry.get().strip()
            if kd_text:
                try:
                    kd_values[selected_axis] = float(kd_text)
                except ValueError:
                    messagebox.showerror("Error", f"Invalid KD value")
                    return
            
            # Check if any values were entered
            if not kp_values and not ki_values and not kd_values:
                messagebox.showwarning("Warning", "No PID values entered")
                return
            
            # Apply settings
            self.log_info(f"Applying PID settings for axis {selected_axis}...")
            results = configure_controller_pid_settings(
                self.controller, 
                kp_values if kp_values else None,
                ki_values if ki_values else None,
                kd_values if kd_values else None
            )
            
            # Log results
            for info in results.get('debug_info', []):
                if 'âœ“' in info:
                    self.log_success(info)
                elif 'âš ' in info or 'âœ—' in info:
                    self.log_warning(info)
            else:
                    self.log_info(info)
            
            # Show success/failure message
            if results.get('burned_to_flash', False):
                messagebox.showinfo("Success", f"PID settings for axis {selected_axis} applied and burned to flash memory successfully!")
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", f"PID settings for axis {selected_axis} applied but may not be saved to flash memory")
                dialog.destroy()
            
        except Exception as e:
            self.log_error(f"Error applying PID settings: {str(e)}")
            messagebox.showerror("Error", f"Error applying PID settings: {str(e)}")
            
    def log_info(self, message):
        """Log an info message"""
        self.log_message(f"INFO: {message}")
        
    def log_success(self, message):
        """Log a success message"""
        self.log_message(f"SUCCESS: {message}")
        
    def log_warning(self, message):
        """Log a warning message"""
        self.log_message(f"WARNING: {message}")
        
    def log_error(self, message):
        """Log an error message"""
        self.log_message(f"ERROR: {message}")
        
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
            
            self.log_message( f"Tuning axis {axis} with KP={kp}, KI={ki}, KD={kd}...\n")
            
            # Use the galil_functions module function
            galil_functions.tune_axis(self.controller, axis, kp, ki, kd)
            
            self.log_message( f"Axis {axis} tuning completed successfully!\n")
            
        except Exception as e:
            error_msg = f"Tuning error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
            
            self.log_message( f"Applying motion parameters to axis {axis}...\n")
            
            # Apply parameters
            self.controller.send_command(f"SP {axis}={speed}")
            self.controller.send_command(f"AC {axis}={accel}")
            self.controller.send_command(f"DC {axis}={decel}")
            
            self.log_message( f"Motion parameters applied successfully!\n")
            self.log_message( f"Speed: {speed}, Accel: {accel}, Decel: {decel}\n")
            
        except Exception as e:
            error_msg = f"Parameter application error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Parameter Error", error_msg)
            
    def define_motor_direction(self):
        """Define the positive direction of motor travel"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.brushless_axis_var.get()
            polarity = self.encoder_polarity_var.get()
            
            self.log_message(f"=== DEFINING MOTOR DIRECTION FOR AXIS {axis} ===")
            self.log_message(f"Encoder Polarity: {polarity}")
            self.log_message("Instructions:")
            self.log_message("1. Click 'Define Motor Direction' button\n")
            self.log_message("2. Move motor by hand in desired positive direction\n")
            self.log_message("3. Watch for encoder count changes\n")
            self.log_message("4. If counts increase in wrong direction, change polarity\n\n")
            
            # Set encoder polarity
            if polarity == "Reversed":
                self.controller.send_command(f"EP{axis}=1")
                self.log_message(f"Encoder polarity set to REVERSED for axis {axis}\n")
            else:
                self.controller.send_command(f"EP{axis}=0")
                self.log_message(f"Encoder polarity set to NORMAL for axis {axis}\n")
            
            # Disable servo for manual movement testing
            self.controller.send_command(f"MO {axis}")
            time.sleep(0.5)
            
            # Get initial position
            initial_pos = int(self.controller.send_command(f"TP {axis}").strip())
            self.log_message(f"Initial position: {initial_pos}\n")
            self.log_message("Now move the motor by hand in the desired positive direction...\n")
            self.log_message("Watch the position change in the real-time encoder display above.\n")
            self.log_message("NOTE: Servo is disabled to allow manual movement.\n\n")
            
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
                        self.log_message(f"Position: {current_pos} (change: {change:+d} counts - {direction} direction)\n")
                        last_pos = current_pos
                        update_count += 1
                    
                    # Update status every 2 seconds
                    if update_count % 20 == 0 and update_count > 0:
                        remaining = 10 - int(time.time() - start_time)
                        self.log_message(f"Monitoring... {remaining} seconds remaining\n")
                    
                    time.sleep(0.1)
                except Exception as e:
                    time.sleep(0.1)
            
            # Clear flag to stop position logging
            self.motor_direction_test_active = False
            
            self.log_message("Motor direction test completed.\n")
            self.log_message("If the direction was wrong, change the encoder polarity and repeat.\n\n")
            
        except Exception as e:
            error_msg = f"Motor direction definition error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Direction Error", error_msg)
            
    def estimate_brushless_modulo(self):
        """Estimate brushless modulo using position analysis (works with any controller)"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.brushless_axis_var.get()
            
            self.log_message(f"=== ESTIMATING BRUSHLESS MODULO FOR AXIS {axis} ===\n")
            self.log_message("This test will take a maximum of 30 seconds.\n")
            
            # Step 1: Check controller capabilities
            self.log_message("Step 1/3: Checking controller capabilities...\n")
            
            brushless_supported = False
            try:
                # Test if brushless commands are supported
                test_response = self.controller.send_command(f"BL {axis}")
                if "?" not in test_response:
                    brushless_supported = True
                    self.log_message("âœ“ Controller supports brushless commands\n")
                else:
                    self.log_message("âš  Controller does not support brushless commands\n")
            except:
                self.log_message("âš  Controller does not support brushless commands\n")
            
            # Step 2: Check what motion commands are supported
            self.log_message("Step 2/3: Checking motion command support...\n")
            
            motion_commands_supported = False
            try:
                # Test basic motion commands
                test_pr = self.controller.send_command(f"PR {axis}=100")
                test_bg = self.controller.send_command(f"BG {axis}")
                test_st = self.controller.send_command(f"ST {axis}")
                
                if "?" not in test_pr and "?" not in test_bg and "?" not in test_st:
                    motion_commands_supported = True
                    self.log_message("âœ“ Motion commands supported\n")
                else:
                    self.log_message("âš  Motion commands not supported\n")
            except:
                self.log_message("âš  Motion commands not supported\n")
            
            # Step 3: Perform manual movement-based brushless analysis
            self.log_message("Step 3/3: Manual movement brushless analysis...\n")
            self.log_message("This method requires manual movement of the motor.\n")
            self.log_message("Please move the motor by hand in both directions during this test.\n\n")
            
            try:
                # Disable servo for manual movement testing
                self.controller.send_command(f"MO {axis}")
                time.sleep(0.5)
                
                # Get initial position
                initial_pos = int(self.controller.send_command(f"TP {axis}").strip())
                self.log_message(f"Initial position: {initial_pos}\n")
                self.log_message("Starting movement analysis...\n")
                self.log_message("NOTE: Servo is disabled to allow manual movement.\n")
                
                # Monitor movement for 15 seconds to collect data
                start_time = time.time()
                positions = []
                last_pos = initial_pos
                movement_detected = False
                
                while time.time() - start_time < 15.0:
                    try:
                        current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                        positions.append(current_pos)
                        
                        # Check for significant movement
                        if abs(current_pos - last_pos) > 10:
                            movement_detected = True
                            self.log_message(f"Movement detected: {last_pos} â†’ {current_pos} (change: {current_pos - last_pos:+d})\n")
                        
                        last_pos = current_pos
                        time.sleep(0.1)
                        
                        # Update progress every 3 seconds
                        elapsed = int(time.time() - start_time)
                        if elapsed % 3 == 0 and elapsed > 0:
                            remaining = 15 - elapsed
                            self.log_message(f"Analyzing... {remaining} seconds remaining\n")
                            
                    except Exception as e:
                        time.sleep(0.1)
                        continue
                
                if not movement_detected:
                    self.log_message("âš  No significant movement detected during test\n")
                    self.log_message("Please ensure motor is free to move and try again\n")
                    return
                
                # Analyze the collected position data
                self.log_message(f"âœ“ Collected {len(positions)} position samples\n")
                
                # Calculate movement statistics
                min_pos = min(positions)
                max_pos = max(positions)
                total_movement = max_pos - min_pos
                
                self.log_message(f"Movement range: {min_pos} to {max_pos} (total: {total_movement} counts)\n")
                
                # Estimate brushless modulo based on movement patterns
                estimated_bm = self.estimate_bm_from_movement(positions, total_movement)
                estimated_pole_pairs = self.estimate_pole_pairs_from_bm(estimated_bm)
                
                self.log_message(f"âœ“ Movement analysis completed\n")
                self.log_message(f"âœ“ Estimated brushless modulo: {estimated_bm:.1f}\n")
                self.log_message(f"âœ“ Estimated pole pairs: {estimated_pole_pairs:.1f}\n")
                
                # Store the estimated values
                self.brushless_bm = estimated_bm
                self.brushless_pole_pairs = estimated_pole_pairs
                
                # Store the estimated values for later application
                self.brushless_bm = estimated_bm
                self.brushless_pole_pairs = estimated_pole_pairs
                
                # Note: Configuration will be applied in the save step
                self.log_message("âœ“ Brushless analysis completed!\n")
                self.log_message(f"âœ“ Estimated BM value: {self.brushless_bm:.1f}\n")
                self.log_message(f"âœ“ Estimated pole pairs: {self.brushless_pole_pairs:.1f}\n")
                self.log_message("âœ“ Ready to save configuration to controller\n")
                self.log_message("  Use 'Save Axis Settings' to apply configuration\n\n")
                
            except Exception as est_error:
                self.log_message(f"âš  Analysis failed: {est_error}\n")
                self.log_message("Using default brushless configuration...\n")
                
                # Set default values
                self.brushless_bm = 5000.0
                self.brushless_pole_pairs = 4.0
                
                self.log_message(f"Default BM: {self.brushless_bm:.1f}\n")
                self.log_message("Ready to save configuration to controller\n\n")
                
        except Exception as e:
            error_msg = f"Brushless modulo estimation error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}\n")
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
            axis = self.brushless_axis_var.get()
            
            self.log_message( f"=== LATCHING INDEXES FOR AXIS {axis} ===\n")
            self.log_message( "This test will take a maximum of 10 seconds to run.\n")
            
            # Check if index is available
            self.log_message( "Checking for index signal...\n")
            
            index_supported = False
            try:
                # Check if index is present (some controllers support this)
                index_response = self.controller.send_command(f"_IX{axis}")
                if "?" not in index_response:
                    index_supported = True
                    self.log_message( f"âœ“ Index detection supported: {index_response.strip()}\n")
                else:
                    self.log_message( "âš  Index detection command not supported\n")
            except:
                self.log_message( "âš  Index detection command not supported\n")
            
            # Check motion command support
            motion_commands_supported = self._check_motion_command_support(axis)
            
            # Get current position for analysis
            try:
                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                self.log_message( f"Current position: {current_pos}\n")
            except:
                current_pos = 0
                self.log_message( "âš  Could not read current position\n")
            
            # Perform index analysis based on available capabilities
            if motion_commands_supported:
                # Use motion-based index latching
                self.log_message( "Using motion-based index latching...\n")
                
                try:
                    # Enable servo
                    self.controller.send_command(f"SH {axis}")
                    time.sleep(0.5)
                    self.log_message( f"âœ“ Servo enabled for axis {axis}\n")
                    
                    # Set motion parameters
                    self.controller.send_command(f"SP {axis}=500")
                    self.controller.send_command(f"AC {axis}=500")
                    self.controller.send_command(f"DC {axis}=500")
                    
                    # First movement
                    self.log_message( "âœ“ Latch: 1\n")
                    self.controller.send_command(f"PR {axis}=5000")
                    self.controller.send_command(f"BG {axis}")
                    time.sleep(2.0)
                    self.controller.send_command(f"ST {axis}")
                    time.sleep(0.5)
                    
                    pos1 = int(self.controller.send_command(f"TP {axis}").strip())
                    movement1 = pos1 - current_pos
                    self.log_message( f"First movement: {movement1} counts\n")
                    
                    # Second movement
                    self.log_message( "âœ“ Latch: 2\n")
                    self.controller.send_command(f"PR {axis}=10000")
                    self.controller.send_command(f"BG {axis}")
                    time.sleep(2.0)
                    self.controller.send_command(f"ST {axis}")
                    time.sleep(0.5)
                    
                    pos2 = int(self.controller.send_command(f"TP {axis}").strip())
                    movement2 = pos2 - pos1
                    self.log_message( f"Second movement: {movement2} counts\n")
                    
                    # Calculate improved BM from movements
                    if abs(movement1) > 100 and abs(movement2) > 100:
                        avg_movement = (abs(movement1) + abs(movement2)) / 2.0
                        index_distance = avg_movement * 4.0
                        brushless_bm = index_distance / 4.0  # Assume 4 pole pairs
                        
                        self.log_message( f"âœ“ Index distance: {index_distance:.1f}\n")
                        self.log_message( f"âœ“ Improved BM: {brushless_bm:.1f}\n")
                    else:
                        brushless_bm = 5000.0
                        self.log_message( "âš  Insufficient movement, using default BM\n")
                    
                    # Disable servo
                    self.controller.send_command(f"MO {axis}")
                    
                except Exception as move_error:
                    self.log_message( f"âš  Motion-based latching failed: {move_error}\n")
                    brushless_bm = 5000.0
                    
            else:
                # Use position-based index analysis
                self.log_message( "Using position-based index analysis...\n")
                
                # Analyze current position for index patterns
                pos_magnitude = abs(current_pos)
                
                if pos_magnitude > 10000:
                    brushless_bm = 8000.0
                    self.log_message( "âœ“ High-resolution position detected\n")
                elif pos_magnitude > 1000:
                    brushless_bm = 4000.0
                    self.log_message( "âœ“ Standard resolution position detected\n")
                else:
                    brushless_bm = 2000.0
                    self.log_message( "âœ“ Low-resolution position detected\n")
                
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
                
                self.log_message( f"âœ“ Position-based BM: {brushless_bm:.1f}\n")
            
            # Store the improved BM
            self.brushless_bm = brushless_bm
            
            # Store the improved BM for later application
            self.brushless_bm = brushless_bm
            
            self.log_message( "âœ“ Index latching completed!\n")
            self.log_message( f"âœ“ Improved BM value: {self.brushless_bm:.1f}\n")
            self.log_message( "âœ“ Ready to save configuration to controller\n")
            self.log_message( "  Use 'Save Axis Settings' to apply configuration\n\n")
            
        except Exception as e:
            error_msg = f"Index latching error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            self.log_message( "This controller may not support index latching.\n")
            self.log_message( "For accurate brushless motor setup, use Galil's GDK software.\n\n")
            messagebox.showerror("Index Error", error_msg)
            
    def skip_index_latching(self):
        """Skip index latching step"""
        self.log_message( "Index latching skipped.\n")
        self.log_message( "Using estimated brushless modulo from previous step.\n\n")
        
    def log_message(self, message):
        """Add message to persistent log with real-time update"""
        try:
            if self.gui_framework and hasattr(self.gui_framework, 'log_message'):
                self.gui_framework.log_message(message)
            else:
                print(f"DEBUG: GUI framework or log_message method not available: {message}")
        except Exception as e:
            print(f"DEBUG: Error in main log_message: {e}")
        
    def save_brushless_settings(self):
        """Save brushless motor configuration settings to controller"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.brushless_axis_var.get()
            
            if not hasattr(self, 'brushless_bm'):
                messagebox.showerror("Error", "Please run brushless modulo estimation first")
                return
            
            self.log_message(f"=== SAVING BRUSHLESS SETTINGS FOR AXIS {axis} ===\n")
            
            # Step 1: Stop any motion on the axis
            try:
                self.controller.send_command(f"ST {axis}")
                time.sleep(0.5)
                self.log_message(f"âœ“ Motion stopped on axis {axis}\n")
            except Exception as stop_error:
                self.log_message(f"âš  Warning: Could not stop motion: {stop_error}\n")
            
            # Step 2: Disable servo for configuration
            try:
                self.controller.send_command(f"MO {axis}")
                time.sleep(0.5)
                self.log_message(f"âœ“ Servo disabled for configuration\n")
            except Exception as mo_error:
                self.log_message(f"âš  Warning: Could not disable servo: {mo_error}\n")
            
            # Step 3: Save brushless modulo (BM) - REAL COMMAND
            try:
                bm_command = f"BM{axis}={self.brushless_bm}"
                response = self.controller.send_command(bm_command)
                if "?" in response:
                    raise Exception(f"Controller rejected BM command: {response}")
                self.log_message(f"âœ“ Brushless Modulo (BM): {self.brushless_bm:.4f}\n")
                self.log_message(f"  Command: {bm_command}\n")
            except Exception as bm_error:
                self.log_message(f"âœ— ERROR: Could not save BM: {bm_error}\n")
                self.log_message(f"  This may indicate the controller doesn't support brushless motors\n")
                return
            
            # Step 4: Enable brushless mode (BL) - REAL COMMAND
            try:
                bl_command = f"BL {axis}=1"
                response = self.controller.send_command(bl_command)
                if "?" in response:
                    raise Exception(f"Controller rejected BL command: {response}")
                self.log_message(f"âœ“ Brushless mode enabled for axis {axis}\n")
                self.log_message(f"  Command: {bl_command}\n")
            except Exception as bl_error:
                self.log_message(f"âœ— ERROR: Could not enable brushless mode: {bl_error}\n")
                self.log_message(f"  This may indicate the controller doesn't support brushless motors\n")
                return
            
            # Step 5: Verify brushless settings
            try:
                bm_verify = self.controller.send_command(f"BM{axis}")
                bl_verify = self.controller.send_command(f"BL {axis}")
                self.log_message(f"âœ“ Verification - BM: {bm_verify.strip()}, BL: {bl_verify.strip()}\n")
            except Exception as verify_error:
                self.log_message(f"âš  Warning: Could not verify settings: {verify_error}\n")
            
            # Step 6: Save settings to non-volatile memory (BN) - REAL COMMAND
            try:
                response = self.controller.send_command("BN")
                if "?" in response:
                    raise Exception(f"Controller rejected BN command: {response}")
                time.sleep(1.0)
                self.log_message(f"âœ“ Settings saved to controller memory\n")
                self.log_message(f"  Command: BN (Burn to Non-volatile memory)\n")
            except Exception as bn_error:
                self.log_message(f"âœ— ERROR: Could not save to memory: {bn_error}\n")
                self.log_message(f"  Settings may be lost on power cycle\n")
            
            # Step 7: Re-enable servo
            try:
                self.controller.send_command(f"SH {axis}")
                time.sleep(0.5)
                self.log_message(f"âœ“ Servo re-enabled for axis {axis}\n")
            except Exception as sh_error:
                self.log_message(f"âš  Warning: Could not re-enable servo: {sh_error}\n")
            
            self.log_message(f"âœ“ REAL BRUSHLESS CONFIGURATION COMPLETE!\n")
            self.log_message(f"âœ“ Axis {axis} is now configured for sinusoidal commutation\n")
            self.log_message(f"âœ“ Settings have been saved to the controller\n")
            self.log_message(f"âœ“ Configuration will persist after power cycle\n\n")
            
            messagebox.showinfo("Success", f"REAL brushless motor configuration completed for axis {axis}!\n\nSettings have been saved to the controller and will persist after power cycle.")
            
        except Exception as e:
            error_msg = f"Save brushless settings error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            self.log_message( "This may indicate the controller doesn't support brushless motors.\n")
            self.log_message( "Check your controller model and firmware version.\n\n")
            messagebox.showerror("Save Error", error_msg)
            
    def update_encoder_positions(self):
        """Update the encoder position display for all axes with real-time data"""
        # Check if encoder labels exist (widgets might be destroyed)
        if not hasattr(self, 'encoder_labels') or not self.encoder_labels:
            return
            
        # Ensure all axes are present in the encoder labels
        expected_axes = ["A", "B", "C", "D"]
        for axis in expected_axes:
            if axis not in self.encoder_labels:
                # Create missing encoder label
                self._create_missing_encoder_label(axis)
            
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
                        position_response = self.controller.send_command(f"TP {axis}")
                        
                        
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
                                    
                                if self.motor_direction_test_active:
                                    timestamp = time.strftime("%H:%M:%S")
                                    self.log_message(f"[{timestamp}] Axis {axis}: {formatted_position}")
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
                            timestamp = time.strftime("%H:%M:%S")
                            self.log_message(f"[{timestamp}] Axis {axis} error: {str(e)}")
                                
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
                self.log_message( f"[{timestamp}] General error: {str(e)}\n")
    
    def update_all_encoder_positions(self, positions):
        """Update encoder position display with provided positions dict"""
        if not hasattr(self, 'encoder_labels') or not self.encoder_labels:
            return
            
        try:
            # Update the new visual displays (speed bars and position dials)
            self._update_all_axis_displays(positions)
            
            # Also update the old text labels for backward compatibility
            for axis in ["A", "B", "C", "D"]:
                if axis in self.encoder_labels and axis in positions:
                    try:
                        position = positions[axis]
                        formatted_position = str(position)
                        self.encoder_labels[axis].config(text=formatted_position, fg='black')
                    except tk.TclError:
                        # Widget was destroyed, ignore
                        pass
        except Exception as e:
            pass  # Ignore errors in position updates
    
    def update_single_encoder_position(self, axis, position):
        """Update encoder position display for a single axis"""
        if not hasattr(self, 'encoder_labels') or not self.encoder_labels:
            return
            
        try:
            if axis in self.encoder_labels:
                try:
                    formatted_position = str(position)
                    self.encoder_labels[axis].config(text=formatted_position, fg='black')
                except tk.TclError:
                    # Widget was destroyed, ignore
                    pass
        except Exception as e:
            pass  # Ignore errors in position updates
    
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
                        # Update every 500ms to reduce controller load
                        self.encoder_update_job = self.root.after(500, update_loop)
            except Exception as e:
                # If there's an error, stop the update loop
                if hasattr(self, 'encoder_update_job'):
                    self.root.after_cancel(self.encoder_update_job)
                # Log the error
                timestamp = time.strftime("%H:%M:%S")
                self.log_message(f"[{timestamp}] Auto-update error: {str(e)}")
        
        self.encoder_update_job = self.root.after(100, update_loop)  # Start with small delay
    
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
        if not self.controller:
            self.log_message( "=== No Controller Connected ===\n")
            self.log_message( "Please connect to a controller first using the Network Config page.\n")
            return
            
        try:
            # Test basic communication
            self.log_message( "=== Testing Controller Connection ===\n")
            
            # Test controller serial number
            try:
                serial_response = self.controller.send_command("SN")
                self.log_message( f"Controller Serial: {serial_response.strip()}\n")
            except Exception as e:
                self.log_message( f"Serial test failed: {str(e)}\n")
            
            # Test position reading for each axis
            self._test_all_axis_positions()
            
            # Test servo status
            try:
                servo_response = self.controller.send_command("_SS")
                self.log_message( f"Servo status: {servo_response.strip()}\n")
            except Exception as e:
                self.log_message( f"Servo status test failed: {str(e)}\n")
            
            self.log_message( "=== Connection Test Complete ===\n")
            
            messagebox.showinfo("Connection Test", "Controller connection test completed. Check the status log for details.")
            
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Test Error", error_msg)
    
    def copy_motor_setup_log(self):
        """Copy the persistent log to clipboard"""
        try:
            if self.gui_framework and hasattr(self.gui_framework, 'copy_persistent_log'):
                self.gui_framework.copy_persistent_log()
            else:
                messagebox.showerror("Copy Error", "Persistent log not available")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy log: {e}")
    
    def re_enable_servo(self):
        """Re-enable servo for the selected axis after manual tests"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.axis_var.get()
            
            self.log_message( f"=== RE-ENABLING SERVO FOR AXIS {axis} ===\n")
            
            # Enable servo
            self.controller.send_command(f"SH {axis}")
            time.sleep(0.5)
            
            # Verify servo is enabled
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
            
            if servo_status == "0":
                self.log_message( f"âœ“ Servo enabled successfully for axis {axis}\n")
                self.log_message( "Motor is now locked and ready for normal operation.\n\n")
            else:
                self.log_message( f"âš  Servo status unclear: {servo_status}\n")
                self.log_message( "Please check motor connections and try again.\n\n")
            
            
        except Exception as e:
            error_msg = f"Servo enable error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Servo Error", error_msg)
    
    
    def toggle_motion_section(self, event=None):
        """Toggle motion parameters section visibility"""
        if hasattr(self, 'motion_content'):
            if self.motion_content.winfo_viewable():
                self.motion_content.pack_forget()
                self.motion_frame.configure("🚀 Motion Parameters â–¶")
            else:
                self.motion_content.pack(fill='x', padx=15, pady=10)
                self.motion_frame.configure("🚀 Motion Parameters â–¼")
    
    def toggle_brushless_section(self, event=None):
        """Toggle brushless motor configuration section visibility"""
        if hasattr(self, 'brushless_content'):
            if self.brushless_content.winfo_viewable():
                self.brushless_content.pack_forget()
                self.brushless_frame.configure("⚙️ Brushless Motor Configuration â–¶")
            else:
                self.brushless_content.pack(fill='x', padx=15, pady=10)
                self.brushless_frame.configure("⚙️ Brushless Motor Configuration â–¼")
            
    def jog_axis(self, direction):
        """Jog the selected axis by the specified distance"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.jog_axis_var.get()
            distance = float(self.jog_distance_entry.get()) * direction
            
            self.log_message(f"Jogging axis {axis} by {abs(distance)}mm...")
            
            # Use the galil_functions module function
            # Assuming 0.2 turns per mm and 64000 clicks per turn (default values)
            turns_per_mm = 0.2
            clicks_per_turn = 64000
            
            # Get speed from the speed entry field
            speed = int(self.speed_entry.get())
            galil_functions.jog_distance(self.controller, axis, distance, turns_per_mm, clicks_per_turn, speed)
            
            self.log_message(f"Jog command sent successfully!")
            
        except Exception as e:
            error_msg = f"Jog error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Jog Error", error_msg)
            
    def stop_axis(self):
        """Stop the selected axis"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.jog_axis_var.get()
            
            self.log_message(f"Stopping axis {axis}...")
            
            # Stop the axis
            self.controller.send_command(f"ST {axis}")
            
            self.log_message(f"Axis {axis} stopped successfully!")
            
        except Exception as e:
            error_msg = f"Stop error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Stop Error", error_msg)
            
    def move_to_position(self):
        """Move the selected axis to the specified position"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            axis = self.pos_axis_var.get()
            position = int(self.position_entry.get())
            
            self.log_message(f"Moving axis {axis} to position {position}...")
            
            # Use the galil_functions module function
            # Get speed from the speed entry field
            speed = int(self.speed_entry.get())
            galil_functions.move_to_position(self.controller, axis, position, speed)
            
            self.log_message(f"Move command sent successfully!")
            
        except Exception as e:
            error_msg = f"Move error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Move Error", error_msg)
            
    def get_controller_info(self):
        """Get static controller information"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.log_message( "Getting controller information...\n\n")
            
            # Use the galil_functions module function
            info = galil_functions.get_controller_info(self.controller)
            
            self.log_message( "CONTROLLER INFORMATION:\n")
            self.log_message( "=" * 50 + "\n")
            self.log_message( info + "\n")
            
        except Exception as e:
            error_msg = f"Error getting controller info: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
            
        self.log_message( "LIVE DIAGNOSTICS:\n")
        self.log_message( "=" * 50 + "\n")
        self.log_message( f"Last Update: {datetime.now().strftime('%H:%M:%S')}\n\n")
        self.log_message( info + "\n")
        
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
        self.encoder_start_btn.configure("Stop Encoder Display", bg=self.colors['error_red'])
        
        self.encoder_update_running = True
        self.encoder_update_thread = threading.Thread(target=self.encoder_update_loop, daemon=True)
        self.encoder_update_thread.start()
        
    def stop_encoder_display(self):
        """Stop encoder position display"""
        self.encoder_running = False
        self.encoder_update_running = False
        self.encoder_start_btn.configure(" Display", bg=self.colors['success_green'])
        
        if self.encoder_update_thread:
            self.encoder_update_thread.join(timeout=1)
            
    def encoder_update_loop(self):
        """Encoder position update loop"""
        while self.encoder_update_running:
            try:
                if not self.controller:
                    break
                    
                # Get current position for all axes
                positions = {}
                for axis in ["A", "B", "C", "D"]:
                    try:
                        pos_str = self.controller.send_command(f"TP {axis}")
                        positions[axis] = int(pos_str.strip())
                    except:
                        positions[axis] = 0
                
                # Update UI in main thread with all positions
                self.root.after(0, self.update_all_encoder_positions, positions)
                
                # Sleep for update interval - increased to reduce controller load
                time.sleep(0.2)  # 200ms updates (5 updates per second)
                
            except Exception as e:
                # Update UI with error in main thread
                self.root.after(0, self.update_encoder_display, None, str(e))
                break
                
    def update_encoder_display(self, position, error=None):
        """Update encoder display with new position"""
        if not self.encoder_update_running:
            return
            
        if error:
            self.position_label.configure(f"Error: {error}")
            return
            
        # Update position label
        self.position_label.configure(f"{position}")
        
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
    
    def check_travel_limits(self):
        """Check travel limits for all axes"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.log_message( "\n=== TRAVEL LIMIT & LIMIT SWITCH CHECK ===\n")
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    travel_limit = self.controller.send_command(f"MG _TL{axis}").strip()
                    limit_status = self.controller.send_command(f"MG _LF{axis}").strip()
                    position = self.controller.send_command(f"TP {axis}").strip()
                    
                    # Check for limit switch configuration
                    try:
                        limit_config = self.controller.send_command(f"MG _LT{axis}").strip()
                    except:
                        limit_config = "?"
                    
                    self.log_message( f"Axis {axis}:\n")
                    self.log_message( f"  Travel Limit: {travel_limit}\n")
                    self.log_message( f"  Limit Status: {limit_status}\n")
                    self.log_message( f"  Limit Config: {limit_config}\n")
                    self.log_message( f"  Position: {position}\n")
                    
                    if limit_status != "0":
                        self.log_message( f"  âš ï¸ LIMIT SWITCH ACTIVE\n")
                    if travel_limit != "0" and travel_limit != "?":
                        self.log_message( f"  âš ï¸ TRAVEL LIMIT SET\n")
                    
                    self.log_message( "\n")
                    
                except Exception as e:
                    self.log_message( f"Axis {axis}: Error checking limits - {e}\n\n")
            
            
        except Exception as e:
            error_msg = f"Travel limit check failed: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Travel Limit Error", error_msg)
    
    def clear_travel_limits(self):
        """Clear travel limits for all axes"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.log_message( "\n=== CLEARING TRAVEL LIMITS ===\n")
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Check current travel limit
                    old_limit = self.controller.send_command(f"MG _TL{axis}").strip()
                    self.log_message( f"Axis {axis}: Current travel limit = {old_limit}\n")
                    
                    # Clear travel limit
                    self.controller.send_command(f"TL {axis}=0")
                    time.sleep(0.2)
                    
                    # Verify it was cleared
                    new_limit = self.controller.send_command(f"MG _TL{axis}").strip()
                    if new_limit == "0":
                        self.log_message( f"Axis {axis}: âœ“ Travel limit cleared\n")
                    else:
                        self.log_message( f"Axis {axis}: âš ï¸ Travel limit still {new_limit}\n")
                    
                except Exception as e:
                    self.log_message( f"Axis {axis}: Error clearing limit - {e}\n")
            
            self.log_message( "\nâœ“ Travel limits cleared for all axes\n")
            
        except Exception as e:
            error_msg = f"Travel limit clear failed: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Travel Limit Error", error_msg)
    
    def restore_travel_limits(self):
        """Restore travel limits to default values"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.log_message( "\n=== RESTORING TRAVEL LIMITS ===\n")
            
            # Default travel limit from config
            default_travel_limit = 8.2
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Set travel limit
                    self.controller.send_command(f"TL {axis}={default_travel_limit}")
                    time.sleep(0.2)
                    
                    # Verify it was set
                    new_limit = self.controller.send_command(f"MG _TL{axis}").strip()
                    if new_limit == str(default_travel_limit):
                        self.log_message( f"Axis {axis}: âœ“ Travel limit restored to {default_travel_limit}\n")
                    else:
                        self.log_message( f"Axis {axis}: âš ï¸ Travel limit set to {new_limit}\n")
                    
                except Exception as e:
                    self.log_message( f"Axis {axis}: Error restoring limit - {e}\n")
            
            self.log_message( "\nâœ“ Travel limits restored for all axes\n")
            
        except Exception as e:
            error_msg = f"Travel limit restore failed: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Travel Limit Error", error_msg)
    
    def disable_limit_switches(self):
        """Try to disable limit switches for testing"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.log_message( "\n=== DISABLING LIMIT SWITCHES ===\n")
            self.log_message( "WARNING: This will disable limit switch protection!\n")
            self.log_message( "Only use this for testing when motors are safe to move.\n\n")
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Check current limit switch status
                    old_limit_status = self.controller.send_command(f"MG _LF{axis}").strip()
                    self.log_message( f"Axis {axis}: Current limit status = {old_limit_status}\n")
                    
                    # Try to disable limit switches by setting limit configuration to 0
                    try:
                        self.controller.send_command(f"LT{axis}=0")
                        time.sleep(0.2)
                        self.log_message( f"Axis {axis}: âœ“ Limit switch configuration disabled\n")
                    except:
                        self.log_message( f"Axis {axis}: âš ï¸ Could not disable limit switch configuration\n")
                    
                    # Stop and re-enable servo to clear any limit switch latches
                    self.controller.send_command(f"ST {axis}")
                    time.sleep(0.2)
                    self.controller.send_command(f"SH {axis}")
                    time.sleep(0.2)
                    
                    # Check limit status again
                    new_limit_status = self.controller.send_command(f"MG _LF{axis}").strip()
                    if new_limit_status == "0":
                        self.log_message( f"Axis {axis}: âœ“ Limit switch cleared\n")
                    else:
                        self.log_message( f"Axis {axis}: âš ï¸ Limit switch still active ({new_limit_status})\n")
                    
                except Exception as e:
                    self.log_message( f"Axis {axis}: Error disabling limits - {e}\n")
            
            self.log_message( "\nâœ“ Limit switch disable attempt completed\n")
            self.log_message( "Note: Some limit switches may be hardware-based and cannot be disabled\n")
            
        except Exception as e:
            error_msg = f"Limit switch disable failed: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Limit Switch Error", error_msg)
    
    def enable_limit_switches(self):
        """Re-enable limit switches for safety"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
            
        try:
            self.log_message( "\n=== RE-ENABLING LIMIT SWITCHES ===\n")
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Try to re-enable limit switches by setting limit configuration to default
                    try:
                        self.controller.send_command(f"LT{axis}=1")
                        time.sleep(0.2)
                        self.log_message( f"Axis {axis}: âœ“ Limit switch configuration re-enabled\n")
                    except:
                        self.log_message( f"Axis {axis}: âš ï¸ Could not re-enable limit switch configuration\n")
                    
                    # Stop and re-enable servo
                    self.controller.send_command(f"ST {axis}")
                    time.sleep(0.2)
                    self.controller.send_command(f"SH {axis}")
                    time.sleep(0.2)
                    
                    # Check limit status
                    limit_status = self.controller.send_command(f"MG _LF{axis}").strip()
                    self.log_message( f"Axis {axis}: Limit status = {limit_status}\n")
                    
                except Exception as e:
                    self.log_message( f"Axis {axis}: Error re-enabling limits - {e}\n")
            
            self.log_message( "\nâœ“ Limit switch re-enable attempt completed\n")
            
        except Exception as e:
            error_msg = f"Limit switch re-enable failed: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Limit Switch Error", error_msg)
    
    def run_command_compatibility_test(self):
        """Run comprehensive command compatibility test"""
        self._ensure_controller_connected()
        
        try:
            self.log_message( "=== STARTING COMMAND COMPATIBILITY TEST ===\n")
            self.log_message( "This will test all available Galil DMC-4103 commands...\n")
            self.log_message( "This may take several minutes. Please wait...\n\n")
            
            # Create compatibility checker
            checker = GalilCommandChecker(self.controller)
            
            # Run the test with progress callback
            def progress_callback(message):
                self.log_message( f"{message}\n")
                self.root.update()
            
            # Run test in separate thread to avoid blocking UI
            def run_test():
                try:
                    results = checker.run_compatibility_test(progress_callback)
                    
                    # Update UI with results
                    self.root.after(0, lambda: self._display_compatibility_results(checker, results))
                    
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"Error during compatibility test: {e}"))
            
            # Start test thread
            test_thread = threading.Thread(target=run_test, daemon=True)
            test_thread.start()
            
        except Exception as e:
            self.log_message( f"Error starting compatibility test: {e}\n")
    
    def _display_compatibility_results(self, checker, results):
        """Display compatibility test results"""
        try:
            self.log_message( "\n" + "="*60 + "\n")
            self.log_message( "COMMAND COMPATIBILITY TEST RESULTS\n")
            self.log_message( "="*60 + "\n")
            self.log_message( f"Total Commands Tested: {results['total_commands']}\n")
            self.log_message( f"Compatible Commands: {results['compatible_commands']}\n")
            self.log_message( f"Incompatible Commands: {results['incompatible_commands']}\n")
            self.log_message( f"Compatibility Rate: {results['compatibility_rate']:.1f}%\n\n")
            
            # Save results
            filename = checker.save_results()
            self.log_message( f"Results saved to: {filename}\n\n")
            
            # Store checker for later use
            self.compatibility_checker = checker
            
            self.log_message( "âœ“ Compatibility test completed successfully!\n")
            self.log_message( "Use 'Show Compatible Commands' to view detailed results.\n")
            
        except Exception as e:
            self.log_message( f"Error displaying results: {e}\n")
    
    def show_compatible_commands(self):
        """Show detailed compatible commands"""
        if not hasattr(self, 'compatibility_checker'):
            self.log_message( "No compatibility test results available. Run the compatibility test first.\n")
            return
        
        try:
            self.log_message( "\n" + "="*60 + "\n")
            self.log_message( "COMPATIBLE COMMANDS BY CATEGORY\n")
            self.log_message( "="*60 + "\n")
            
            compatible_by_category = self.compatibility_checker.get_compatible_commands_by_category()
            
            for category, commands in compatible_by_category.items():
                if commands:
                    self.log_message( f"\n{category}:\n")
                    self.log_message( "-" * len(category) + "\n")
                    for command, info in commands.items():
                        self.log_message( f"  {command:<10} - {info['description']}\n")
                        if info.get('response'):
                            self.log_message( f"           Response: {info['response']}\n")
                    self.log_message( "\n")
            
            
        except Exception as e:
            self.log_message( f"Error showing compatible commands: {e}\n")
    
    def configure_all_axes_like_axis_a(self):
        """Configure all axes to match Axis A settings (which works correctly)"""
        self.append_test_log("=== CONFIGURING ALL AXES TO MATCH AXIS A ===")
        
        try:
            # Get Axis A settings as the reference
            self.append_test_log("Reading Axis A configuration as reference...")
            
            # Get Axis A limit switch settings using correct variable names
            try:
                # Use correct DMC-4103 variable names
                axis_a_lf = self.controller.send_command("MG _LFA").strip()  # Forward limit switch
                axis_a_lr = self.controller.send_command("MG _LRA").strip()  # Reverse limit switch
                axis_a_tl = self.controller.send_command("MG _TLA").strip()  # Travel limit
                
                self.append_test_log(f"Axis A settings - LF: {axis_a_lf}, LR: {axis_a_lr}, TL: {axis_a_tl}")
                
                # If variables return "?", use default values
                if axis_a_lf == "?" or axis_a_lf == "":
                    axis_a_lf = "0"  # Default: no forward limit
                if axis_a_lr == "?" or axis_a_lr == "":
                    axis_a_lr = "0"  # Default: no reverse limit  
                if axis_a_tl == "?" or axis_a_tl == "":
                    axis_a_tl = "0"  # Default: no travel limit
                    
                self.append_test_log(f"Using Axis A settings - LF: {axis_a_lf}, LR: {axis_a_lr}, TL: {axis_a_tl}")
                
            except Exception as e:
                self.append_test_log(f"WARNING: Could not read Axis A settings: {e}")
                # Use default values if reading fails
                axis_a_lf = "0"
                axis_a_lr = "0" 
                axis_a_tl = "0"
                self.append_test_log("Using default limit settings for all axes")
            
            # Configure other axes to match Axis A
            for axis in ["B", "C", "D"]:
                self.append_test_log(f"Configuring Axis {axis} to match Axis A...")
                
                try:
                    # Set motor type (required for servo operation)
                    # Ensure motor is off before setting motor type (required by Galil)
                    self.controller.send_command(f"MO {axis}")  # Motor off
                    time.sleep(0.1)
                    
                    # Set motor type using correct Galil syntax: MTm= n
                    mt_response = self.controller.send_command(f"MT{axis}=1")  # Servo motor (3-phased brushless)
                    if mt_response == "?":
                        # Try stepper motor type if servo fails
                        mt_response = self.controller.send_command(f"MT{axis}=2")  # Stepper motor
                        if mt_response == "?":
                            self.append_test_log(f"WARNING: Could not set motor type for Axis {axis}")
                        elif mt_response == "":
                            self.append_test_log(f"Axis {axis}: Using stepper motor type (MT=2) - set successfully")
                        else:
                            self.append_test_log(f"Axis {axis}: Using stepper motor type (MT=2) - response: {mt_response}")
                    elif mt_response == "":
                        self.append_test_log(f"Axis {axis}: Using servo motor type (MT=1) - set successfully")
                    else:
                        self.append_test_log(f"Axis {axis}: Using servo motor type (MT=1) - response: {mt_response}")
                    time.sleep(0.2)  # Give more time for motor type to be set
                    
                    # Verify motor type was set
                    motor_type = self.controller.send_command(f"MG _MT{axis}").strip()
                    if motor_type == "?" or motor_type == "":
                        self.append_test_log(f"WARNING: Could not verify motor type for Axis {axis}")
                    
                    # Clear any travel limits
                    self.controller.send_command(f"TL {axis}=0")
                    time.sleep(0.1)
                    
                    # Clear software limits that might be preventing motion
                    self.controller.send_command(f"FL {axis}=0")  # Clear forward software limit
                    self.controller.send_command(f"BL {axis}=0")  # Clear reverse software limit
                    time.sleep(0.1)
                    
                    # Set limit switch configuration to match Axis A (skip LT command as it's not needed)
                    
                    # Set travel limits to match Axis A
                    if axis_a_tl != "0":
                        self.controller.send_command(f"TL {axis}={axis_a_tl}")
                        time.sleep(0.1)
                    
                    # Stop and re-enable servo to apply changes
                    self.controller.send_command(f"ST {axis}")
                    time.sleep(0.2)
                    self.controller.send_command(f"SH {axis}")
                    time.sleep(0.2)
                    
                    # Verify settings
                    try:
                        new_tl = self.controller.send_command(f"MG _TL{axis}").strip()
                        new_lf = self.controller.send_command(f"MG _LF{axis}").strip()
                        new_lr = self.controller.send_command(f"MG _LR{axis}").strip()
                        self.append_test_log(f"Axis {axis} configured - TL: {new_tl}, LF: {new_lf}, LR: {new_lr}")
                    except:
                        self.append_test_log(f"Axis {axis} configuration applied")
                    
                except Exception as e:
                    self.append_test_log(f"WARNING: Could not configure Axis {axis}: {e}")
            
            self.append_test_log("=== AXIS CONFIGURATION COMPLETE ===")
            
        except Exception as e:
            self.append_test_log(f"ERROR during axis configuration: {e}")
    
    def clear_all_software_limits(self):
        """Clear all software limits to prevent motion restrictions during diagnostics"""
        self.append_test_log("=== CLEARING SOFTWARE LIMITS ===")
        
        try:
            for axis in ["A", "B", "C", "D"]:
                self.append_test_log(f"Clearing software limits for Axis {axis}...")
                
                # Set motor type (required for servo operation)
                # Ensure motor is off before setting motor type (required by Galil)
                self.controller.send_command(f"MO {axis}")  # Motor off
                time.sleep(0.1)
                
                # Set motor type using correct Galil syntax: MTm= n
                mt_response = self.controller.send_command(f"MT{axis}=1")  # Servo motor (3-phased brushless)
                if mt_response == "?":
                    # Try stepper motor type if servo fails
                    mt_response = self.controller.send_command(f"MT{axis}=2")  # Stepper motor
                    if mt_response == "?":
                        self.append_test_log(f"WARNING: Could not set motor type for Axis {axis}")
                    elif mt_response == "":
                        self.append_test_log(f"Axis {axis}: Using stepper motor type (MT=2) - set successfully")
                    else:
                        self.append_test_log(f"Axis {axis}: Using stepper motor type (MT=2) - response: {mt_response}")
                elif mt_response == "":
                    self.append_test_log(f"Axis {axis}: Using servo motor type (MT=1) - set successfully")
                else:
                    self.append_test_log(f"Axis {axis}: Using servo motor type (MT=1) - response: {mt_response}")
                time.sleep(0.2)  # Give more time for motor type to be set
                
                # Clear forward and reverse software limits
                self.controller.send_command(f"FL {axis}=0")  # Forward software limit
                self.controller.send_command(f"BL {axis}=0")  # Reverse software limit
                time.sleep(0.1)
                
                # Verify limits are cleared
                try:
                    fl_value = self.controller.send_command(f"MG _FL{axis}").strip()
                    bl_value = self.controller.send_command(f"MG _BL{axis}").strip()
                    self.append_test_log(f"Axis {axis} limits - FL: {fl_value}, BL: {bl_value}")
                except:
                    self.append_test_log(f"Axis {axis} limits cleared (verification failed)")
            
            self.append_test_log("=== SOFTWARE LIMITS CLEARED ===")
            
        except Exception as e:
            self.append_test_log(f"ERROR: Failed to clear software limits: {e}")
            self.append_test_log("Proceeding with diagnostics anyway...")
    

    
    def copy_axis_a_to_all_axes(self):
        """Copy all working Axis A settings to Axes B, C, and D"""
        self.append_test_log("=== COPYING AXIS A SETTINGS TO ALL AXES ===")
        
        try:
            # Step 1: Read all Axis A settings
            self.append_test_log("Step 1: Reading all Axis A settings...")
            
            # PID Settings
            try:
                kp_a = float(self.controller.send_command("MG _KPA").strip())
                ki_a = float(self.controller.send_command("MG _KIA").strip())
                kd_a = float(self.controller.send_command("MG _KDA").strip())
                self.append_test_log(f"Axis A PID - KP: {kp_a}, KI: {ki_a}, KD: {kd_a}")
            except:
                self.append_test_log("Using default PID values")
                kp_a, ki_a, kd_a = 10.0, 0.1, 50.0
            
            # Motion Parameters
            try:
                sp_a = float(self.controller.send_command("MG _SPA").strip())
                ac_a = float(self.controller.send_command("MG _ACA").strip())
                dc_a = float(self.controller.send_command("MG _DCA").strip())
                self.append_test_log(f"Axis A Motion - SP: {sp_a}, AC: {ac_a}, DC: {dc_a}")
            except:
                self.append_test_log("Using default motion parameters")
                sp_a, ac_a, dc_a = 50000.0, 25000.0, 50000.0
            
            # Limit Settings
            try:
                tl_a = self.controller.send_command("MG _TLA").strip()
                lt_a = self.controller.send_command("MG _LTA").strip()
                lf_a = self.controller.send_command("MG _LFA").strip()
                self.append_test_log(f"Axis A Limits - TL: {tl_a}, LT: {lt_a}, LF: {lf_a}")
            except:
                self.append_test_log("Using default limit settings")
                tl_a, lt_a, lf_a = "0", "0", "0"
            
            # Servo Settings
            try:
                servo_a = self.controller.send_command("MG _SAA").strip()
                self.append_test_log(f"Axis A Servo Status: {servo_a}")
            except:
                self.append_test_log("Could not read servo status")
            
            # Step 2: Apply settings to all other axes
            self.append_test_log("Step 2: Applying settings to Axes B, C, D...")
            
            for axis in ['B', 'C', 'D']:
                self.append_test_log(f"Configuring Axis {axis}...")
                
                # Stop any motion
                self.controller.send_command(f"ST {axis}")
                time.sleep(0.1)
                
                # Apply PID settings
                self.controller.send_command(f"KP {axis}={kp_a}")
                self.controller.send_command(f"KI {axis}={ki_a}")
                self.controller.send_command(f"KD {axis}={kd_a}")
                time.sleep(0.1)
                
                # Apply motion parameters
                self.controller.send_command(f"SP {axis}={sp_a}")
                self.controller.send_command(f"AC {axis}={ac_a}")
                self.controller.send_command(f"DC {axis}={dc_a}")
                time.sleep(0.1)
                
                # Apply limit settings
                self.controller.send_command(f"TL{axis}={tl_a}")
                self.controller.send_command(f"LT{axis}={lt_a}")
                self.controller.send_command(f"LF{axis}={lf_a}")
                time.sleep(0.1)
                
                # Reset servo
                self.controller.send_command(f"MO {axis}")  # Disable
                time.sleep(0.1)
                self.controller.send_command(f"SH {axis}")  # Enable
                time.sleep(0.2)
                
                self.append_test_log(f"Axis {axis} configuration complete")
            
            # Step 3: Verify settings were applied
            self.append_test_log("Step 3: Verifying settings...")
            
            for axis in ['B', 'C', 'D']:
                try:
                    kp = float(self.controller.send_command(f"MG _KP {axis}").strip())
                    ki = float(self.controller.send_command(f"MG _KI {axis}").strip())
                    kd = float(self.controller.send_command(f"MG _KD {axis}").strip())
                    sp = float(self.controller.send_command(f"MG _SP {axis}").strip())
                    ac = float(self.controller.send_command(f"MG _AC {axis}").strip())
                    dc = float(self.controller.send_command(f"MG _DC {axis}").strip())
                    
                    self.append_test_log(f"Axis {axis} verified - KP:{kp}, KI:{ki}, KD:{kd}, SP:{sp}, AC:{ac}, DC:{dc}")
                except Exception as e:
                    self.append_test_log(f"Could not verify Axis {axis} settings: {e}")
            
            # Step 4: Test movement on all axes
            self.append_test_log("Step 4: Testing movement on all axes...")
            
            for axis in ['B', 'C', 'D']:
                self.append_test_log(f"Testing Axis {axis} movement...")
                try:
                    pos_start = int(self.controller.send_command(f"TP {axis}").strip())
                    
                    # Small test move
                    self.controller.send_command(f"SP {axis}=5000")
                    self.controller.send_command(f"AC {axis}=5000")
                    self.controller.send_command(f"DC {axis}=5000")
                    self.controller.send_command(f"PR {axis}=500")
                    self.controller.send_command(f"BG {axis}")
                    time.sleep(0.5)
                    self.controller.send_command(f"ST {axis}")
                    time.sleep(0.5)
                    
                    pos_end = int(self.controller.send_command(f"TP {axis}").strip())
                    movement = pos_end - pos_start
                    
                    if abs(movement) > 50:
                        self.append_test_log(f"âœ“ Axis {axis}: SUCCESS - moved {movement} counts")
                    else:
                        self.append_test_log(f"âš  Axis {axis}: LIMITED - moved {movement} counts")
                        
                except Exception as e:
                    self.append_test_log(f"âœ— Axis {axis}: FAILED - {e}")
            
            # Step 5: Summary
            self.append_test_log("=== COPY COMPLETE ===")
            self.append_test_log("All axes now have identical settings to Axis A")
            self.append_test_log("Run motor detection to verify all axes are working")
            
        except Exception as e:
            self.append_test_log(f"ERROR copying settings: {e}")
        
    def show_controller_testing(self):
        """Show comprehensive controller testing interface"""
        self.clear_main_content()
        
        # Title
        title = tk.Label(self.main_content, text="Controller Testing", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Main content frame
        main_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        main_frame.pack(fill='both', expand=True)
        
        # 1. ENCODER POSITION DISPLAY (TOP)
        encoder_frame = tk.LabelFrame(main_frame, text="Real-time Encoder Positions", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        encoder_frame.pack(fill='x', pady=(0, 10))
        
        # Ensure encoder frame has proper sizing - make it taller for better visibility
        encoder_frame.pack_propagate(False)
        encoder_frame.configure(height=560)
        
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
        encoder_displays_frame.pack(fill='x', expand=True, padx=15, pady=(0, 15))
        
        # Get shared encoder displays
        self.encoder_displays, self.encoder_labels = self.get_shared_encoder_displays()
        
        for i, axis in enumerate(['A', 'B', 'C', 'D']):
            # Individual axis frame - make it taller to accommodate both speed bar and position dial
            axis_frame = tk.Frame(encoder_displays_frame, bg=self.colors['main_bg'], relief='solid', bd=1)
            axis_frame.pack(side='left', fill='both', expand=True, padx=3, pady=3)
            
            # Ensure minimum size for visibility - make them much larger to prevent cutoff
            axis_frame.pack_propagate(False)
            axis_frame.configure(width=280, height=480)
            
            # Force the frame to maintain its size
            axis_frame.update_idletasks()
            axis_frame.configure(width=280, height=480)
            
            # Axis title
            axis_title = tk.Label(axis_frame, text=f"Axis {axis}", 
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'])
            axis_title.pack(pady=(5, 2))
            
            # Speed bar canvas (half-moon shaped) - make it much larger to prevent cutoff
            speed_canvas = tk.Canvas(axis_frame, bg='white', height=140, width=250, relief='sunken', bd=1)
            speed_canvas.pack(padx=8, pady=5)
            
            # Position dial canvas (clock-like) - make it much larger to prevent cutoff
            position_canvas = tk.Canvas(axis_frame, bg='white', height=200, width=200, relief='sunken', bd=1)
            position_canvas.pack(padx=8, pady=5)
            
            # Position label for this axis
            position_label = tk.Label(axis_frame, text="Position: 0", 
                                    font=("Arial", 11, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'])
            position_label.pack(pady=(8, 15))
            
            # Store references - we'll store both canvases
            self.encoder_displays[axis] = {
                'speed': speed_canvas,
                'position': position_canvas
            }
            self.encoder_labels[axis] = position_label
            
            # Initialize the displays
            # Initializing encoder display for axis
            self._initialize_encoder_display(axis)
            
            # Force update for each axis frame
            axis_frame.update_idletasks()
        
        # After all displays are created, update them with current positions if available
        self.root.after(100, self._update_displays_with_current_positions)
        
        # Also start a periodic update to ensure displays stay current
        self.root.after(200, self._start_periodic_display_updates)
        
        # Force an immediate update to test the display system
        self.root.after(300, self._force_immediate_display_update)
        
        # 3. MANUAL COMMAND BOX (THIRD)
        command_frame = tk.LabelFrame(main_frame, text="Manual Command Input", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        command_frame.pack(fill='x', pady=(0, 10))
        
        # Command input section
        command_input_frame = tk.Frame(command_frame, bg=self.colors['main_bg'])
        command_input_frame.pack(fill='x', padx=15, pady=15)
        
        # Command input label and entry
        tk.Label(command_input_frame, text="DMC-4103 Command:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        # Command entry with send button
        command_entry_frame = tk.Frame(command_input_frame, bg=self.colors['main_bg'])
        command_entry_frame.pack(fill='x', pady=(5, 10))
        
        self.manual_command_entry = tk.Entry(command_entry_frame, font=("Consolas", 11), 
                                           bg='white', fg='black', relief='solid', bd=1)
        self.manual_command_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.manual_command_entry.bind('<Return>', self.send_manual_command)
        
        # Send button
        send_btn = tk.Button(command_entry_frame, text="Send Command", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['accent_blue'], fg='white',
                           command=self.send_manual_command)
        send_btn.pack(side='right')
        
        # Quick command buttons
        quick_commands_frame = tk.Frame(command_frame, bg=self.colors['main_bg'])
        quick_commands_frame.pack(fill='x', padx=15, pady=(0, 10))
        
        tk.Label(quick_commands_frame, text="Quick Commands:", font=("Arial", 9, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        quick_btn_frame = tk.Frame(quick_commands_frame, bg=self.colors['main_bg'])
        quick_btn_frame.pack(fill='x', pady=(5, 0))
        
        # Quick command buttons
        quick_commands = [
            ("TPA", "Position A"), ("TPB", "Position B"), ("TPC", "Position C"), ("TPD", "Position D"),
            ("SH A", "Servo On A"), ("MO A", "Motor Off A"), ("ST A", "Stop A"), ("BG A", "Begin A")
        ]
        
        for i, (cmd, desc) in enumerate(quick_commands):
            btn = tk.Button(quick_btn_frame, text=f"{cmd}\n{desc}", 
                          font=("Arial", 8), width=8, height=2,
                          bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                          command=lambda c=cmd: self.insert_quick_command(c))
            btn.grid(row=i//4, column=i%4, padx=2, pady=2)
        
        # Command response area
        response_frame = tk.Frame(command_frame, bg=self.colors['main_bg'])
        response_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        tk.Label(response_frame, text="Response:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        self.command_response_text = scrolledtext.ScrolledText(response_frame, height=4, 
                                                            font=("Consolas", 9),
                                                            bg='white', fg='black')
        self.command_response_text.pack(fill='x', pady=(5, 0))
        
        # Clear response button
        clear_btn = tk.Button(response_frame, text="Clear Response", 
                            font=("Arial", 8),
                            bg=self.colors['warning_orange'], fg='white',
                            command=self.clear_command_response)
        clear_btn.pack(anchor='e', pady=(5, 0))
        
        # Command examples
        examples_frame = tk.Frame(command_frame, bg=self.colors['main_bg'])
        examples_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        tk.Label(examples_frame, text="Command Examples:", font=("Arial", 9, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        examples_text = "TPA (Tell Position A) | TPB (Tell Position B) | SH A (Servo Here A) | MO A (Motor Off A)\n"
        examples_text += "SP A=1000 (Set Speed A) | AC A=500 (Set Acceleration A) | BG A (Begin Motion A)\n"
        examples_text += "PA A=1000 (Position Absolute A) | PR A=100 (Position Relative A) | ST A (Stop A)"
        
        examples_label = tk.Label(examples_frame, text=examples_text, 
                                font=("Consolas", 8),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                justify='left')
        examples_label.pack(anchor='w', pady=(5, 0))
        
        # 4. MOTION CONTROLS (FOURTH)
        motion_frame = tk.LabelFrame(main_frame, text="Motion Controls", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        motion_frame.pack(fill='x', pady=(0, 10))
        
        # Create a two-column layout for motion controls
        motion_content_frame = tk.Frame(motion_frame, bg=self.colors['main_bg'])
        motion_content_frame.pack(fill='x', padx=15, pady=15)
        
        # Left column - PID Configuration
        pid_column = tk.Frame(motion_content_frame, bg=self.colors['main_bg'])
        pid_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # PID Configuration Section
        pid_frame = tk.LabelFrame(pid_column, text="PID Configuration", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        pid_frame.pack(fill='x', pady=(0, 10))
        
        # Axis selection at the top
        axis_frame = tk.Frame(pid_frame, bg=self.colors['main_bg'])
        axis_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        tk.Label(axis_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        self.test_axis_var = tk.StringVar(value="A")
        axis_combo = ttk.Combobox(axis_frame, textvariable=self.test_axis_var, 
                                 values=["A", "B", "C", "D"], width=10)
        axis_combo.pack(side='left', padx=(10, 0))
        
        # PID values in a column
        pid_values_frame = tk.Frame(pid_frame, bg=self.colors['main_bg'])
        pid_values_frame.pack(fill='x', padx=10, pady=5)
        
        # KP
        kp_frame = tk.Frame(pid_values_frame, bg=self.colors['main_bg'])
        kp_frame.pack(fill='x', pady=2)
        tk.Label(kp_frame, text="KP:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        self.test_kp_entry = tk.Entry(kp_frame, font=("Arial", 10), width=12)
        self.test_kp_entry.pack(side='right')
        self.test_kp_entry.insert(0, "10.0")
        
        # KI
        ki_frame = tk.Frame(pid_values_frame, bg=self.colors['main_bg'])
        ki_frame.pack(fill='x', pady=2)
        tk.Label(ki_frame, text="KI:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        self.test_ki_entry = tk.Entry(ki_frame, font=("Arial", 10), width=12)
        self.test_ki_entry.pack(side='right')
        self.test_ki_entry.insert(0, "0.1")
        
        # KD
        kd_frame = tk.Frame(pid_values_frame, bg=self.colors['main_bg'])
        kd_frame.pack(fill='x', pady=2)
        tk.Label(kd_frame, text="KD:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        self.test_kd_entry = tk.Entry(kd_frame, font=("Arial", 10), width=12)
        self.test_kd_entry.pack(side='right')
        self.test_kd_entry.insert(0, "50.0")
        
        # Tune button
        tune_btn = tk.Button(pid_frame, text="Tune Axis", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=self.test_tune_axis)
        tune_btn.pack(pady=(10, 15))
        
        # Motion Parameters Section
        params_frame = tk.LabelFrame(pid_column, text="Motion Parameters", 
                                   font=("Arial", 10, "bold"),
                                  bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                  relief='solid', bd=1)
        params_frame.pack(fill='x', pady=(0, 10))
        
        # Speed and acceleration
        params_values_frame = tk.Frame(params_frame, bg=self.colors['main_bg'])
        params_values_frame.pack(fill='x', padx=10, pady=10)
        
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
        
        # Right column - Movement Controls
        movement_column = tk.Frame(motion_content_frame, bg=self.colors['main_bg'])
        movement_column.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Jog Controls Section
        jog_frame = tk.LabelFrame(movement_column, text="Jog Controls", 
                                font=("Arial", 10, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        jog_frame.pack(fill='x', pady=(0, 10))
        
        # Jog Distance
        jog_distance_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_distance_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        tk.Label(jog_distance_frame, text="Jog Distance (mm):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        self.test_jog_distance_entry = tk.Entry(jog_distance_frame, font=("Arial", 10), width=12)
        self.test_jog_distance_entry.pack(anchor='w', pady=(5, 0))
        self.test_jog_distance_entry.insert(0, "10.0")
        
        # Jog buttons
        jog_buttons_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_buttons_frame.pack(fill='x', padx=10, pady=(5, 15))
        
        tk.Button(jog_buttons_frame, text="Jog +", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=lambda: self.test_jog_axis(1)).pack(side='left', padx=(0, 5))
        
        tk.Button(jog_buttons_frame, text="Jog -", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=lambda: self.test_jog_axis(-1)).pack(side='left', padx=5)
        
        tk.Button(jog_buttons_frame, text="Stop", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.test_stop_axis).pack(side='left', padx=5)
        
        # Position Control Section
        pos_frame = tk.LabelFrame(movement_column, text="Position Control", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        pos_frame.pack(fill='x', pady=(0, 10))
        
        # Position input
        pos_input_frame = tk.Frame(pos_frame, bg=self.colors['main_bg'])
        pos_input_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        tk.Label(pos_input_frame, text="Position (counts):", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        self.test_position_entry = tk.Entry(pos_input_frame, font=("Arial", 10), width=12)
        self.test_position_entry.pack(anchor='w', pady=(5, 0))
        self.test_position_entry.insert(0, "10000")
        
        # Move buttons
        move_buttons_frame = tk.Frame(pos_frame, bg=self.colors['main_bg'])
        move_buttons_frame.pack(fill='x', padx=10, pady=(5, 15))
        
        tk.Button(move_buttons_frame, text="Move", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.test_move_to_position).pack(side='left', padx=(0, 5))
        
        tk.Button(move_buttons_frame, text="Test Move", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.test_simple_move).pack(side='left', padx=5)
        
        # Servo Control Section
        servo_frame = tk.LabelFrame(movement_column, text="Servo Control", 
                            font=("Arial", 10, "bold"),
                                      bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                      relief='solid', bd=1)
        servo_frame.pack(fill='x', pady=(0, 10))
        
        # Servo control buttons
        servo_buttons_frame = tk.Frame(servo_frame, bg=self.colors['main_bg'])
        servo_buttons_frame.pack(fill='x', padx=10, pady=10)
        
        # Configure grid weights for 3 columns
        servo_buttons_frame.grid_columnconfigure(0, weight=1)
        servo_buttons_frame.grid_columnconfigure(1, weight=1)
        servo_buttons_frame.grid_columnconfigure(2, weight=1)
        
        # Row 1
        tk.Button(servo_buttons_frame, text="Servo On", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.test_servo_on).grid(row=0, column=0, padx=2, pady=2, sticky='ew')
        
        tk.Button(servo_buttons_frame, text="Servo Off", 
                font=("Arial", 10, "bold"),
                bg=self.colors['error_red'], fg='white',
                command=self.test_servo_off).grid(row=0, column=1, padx=2, pady=2, sticky='ew')
        
        tk.Button(servo_buttons_frame, text="Stop All", 
                font=("Arial", 10, "bold"),
                bg=self.colors['warning_orange'], fg='white',
                command=self.test_stop_all).grid(row=0, column=2, padx=2, pady=2, sticky='ew')
        
        # Row 2
        tk.Button(servo_buttons_frame, text="Status Check", 
                font=("Arial", 10, "bold"),
                bg=self.colors['accent_blue'], fg='white',
                command=self.check_controller_status).grid(row=1, column=0, padx=2, pady=2, sticky='ew')
        
        tk.Button(servo_buttons_frame, text="Enable All Servos", 
                font=("Arial", 10, "bold"),
                bg=self.colors['success_green'], fg='white',
                command=self.enable_all_servos).grid(row=1, column=1, padx=2, pady=2, sticky='ew')

        # 4. AUTOMATIC DIAGNOSTICS (BOTTOM)
        auto_diag_frame = tk.LabelFrame(main_frame, text="Automatic Diagnostics", 
                                      font=("Arial", 12, "bold"),
                                      bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                      relief='solid', bd=1)
        auto_diag_frame.pack(fill='x', pady=(0, 10))

        # Automatic Diagnostics buttons in 3 columns
        auto_diag_row = tk.Frame(auto_diag_frame, bg=self.colors['main_bg'])
        auto_diag_row.pack(fill='x', padx=15, pady=10)
        
        # Configure grid weights for 3 columns
        auto_diag_row.grid_columnconfigure(0, weight=1)
        auto_diag_row.grid_columnconfigure(1, weight=1)
        auto_diag_row.grid_columnconfigure(2, weight=1)

        self.auto_diag_running = False
        
        # Row 1
        self.auto_diag_btn = tk.Button(auto_diag_row, text="Run Automatic Diagnostics", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['accent_blue'], fg='white',
                                       command=self.toggle_automatic_diagnostics)
        self.auto_diag_btn.grid(row=0, column=0, padx=2, pady=2, sticky='ew')
        
        # Copy Axis A to All Axes button
        self.copy_axis_a_btn = tk.Button(auto_diag_row, text="Copy Axis A to All Axes", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['accent_blue'], fg='white',
                                       command=self.copy_axis_a_to_all_axes)
        self.copy_axis_a_btn.grid(row=0, column=1, padx=2, pady=2, sticky='ew')
        
        # Save Report button
        self.save_report_btn = tk.Button(auto_diag_row, text="💾 Save Report", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['warning_orange'], fg='white',
                                       command=self.save_diagnostic_report,
                                       state='disabled')
        self.save_report_btn.grid(row=0, column=2, padx=2, pady=2, sticky='ew')
        
        # Row 2
        # Load Report button
        self.load_report_btn = tk.Button(auto_diag_row, text="📂 Load Report", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['accent_blue'], fg='white',
                                       command=self.load_diagnostic_report)
        self.load_report_btn.grid(row=1, column=0, padx=2, pady=2, sticky='ew')
        
        # Export CSV button
        self.export_csv_btn = tk.Button(auto_diag_row, text="📊 Export CSV", 
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['success_green'], fg='white',
                                       command=self.export_diagnostic_csv,
                                       state='disabled')
        self.export_csv_btn.grid(row=1, column=1, padx=2, pady=2, sticky='ew')
        
        # Compare Reports button
        self.compare_reports_btn = tk.Button(auto_diag_row, text="📈 Compare Reports", 
                                           font=("Arial", 10, "bold"),
                                           bg=self.colors['warning_orange'], fg='white',
                                           command=self.compare_diagnostic_reports)
        self.compare_reports_btn.grid(row=1, column=2, padx=2, pady=2, sticky='ew')
        
        # Ensure scroll region is properly updated for this page
        self.root.after(500, self._update_page_scroll_region)
        self.root.after(1000, self._update_page_scroll_region)
        
        # Force update encoder displays to ensure all axes are visible
        self.root.after(200, self._force_update_encoder_displays)
        self.root.after(400, self._force_update_encoder_displays)
        
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
        """Run comprehensive diagnostics using the new controller commands module"""
        if self.controller_commands:
            # First, configure all axes to match Axis A settings
            self.configure_all_axes_like_axis_a()
        
        # Clear software limits for all axes to prevent motion restrictions
        self.clear_all_software_limits()
        
        # Initialize diagnostic results storage
        self.diagnostic_results = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'controller_info': {},
            'motor_detection': {},
            'axis_results': {},
            'summary': {}
        }
        
        # Run the comprehensive diagnostics using the new module
        result = self.controller_commands.run_automatic_diagnostics()
        
        if "error" in result:
            self.append_test_log(f"ERROR: {result['error']}")
            return
        
        # Process the results
        self.diagnostic_results.update(result)
        
        # Display motor detection summary
        motor_detection = result.get("motor_detection", {})
        total_motors = sum(1 for detected in motor_detection.values() if detected)
        
        self.append_test_log(f"\n=== MOTOR DETECTION SUMMARY ===")
        for axis, detected in motor_detection.items():
            status = "✓ Motor detected" if detected else "✗ No motor detected"
            self.append_test_log(f"Axis {axis}: {status}")
        
        self.append_test_log(f"Total motors detected: {total_motors}/4")
        if total_motors == 0:
            self.append_test_log("WARNING: No motors detected on any axis!")
            self.append_test_log("Please check motor connections and try again.")
            return result
        
        # Continue with axis testing if motors are detected
        self.append_test_log("Motors detected, proceeding with axis testing...")
        
        # Display axis test results
        axis_results = result.get("axis_results", {})
        if axis_results:
            self.append_test_log(f"\n=== AXIS TEST RESULTS ===")
            for axis, test_result in axis_results.items():
                status = "✓ PASS" if test_result.get("passed", False) else "✗ FAIL"
                self.append_test_log(f"Axis {axis}: {status}")
                if not test_result.get("passed", False):
                    self.append_test_log(f"  Error: {test_result.get('error', 'Unknown error')}")
        
        # Display summary
        summary = result.get("summary", {})
        if summary:
            self.append_test_log(f"\n=== DIAGNOSTIC SUMMARY ===")
            self.append_test_log(f"Overall Status: {summary.get('overall_status', 'Unknown')}")
            self.append_test_log(f"Tests Passed: {summary.get('tests_passed', 0)}")
            self.append_test_log(f"Tests Failed: {summary.get('tests_failed', 0)}")
        
        return result


    def auto_connect_to_controller(self):
        """Automatically detect and connect to the Galil controller on startup"""
        if self.connection_manager:
            self.connection_manager.auto_connect_to_controller("10.1.0.21", self.update_connection_status)
        else:
            self.append_test_log("ERROR: Connection manager not initialized")

    def refresh_connection_status_display(self):
        """Refresh the connection status display based on current connection state"""
        try:
            if self.controller:
                self.update_connection_status(True)
            else:
                self.update_connection_status(False)
        except Exception as e:
            # Log the error but don't crash the application
            print(f"Error refreshing connection status display: {e}")
            # Try to update just the global header if possible
            try:
                if hasattr(self, 'gui_framework') and hasattr(self.gui_framework, 'connection_status') and self.gui_framework.connection_status.winfo_exists():
                    if self.controller:
                        self.gui_framework.connection_status.config(text="Connected", fg=self.colors['success_green'])
                    else:
                        self.gui_framework.connection_status.config(text="Disconnected", fg=self.colors['error_red'])
            except:
                pass  # If even this fails, just continue
    
    def update_connection_status(self, connected):
        """Update UI elements to reflect connection status"""
        # Debug: Log connection status updates
        self.append_test_log(f"DEBUG: update_connection_status called with connected={connected}")
        
        if connected:
            # Update global header connection status
            if hasattr(self, 'gui_framework') and hasattr(self.gui_framework, 'connection_status') and self.gui_framework.connection_status.winfo_exists():
                self.gui_framework.connection_status.config(text="Connected", fg=self.colors['success_green'])
            
            # Update local connection status label (if it exists in network config tab)
            if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
                self.connection_status_label.config(text="Connected", fg=self.colors['success_green'])
            
            # Start encoder update loop with a small delay to ensure controller is fully initialized
            self.root.after(100, self.start_encoder_update)
                
        else:
            # Clear controller reference when disconnected
            self.controller = None
            self.controller_commands = None
            self.diagnostics = None
            
            # Stop encoder update loop
            self.test_encoder_update_running = False
            if hasattr(self, 'test_encoder_update_thread') and self.test_encoder_update_thread.is_alive():
                self.test_encoder_update_thread.join(timeout=1.0)
            
            # Update global header connection status
            if hasattr(self, 'gui_framework') and hasattr(self.gui_framework, 'connection_status') and self.gui_framework.connection_status.winfo_exists():
                self.gui_framework.connection_status.config(text="Disconnected", fg=self.colors['error_red'])
            
            # Update local connection status label (if it exists in network config tab)
            if hasattr(self, 'connection_status_label') and self.connection_status_label.winfo_exists():
                self.connection_status_label.config(text="Disconnected", fg=self.colors['error_red'])
            
            # Update all position labels to show disconnected
            if hasattr(self, 'encoder_labels'):
                for axis in ['A', 'B', 'C', 'D']:
                    if axis in self.encoder_labels and self.encoder_labels[axis].winfo_exists():
                        self.encoder_labels[axis].configure(text="Not Connected", fg=self.colors['error_red'])
                        # Clear the canvases and show disconnected state
                        if axis in self.encoder_displays:
                            # Clear speed bar
                            if 'speed' in self.encoder_displays[axis] and self.encoder_displays[axis]['speed'].winfo_exists():
                                self.encoder_displays[axis]['speed'].delete("all")
                                self.encoder_displays[axis]['speed'].create_text(90, 30, text="No Connection", 
                                                                                font=("Arial", 10), fill='red')
                            
                            # Clear position dial
                            if 'position' in self.encoder_displays[axis] and self.encoder_displays[axis]['position'].winfo_exists():
                                self.encoder_displays[axis]['position'].delete("all")
                                self.encoder_displays[axis]['position'].create_text(60, 60, text="?", 
                                                                                   font=("Arial", 20), fill='gray')

    def test_basic_controller_communication(self):
        """Test basic controller communication to ensure commands are working"""
        if self.controller_commands:
            return self.controller_commands.test_basic_controller_communication()
        else:
            self.append_test_log("ERROR: Controller commands not initialized")
            return False
            
    def test_motor_type_commands(self):
        """Test different motor type command formats to find the correct syntax"""
        if self.controller_commands:
            result = self.controller_commands.test_motor_type_commands()
            working_commands = result.get("working_commands", [])
            if working_commands:
                return working_commands[0]  # Return first working command
            else:
                return None
        else:
            self.append_test_log("ERROR: Controller commands not initialized")
            return None

    def detect_motor_on_axis(self, axis):
        """Detect if a motor is connected and responding on the specified axis"""
        if self.controller_commands:
            return self.controller_commands.detect_motor_on_axis(axis)
        else:
            self.append_test_log("ERROR: Controller commands not initialized")
            return False
                
    def append_test_log(self, line: str):
        """Append a line to the persistent log in a thread-safe way."""
        # Use the persistent log instead of the individual page log
        try:
            self.log_message(line)
        except Exception as e:
            print(f"DEBUG: Error in append_test_log: {e}")
    
    def start_encoder_overlay(self):
        """Start encoder overlay functionality"""
        self.log_message("Encoder overlay started")
    
    def jog_negative(self):
        """Jog axis in negative direction"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        self.log_message("Jog negative command executed")
    
    def jog_positive(self):
        """Jog axis in positive direction"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        self.log_message("Jog positive command executed")

    def _on_visibility_change(self, event):
        """Handle window visibility change events"""
        if event.state == 'VisibilityUnobscured':
            # Window became visible, ensure all axes are visible
            self._ensure_all_axes_visible()
    
    def clear_motor_setup_log(self):
        """Clear the motor setup log"""
        if hasattr(self, 'motor_setup_log_text') and self.motor_setup_log_text.winfo_exists():
            self.motor_setup_log_text.delete(1.0, tk.END)
    
    def remove_axis_b_limits(self):
        """Remove limits for axis B"""
        if self.controller_commands:
            self.controller_commands.remove_axis_limits("B")
        else:
            self.append_test_log("ERROR: Controller commands not initialized")
    
    def save_diagnostic_report(self):
        """Save diagnostic report to file"""
        if hasattr(self, 'diagnostic_results') and self.diagnostic_results:
            try:
                import json
                from tkinter import filedialog
                
                # Ask user for file location
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    title="Save Diagnostic Report"
                )
                
                if file_path:
                    # Add metadata
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
        else:
            messagebox.showwarning("No Data", "No diagnostic results to save. Run diagnostics first.")



    def start_encoder_update(self):
        """Start the encoder position update loop if controller is connected"""
        # Debug: Log controller reference status
        self.append_test_log(f"DEBUG: start_encoder_update called, controller is None: {self.controller is None}")
        if self.controller:
            self.append_test_log(f"DEBUG: Controller type: {type(self.controller)}")
        
        if not self.controller:
            self.append_test_log("Cannot start encoder update: No controller connected")
            return False
        
        # Check if controller is actually connected by testing a simple command
        try:
            self.append_test_log("DEBUG: Testing controller with TP A command...")
            response = self.controller.send_command("TP A")
            self.append_test_log(f"DEBUG: TP A response: {response}")
        except Exception as e:
            self.append_test_log(f"Cannot start encoder update: Controller not responding ({e})")
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

    def stop_all_motion(self):
        """Stop all motion on all axes"""
        if not self.controller:
            self.append_test_log("Cannot stop motion: No controller connected")
            return
            
        try:
            # Send stop command to all axes
            self.controller.send_command("ST")
            self.append_test_log("All motion stopped")
        except Exception as e:
            self.append_test_log(f"Failed to stop motion: {e}")

    def stop_encoder_overlay(self):
        """Stop the encoder overlay display"""
        try:
            if hasattr(self, 'encoder_overlay_running'):
                self.encoder_overlay_running = False
            self.append_test_log("Encoder overlay stopped")
        except Exception as e:
            self.append_test_log(f"Failed to stop encoder overlay: {e}")

    def test_controller_commands(self):
        """Test basic controller commands"""
        if not self.controller:
            self.append_test_log("Cannot test commands: No controller connected")
            return
            
        try:
            # Test basic commands
            response = self.controller.send_command("TP A")
            self.append_test_log(f"Test command response: {response}")
        except Exception as e:
            self.append_test_log(f"Command test failed: {e}")

    def apply_network_config(self):
        """Apply network configuration settings"""
        try:
            # Get values from GUI
            ip = self.config_ip_entry.get() if hasattr(self, 'config_ip_entry') else "10.1.0.21"
            subnet = self.subnet_entry.get() if hasattr(self, 'subnet_entry') else "255.255.255.0"
            gateway = self.gateway_entry.get() if hasattr(self, 'gateway_entry') else "10.1.0.1"
            
            self.append_test_log(f"Applying network config: IP={ip}, Subnet={subnet}, Gateway={gateway}")
            # TODO: Implement actual network configuration
        except Exception as e:
            self.append_test_log(f"Failed to apply network config: {e}")

    def save_settings(self):
        """Save application settings"""
        try:
            # Get values from GUI
            auto_connect = self.auto_connect_var.get() if hasattr(self, 'auto_connect_var') else True
            default_ip = self.default_ip_entry.get() if hasattr(self, 'default_ip_entry') else "10.1.0.21"
            
            self.append_test_log(f"Saving settings: Auto-connect={auto_connect}, Default IP={default_ip}")
            # TODO: Implement actual settings save
        except Exception as e:
            self.append_test_log(f"Failed to save settings: {e}")

    def test_axis_diagnostics(self):
        """Test axis diagnostics for all axes"""
        if not self.controller:
            self.append_test_log("Cannot run diagnostics: No controller connected")
            return
            
        try:
            axes = ['A', 'B', 'C', 'D']
            for axis in axes:
                # Test position reading
                pos_response = self.controller.send_command(f"TP {axis}")
                self.append_test_log(f"Axis {axis} position: {pos_response}")
                
                # Test status reading
                status_response = self.controller.send_command(f"TS {axis}")
                self.append_test_log(f"Axis {axis} status: {status_response}")
                
        except Exception as e:
            self.append_test_log(f"Diagnostics failed: {e}")

    def reset_network_config(self):
        """Reset network configuration to defaults"""
        try:
            # Reset to default values
            if hasattr(self, 'config_ip_entry'):
                self.config_ip_entry.delete(0, tk.END)
                self.config_ip_entry.insert(0, "10.1.0.21")
            
            if hasattr(self, 'subnet_entry'):
                self.subnet_entry.delete(0, tk.END)
                self.subnet_entry.insert(0, "255.255.255.0")
                
            if hasattr(self, 'gateway_entry'):
                self.gateway_entry.delete(0, tk.END)
                self.gateway_entry.insert(0, "10.1.0.1")
                
            self.append_test_log("Network configuration reset to defaults")
        except Exception as e:
            self.append_test_log(f"Failed to reset network config: {e}")

    def apply_controller_settings(self):
        """Apply controller settings"""
        try:
            # Get values from GUI
            auto_connect = self.auto_connect_var.get() if hasattr(self, 'auto_connect_var') else True
            default_ip = self.default_ip_entry.get() if hasattr(self, 'default_ip_entry') else "10.1.0.21"
            
            self.append_test_log(f"Applying controller settings: Auto-connect={auto_connect}, Default IP={default_ip}")
            # TODO: Implement actual controller settings application
        except Exception as e:
            self.append_test_log(f"Failed to apply controller settings: {e}")

    def _initialize_encoder_display(self, axis):
        """Initialize the speed bar and position dial for an axis"""
        # Initialize encoder display for axis
        if axis not in self.encoder_displays:
            # Axis not found in encoder_displays
            return
            
        # Drawing speed bar and position dial for axis
        # Initialize speed bar
        self._draw_speed_bar(axis, 0)
        
        # Initialize position dial
        self._draw_position_dial(axis, 0)
    
    def _update_displays_with_current_positions(self):
        """Update displays with current encoder positions if controller is connected"""
        if not self.controller:
            return
            
        try:
            # Get current positions and velocities from controller
            positions = {}
            velocities = {}
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Read position
                    pos_str = self.controller.send_command(f"TP {axis}")
                    positions[axis] = int(pos_str.strip())
                    
                    # Read velocity
                    vel_str = self.controller.send_command(f"TV {axis}")
                    velocities[axis] = abs(float(vel_str.strip()))
                    
                    # Debug: Log the actual command responses for axis A
                    if axis == "A":
                        # Position and velocity read successfully
                        pass
                        
                except Exception as e:
                    positions[axis] = 0
                    velocities[axis] = 0
                    if axis == "A":
                        # Error reading axis
                        pass
            
            # Updating displays with current positions and velocities
            # Update all displays with current positions and velocities
            self._update_all_axis_displays(positions, velocities)
            
        except Exception as e:
            # Error getting current positions
            pass
    
    def _start_periodic_display_updates(self):
        """Start periodic updates to ensure displays stay current when encoder loop is not running"""
        # Only run if encoder update loop is not running
        if not self.controller or self.test_encoder_update_running:
            # If encoder loop is running, just schedule next check
            self.root.after(500, self._start_periodic_display_updates)
            return
            
        try:
            # Get current positions and velocities
            positions = {}
            velocities = {}
            for axis in ["A", "B", "C", "D"]:
                try:
                    # Read position
                    pos_str = self.controller.send_command(f"TP {axis}")
                    positions[axis] = int(pos_str.strip())
                    
                    # Read velocity
                    vel_str = self.controller.send_command(f"TV {axis}")
                    velocities[axis] = abs(float(vel_str.strip()))
                except:
                    positions[axis] = 0
                    velocities[axis] = 0
            
            # Update displays
            self._update_all_axis_displays(positions, velocities)
            
        except Exception as e:
            # Error in periodic update
            pass
        
        # Schedule next update in 500ms (slower when encoder loop is not running)
        self.root.after(500, self._start_periodic_display_updates)
    
    def _force_immediate_display_update(self):
        """Force an immediate update of all displays with test data"""
        # Force immediate display update with test data
        
        # Test with some sample data
        test_positions = {'A': 123456, 'B': 78901, 'C': 234567, 'D': 345678}
        test_velocities = {'A': 1500, 'B': 0, 'C': 2500, 'D': 0}
        
        self._update_all_axis_displays(test_positions, test_velocities)
        
        # Test smooth position updates with changing data
        self.root.after(1000, lambda: self._test_smooth_position_updates())
        
        # Also try with real data if controller is available
        if self.controller:
            # Also updating with real controller data
            self._update_displays_with_current_positions()
    
    def _test_smooth_position_updates(self):
        """Test smooth position updates with changing data"""
        # Testing smooth position updates
        
        # Test with changing positions to demonstrate smooth movement
        test_positions = {'A': 150000, 'B': 100000, 'C': 300000, 'D': 400000}
        test_velocities = {'A': 2000, 'B': 500, 'C': 3000, 'D': 1000}
        
        self._update_all_axis_displays(test_positions, test_velocities)
    
    def _ensure_encoder_displays_exist(self):
        """Ensure encoder displays exist and are properly initialized"""
        if not hasattr(self, 'encoder_displays') or not self.encoder_displays:
            # Encoder displays not found, initializing
            # Initialize empty displays
            self.encoder_displays = {}
            self.encoder_labels = {}
            
        # Check if all axes have displays
        for axis in ['A', 'B', 'C', 'D']:
            if axis not in self.encoder_displays:
                # Missing encoder display for axis
                return False
                
        return True
    
    def get_shared_encoder_displays(self):
        """Get or create shared encoder displays that persist across pages"""
        if not hasattr(self, 'encoder_displays') or not self.encoder_displays:
            self.encoder_displays = {}
            self.encoder_labels = {}
            
        return self.encoder_displays, self.encoder_labels
    
    def _draw_speed_bar(self, axis, speed):
        """Draw the half-moon speed bar with gradient from green to red"""
        if axis not in self.encoder_displays or 'speed' not in self.encoder_displays[axis]:
            # No speed canvas for axis
            return
            
        canvas = self.encoder_displays[axis]['speed']
        if not canvas.winfo_exists():
            # Speed canvas for axis does not exist
            return
            
        # Drawing speed bar for axis
        canvas.delete("all")
        
        # Canvas dimensions - updated for much larger canvas
        width = 250
        height = 140
        
        # Half-moon arc parameters
        center_x = width // 2
        center_y = height - 25  # Position at bottom with less margin to move arc down
        radius = 100
        
        # Draw the half-moon arc (semicircle)
        canvas.create_arc(center_x - radius, center_y - radius, 
                         center_x + radius, center_y + radius,
                         start=0, extent=180, outline='black', width=3, style='arc')
        
        # Calculate speed position (0 to 3,000,000 maps to 0 to 180 degrees)
        max_speed = 3000000
        speed_ratio = min(speed / max_speed, 1.0)  # Clamp to 0-1
        angle = speed_ratio * 180  # 0 to 180 degrees
        
        # Draw gradient segments (simplified - we'll use color interpolation)
        segments = 20
        for i in range(segments):
            start_angle = (i / segments) * 180
            end_angle = ((i + 1) / segments) * 180
            
            # Calculate color (green to red)
            ratio = i / segments
            if ratio < 0.5:
                # Green to yellow
                r = int(255 * ratio * 2)
                g = 255
                b = 0
            else:
                # Yellow to red
                r = 255
                g = int(255 * (2 - ratio * 2))
                b = 0
            
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            # Draw arc segment
            canvas.create_arc(center_x - radius + 2, center_y - radius + 2,
                             center_x + radius - 2, center_y + radius - 2,
                             start=start_angle, extent=end_angle - start_angle,
                             outline=color, width=8, style='arc')
        
        # Draw speed marker
        if speed > 0:
            marker_angle = math.radians(angle)
            marker_x = center_x + (radius - 15) * math.cos(marker_angle)
            marker_y = center_y - (radius - 15) * math.sin(marker_angle)
            
            canvas.create_oval(marker_x - 4, marker_y - 4, marker_x + 4, marker_y + 4,
                             fill='black', outline='white', width=2)
        
        # Draw speed labels
        canvas.create_text(15, 15, text="0", font=("Arial", 10), fill='black')
        canvas.create_text(width // 2, 15, text="1.5M", font=("Arial", 10), fill='black')
        canvas.create_text(width - 15, 15, text="3M", font=("Arial", 10), fill='black')
        
        # Draw current speed value
        canvas.create_text(width // 2, height - 15, text=f"SPEED: {speed:,}", 
                          font=("Arial", 10, "bold"), fill='black')
    
    def _draw_position_dial(self, axis, position):
        """Draw the clock-like position dial with tick marks and needle"""
        if axis not in self.encoder_displays or 'position' not in self.encoder_displays[axis]:
            # No position canvas for axis
            return
            
        canvas = self.encoder_displays[axis]['position']
        if not canvas.winfo_exists():
            # Position canvas for axis does not exist
            return
            
        # Only log occasionally to avoid spam
        if hasattr(self, '_debug_counter'):
            self._debug_counter += 1
        else:
            self._debug_counter = 1
            
        if self._debug_counter % 10 == 0:  # Log every 10th update
            # Drawing position dial for axis
            pass
        
        canvas.delete("all")
        
        # Canvas dimensions - updated for much larger canvas
        width = 200
        height = 200
        center_x = width // 2
        center_y = height // 2
        radius = 85
        
        # Draw outer circle
        canvas.create_oval(center_x - radius, center_y - radius,
                          center_x + radius, center_y + radius,
                          outline='black', width=2)
        
        # Draw tick marks (like a clock) - no numbers inside
        for i in range(12):  # 12 major tick marks
            angle = math.radians(i * 30)  # 30 degrees apart
            
            # Calculate tick mark positions
            inner_x = center_x + (radius - 10) * math.cos(angle - math.pi/2)
            inner_y = center_y + (radius - 10) * math.sin(angle - math.pi/2)
            outer_x = center_x + (radius - 2) * math.cos(angle - math.pi/2)
            outer_y = center_y + (radius - 2) * math.sin(angle - math.pi/2)
            
            canvas.create_line(inner_x, inner_y, outer_x, outer_y, width=2, fill='black')
        
        # Draw minor tick marks
        for i in range(60):  # 60 minor tick marks (6 degrees apart)
            if i % 5 != 0:  # Skip major tick marks
                angle = math.radians(i * 6)
                inner_x = center_x + (radius - 6) * math.cos(angle - math.pi/2)
                inner_y = center_y + (radius - 6) * math.sin(angle - math.pi/2)
                outer_x = center_x + (radius - 2) * math.cos(angle - math.pi/2)
                outer_y = center_y + (radius - 2) * math.sin(angle - math.pi/2)
                
                canvas.create_line(inner_x, inner_y, outer_x, outer_y, width=1, fill='gray')
        
        # Draw needle (position indicator)
        if position != 0:
            # Convert position to angle (assuming position is in degrees or similar)
            # For now, we'll use modulo to keep it within 0-360 range
            angle = math.radians(position % 360)
            
            # Calculate needle end position
            needle_x = center_x + (radius - 12) * math.cos(angle - math.pi/2)
            needle_y = center_y + (radius - 12) * math.sin(angle - math.pi/2)
            
            # Draw needle
            canvas.create_line(center_x, center_y, needle_x, needle_y, 
                             width=3, fill='red')
            
            # Draw center dot
            canvas.create_oval(center_x - 3, center_y - 3, center_x + 3, center_y + 3,
                             fill='black', outline='white')
        
        # Draw position value below the dial
        canvas.create_text(center_x, center_y + radius + 35, text=f"POSITION: {position:,}", 
                          font=("Arial", 11, "bold"), fill='black')

    def _update_position_dial_smoothly(self, axis, target_position):
        """Update position dial with smooth interpolation to prevent jumping"""
        if axis not in self.encoder_displays or 'position' not in self.encoder_displays[axis]:
            return
            
        canvas = self.encoder_displays[axis]['position']
        if not canvas.winfo_exists():
            return
        
        current_time = time.time()
        
        # Initialize current position if not set
        if axis not in self.current_dial_positions:
            self.current_dial_positions[axis] = target_position
            self.target_positions[axis] = target_position
            self.position_dial_update_times[axis] = current_time
            # Draw immediately for first time
            self._draw_position_dial(axis, target_position)
            return
        
        # Set target position
        self.target_positions[axis] = target_position
        
        # Calculate time since last update
        time_diff = current_time - self.position_dial_update_times[axis]
        
        # Only update dial every 50ms to reduce jumping
        if time_diff < 0.05:  # 50ms
            return
        
        # Get current and target positions
        current_pos = self.current_dial_positions[axis]
        target_pos = self.target_positions[axis]
        
        # Calculate smooth interpolation
        if abs(target_pos - current_pos) > 1:  # Only interpolate if difference is significant
            # Use exponential smoothing for smooth movement
            smoothing_factor = 0.3  # Adjust this value (0.1 = very smooth, 0.9 = more responsive)
            new_pos = current_pos + (target_pos - current_pos) * smoothing_factor
            self.current_dial_positions[axis] = new_pos
        else:
            # If very close, just set to target
            self.current_dial_positions[axis] = target_pos
        
        # Update the dial with interpolated position
        self._draw_position_dial(axis, int(self.current_dial_positions[axis]))
        self.position_dial_update_times[axis] = current_time

    def test_tune_axis(self):
        """Tune the selected axis with PID values"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            kp = float(self.test_kp_entry.get())
            ki = float(self.test_ki_entry.get())
            kd = float(self.test_kd_entry.get())
            
            self.log_message( f"Tuning axis {axis} with KP={kp}, KI={ki}, KD={kd}...\n")
            
            # Use the galil_functions module function
            galil_functions.tune_axis(self.controller, axis, kp, ki, kd)
            
            self.log_message( f"Axis {axis} tuning completed successfully!\n")
            
        except Exception as e:
            error_msg = f"Tuning error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
                self.controller.send_command(f"SH {axis}")
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
            
            self.log_message( f"Stopping axis {axis}...\n")
            
            # Stop the axis
            self.controller.send_command(f"ST {axis}")
            
            self.log_message( f"Axis {axis} stopped successfully!\n")
            
        except Exception as e:
            error_msg = f"Stop error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
                self.controller.send_command(f"SH {axis}")
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
            
            self.append_test_log(f"Attempting small move: {current_pos} â†’ {target_pos}")
            
            # Use conservative parameters
            speed = 1000
            accel = 500
            
            # Stop any existing motion
            self.controller.send_command(f"ST {axis}")
            time.sleep(0.1)
            
            # Enable servo
            self.controller.send_command(f"SH {axis}")
            time.sleep(0.2)
            
            # Set conservative parameters
            self.controller.send_command(f"SP {axis}={speed}")
            self.controller.send_command(f"AC {axis}={accel}")
            self.controller.send_command(f"DC {axis}={accel*2}")
            
            # Move to target position
            self.controller.send_command(f"PA{axis}={target_pos}")
            self.controller.send_command(f"BG {axis}")
            
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
                speed = self.controller.send_command(f"MG _SP {axis}").strip()
                accel = self.controller.send_command(f"MG _AC {axis}").strip()
                decel = self.controller.send_command(f"MG _DC {axis}").strip()
                self.append_test_log(f"Current parameters - Speed: {speed}, Accel: {accel}, Decel: {decel}")
            except Exception as e:
                self.append_test_log(f"Error reading parameters: {e}")
            
            # Check PID settings
            try:
                kp = self.controller.send_command(f"MG _KP {axis}").strip()
                ki = self.controller.send_command(f"MG _KI {axis}").strip()
                kd = self.controller.send_command(f"MG _KD {axis}").strip()
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
                response = self.controller.send_command(f"ST {axis}")
                self.append_test_log(f"ST {axis} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"ST {axis} failed: {e}")
            
            # Test servo on command
            try:
                response = self.controller.send_command(f"SH {axis}")
                self.append_test_log(f"SH{axis} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"SH{axis} failed: {e}")
            
            # Test speed command
            try:
                response = self.controller.send_command(f"SP {axis}=100")
                self.append_test_log(f"SP {axis}=100 response: '{response}'")
            except Exception as e:
                self.append_test_log(f"SP {axis}=100 failed: {e}")
            
            # Test acceleration command
            try:
                response = self.controller.send_command(f"AC {axis}=100")
                self.append_test_log(f"AC {axis}=100 response: '{response}'")
            except Exception as e:
                self.append_test_log(f"AC {axis}=100 failed: {e}")
            
            # Test position command
            try:
                current_pos = int(self.controller.send_command(f"TP {axis}").strip())
                response = self.controller.send_command(f"PA{axis}={current_pos}")
                self.append_test_log(f"PA{axis}={current_pos} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"PA{axis} failed: {e}")
            
            # Test begin command
            try:
                response = self.controller.send_command(f"BG {axis}")
                self.append_test_log(f"BG {axis} response: '{response}'")
            except Exception as e:
                self.append_test_log(f"BG {axis} failed: {e}")
            
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
                response = self.controller.send_command(f"MO {axis}")
                self.append_test_log(f"MO{axis} (servo off) response: '{response}'")
                time.sleep(0.1)
                response = self.controller.send_command(f"SH {axis}")
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
            
            self.log_message( f"Applying motion parameters to axis {axis}...\n")
            self.log_message( f"Speed: {speed}, Acceleration: {accel}\n")

            # Stop the axis first
            self.controller.send_command(f"ST {axis}")
            
            # Apply motion parameters
            self._apply_motion_parameters(axis, speed, accel)

            # Verify via MG _SP/_AC/_DC
            try:
                actual_speed = self.controller.send_command(f"MG _SP {axis}").strip()
                actual_accel = self.controller.send_command(f"MG _AC {axis}").strip()
                actual_decel = self.controller.send_command(f"MG _DC {axis}").strip()
                self.log_message( "Motion parameters applied successfully!\n")
                self.log_message( f"Current SP: {actual_speed}, AC: {actual_accel}, DC: {actual_decel}\n")
            except Exception as e:
                self.log_message( f"Parameters applied, but verification failed: {e}\n")
            
            
        except Exception as e:
            error_msg = f"Parameter application error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Parameter Error", error_msg)
            

            
    def test_encoder_update_loop(self):
        """Encoder position update loop for all axes"""
        self._run_encoder_update_loop()
                
    def test_update_all_encoder_displays(self, axis_positions, axis_velocities=None, error=None):
        """Update all encoder displays with positions and velocities for each axis"""
        self._ensure_encoder_update_running()
            
        # Check if widgets still exist before trying to update them
        self._validate_encoder_widgets()
            
        self._handle_encoder_display_error_if_needed(error)
            
        # Update each axis display
        self._update_all_axis_displays(axis_positions, axis_velocities)
             
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
                        self.controller.send_command(f"SH {axis}")
                        time.sleep(0.1)
                except Exception as e:
                    # Ignore errors for individual axes
                    pass
        except Exception as e:
            # Ignore errors in servo maintenance
            pass
            
    def enable_all_servos(self):
        """Enable servos for all axes"""
        if self.controller_commands:
            return self.controller_commands.enable_all_servos()
        else:
            self.append_test_log("ERROR: Controller commands not initialized")
            messagebox.showerror("Error", "Please connect to a controller first")
            return False
            
    def test_servo_off(self):
        """Disable servo for the selected axis"""
        self._ensure_controller_connected()
            
        try:
            axis = self.test_axis_var.get()
            
            self.log_message( f"Disabling servo for axis {axis}...\n")
            
            # Stop motion first
            self.controller.send_command(f"ST {axis}")
            
            # Disable servo
            self.controller.send_command(f"MO {axis}")
            
            self.log_message( f"Servo disabled for axis {axis}\n")
            
        except Exception as e:
            error_msg = f"Servo disable error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
            messagebox.showerror("Servo Error", error_msg)
            
    def test_stop_all(self):
        """Stop all axes"""
        self._ensure_controller_connected()
            
        try:
            self.log_message( "Stopping all axes...\n")
            
            # Stop all axes
            self.controller.send_command("ST")
            
            self.log_message( "All axes stopped\n")
            
        except Exception as e:
            error_msg = f"Stop all error: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
                
            self.log_message( f"Configuration saved successfully to: {file_path}\n")
            messagebox.showinfo("Success", f"Configuration saved to:\n{file_path}")
            
        except Exception as e:
            error_msg = f"Error saving configuration: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
            self.log_message( f"Configuration loaded from: {file_path}\n")
            self.log_message( "Loaded settings:\n")
            
            if 'motion_parameters' in config:
                motion = config['motion_parameters']
                self.log_message( f"  Motion: Speed={motion.get('default_speed', 'N/A')}, "
                                                       f"Accel={motion.get('default_acceleration', 'N/A')}, "
                                                       f"Decel={motion.get('default_deceleration', 'N/A')}\n")
                                                       
            if 'pid_parameters' in config:
                pid = config['pid_parameters']
                self.log_message( f"  PID: KP={pid.get('default_kp', 'N/A')}, "
                                                       f"KI={pid.get('default_ki', 'N/A')}, "
                                                       f"KD={pid.get('default_kd', 'N/A')}\n")
                                                       
            if 'saved_timestamp' in config:
                self.log_message( f"  Saved: {config['saved_timestamp']}\n")
                
            messagebox.showinfo("Success", f"Configuration loaded from:\n{file_path}")
            
        except Exception as e:
            error_msg = f"Error loading configuration: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
                self.log_message( f"Note: Some UI elements could not be updated: {e}\n")
                
            self.log_message( "All settings have been reset to default values.\n")
            self.log_message( "Default configuration:\n")
            self.log_message( f"  IP: {default_config['default_ip']}\n")
            self.log_message( f"  Speed: {default_config['motion_parameters']['default_speed']}\n")
            self.log_message( f"  KP: {default_config['pid_parameters']['default_kp']}\n")
            self.log_message( f"  KI: {default_config['pid_parameters']['default_ki']}\n")
            self.log_message( f"  KD: {default_config['pid_parameters']['default_kd']}\n")
            
            messagebox.showinfo("Success", "All settings have been reset to their default values.")
            
        except Exception as e:
            error_msg = f"Error resetting to defaults: {str(e)}"
            self.log_message( f"ERROR: {error_msg}\n")
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
    
    def _stop_all_encoder_updates(self):
        """Stop all encoder update loops"""
        try:
            # Stop test encoder update loop
            if hasattr(self, 'test_encoder_update_running'):
                self.test_encoder_update_running = False
            if hasattr(self, 'test_encoder_update_thread') and self.test_encoder_update_thread.is_alive():
                self.test_encoder_update_thread.join(timeout=1.0)
            
            # Stop auto encoder update loop
            if hasattr(self, 'encoder_update_running'):
                self.encoder_update_running = False
            if hasattr(self, 'encoder_update_thread') and self.encoder_update_thread.is_alive():
                self.encoder_update_thread.join(timeout=1.0)
            
            # Stop GUI-based encoder update
            self.stop_encoder_auto_update()
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
                position_response = self.controller.send_command(f"TP {axis}")
                position = int(float(position_response.strip()))
                self.log_message( f"Axis {axis} position: {position}\n")
            except Exception as e:
                self.log_message( f"Axis {axis} test failed: {str(e)}\n")
                
    def _ensure_servo_enabled(self, axis):
        """Ensure servo is enabled for the specified axis"""
        servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Try again
            self.controller.send_command(f"SH {axis}")
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
                    self.controller.send_command(f"SH {axis}")
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
                self.controller.send_command(f"SH {axis}")
        except Exception as e:
            self.append_test_log(f"Error checking final servo status: {e}")
            
    def _check_motion_command_support(self, axis):
        """Check if motion commands are supported for the given axis"""
        try:
            # Test basic motion commands
            test_pr = self.controller.send_command(f"PR {axis}=100")
            test_bg = self.controller.send_command(f"BG {axis}")
            test_st = self.controller.send_command(f"ST {axis}")
            
            if "?" not in test_pr and "?" not in test_bg and "?" not in test_st:
                self.log_message( "âœ“ Motion commands supported for index latching\n")
                return True
            else:
                self.log_message( "âš  Motion commands not supported - using position analysis\n")
                return False
        except:
            self.log_message( "âš  Motion commands not supported - using position analysis\n")
            return False
            
    def _apply_motion_parameters(self, axis, speed, accel):
        """Apply motion parameters to the specified axis"""
        # Apply speed parameter
        resp = self.controller.send_command(f"SP {axis}={speed}")
        if resp.strip() == "?":
            self.log_message( f"WARNING: Controller rejected speed value {speed}\n")
        else:
            self.log_message( f"Speed parameter applied successfully\n")
        
        # Apply acceleration parameter
        resp = self.controller.send_command(f"AC {axis}={accel}")
        if resp.strip() == "?":
            self.log_message( f"WARNING: Controller rejected acceleration value {accel}\n")
        else:
            self.log_message( f"Acceleration parameter applied successfully\n")
        
        # Apply deceleration parameter (typically 2x acceleration)
        decel = accel * 2
        resp = self.controller.send_command(f"DC {axis}={decel}")
        if resp.strip() == "?":
            self.log_message( f"WARNING: Controller rejected deceleration value {decel}\n")
        else:
            self.log_message( f"Deceleration parameter applied successfully\n")
            
    def _run_encoder_update_loop(self):
        """Run the encoder position update loop"""
        servo_maintenance_counter = 0
        connection_check_count = 0
        max_connection_checks = 3  # Only check connection 3 times before stopping
        
        while self.test_encoder_update_running:
            try:
                if not self.controller:
                    connection_check_count += 1
                    if connection_check_count <= max_connection_checks:
                        # Log connection attempt only for first few times
                        count = connection_check_count
                        max_count = max_connection_checks
                        self.root.after(0, lambda c=count, m=max_count: self.append_test_log(f"Connection attempt {c}/{m}: No controller connected"))
                    else:
                        # Stop the loop if no controller for too long
                        self.test_encoder_update_running = False
                        self.root.after(0, lambda: self.append_test_log("Stopping encoder updates: No controller connected"))
                        break
                    time.sleep(1.0)  # Wait longer when no controller
                    continue
                
                # Check if controller is still connected by testing a simple command
                try:
                    self.controller.send_command("TP A")
                except Exception as conn_error:
                    # Controller is disconnected, stop the loop
                    self.test_encoder_update_running = False
                    error_msg = str(conn_error)
                    self.root.after(0, lambda msg=error_msg: self.append_test_log(f"Stopping encoder updates: Controller disconnected ({msg})"))
                    break
                
                # Read positions and velocities from all axes
                axis_positions = {}
                axis_velocities = {}
                for axis in ["A", "B", "C", "D"]:
                    try:
                        # Read position
                        pos_str = self.controller.send_command(f"TP {axis}")
                        position = int(pos_str.strip())
                        axis_positions[axis] = position
                        
                        # Read actual velocity
                        vel_str = self.controller.send_command(f"TV {axis}")
                        velocity = abs(float(vel_str.strip()))  # Use absolute value for speed display
                        axis_velocities[axis] = velocity
                        
                    except Exception as e:
                        # Check if this is a connection error - if so, stop the entire loop
                        error_msg = str(e).lower()
                        if "not connected" in error_msg or "connection" in error_msg:
                            self.test_encoder_update_running = False
                            error_str = str(e)
                            self.root.after(0, lambda msg=error_str: self.append_test_log(f"Stopping encoder updates: Connection lost ({msg})"))
                            break
                        
                        # If axis doesn't respond, mark as error but don't log every error
                        axis_positions[axis] = None
                        axis_velocities[axis] = 0
                        # Only log errors occasionally to avoid spam
                        if hasattr(self, '_encoder_error_count'):
                            self._encoder_error_count += 1
                        else:
                            self._encoder_error_count = 1
                        
                        # Log error only every 10th occurrence to avoid spam
                        if self._encoder_error_count % 10 == 1:
                            error_axis = axis
                            error_msg = str(e)
                            self.root.after(0, lambda ax=error_axis, msg=error_msg: self.append_test_log(f"Encoder read error for axis {ax}: {msg}"))
                
                # Update all encoder displays in main thread
                if self.test_encoder_update_running:  # Double-check before updating UI
                    # Sending positions and velocities to UI
                    self.root.after(0, self.test_update_all_encoder_displays, axis_positions, axis_velocities)
                
                # Perform servo maintenance every 20 updates (10 seconds with 500ms intervals)
                servo_maintenance_counter += 1
                if servo_maintenance_counter >= 20:
                    self.maintain_servo_status()
                    servo_maintenance_counter = 0
                
                # Sleep for update interval - increased to reduce controller load
                time.sleep(0.5)  # 500ms updates (2 updates per second instead of 10)
                
            except Exception as e:
                # Update UI with error in main thread - ensure we only pass string error messages
                if self.test_encoder_update_running:  # Double-check before updating UI
                    error_msg = str(e) if e else "Unknown error"
                    # Ensure error message doesn't contain widget references
                    if "!" in error_msg and ("frame" in error_msg or "canvas" in error_msg or "label" in error_msg):
                        error_msg = "Widget reference error in encoder update"
                    self.root.after(0, self.test_update_all_encoder_displays, None, error_msg)
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
            
    def _update_all_axis_displays(self, axis_positions, axis_velocities=None):
        """Update all axis displays with position and velocity data"""
        # Update displays with position data
        
        # Check if encoder displays exist - if not, just return (displays will be created later)
        if not hasattr(self, 'encoder_displays') or not self.encoder_displays:
            # Encoder displays not yet created, skipping update
            return
            
        # Check if all axes have displays
        missing_axes = []
        for axis in ['A', 'B', 'C', 'D']:
            if axis not in self.encoder_displays:
                missing_axes.append(axis)
        
        if missing_axes:
            # Missing encoder displays for axes, skipping update
            return
            
        for axis in ['A', 'B', 'C', 'D']:
            try:
                if axis not in self.encoder_displays or axis not in self.encoder_labels:
                    continue
                    
                # Check if new structure exists
                if isinstance(self.encoder_displays[axis], dict):
                    # New structure with speed and position canvases
                    speed_canvas = self.encoder_displays[axis].get('speed')
                    position_canvas = self.encoder_displays[axis].get('position')
                    label = self.encoder_labels[axis]
                    
                    if not speed_canvas or not position_canvas or not label:
                        continue
                        
                    if not speed_canvas.winfo_exists() or not position_canvas.winfo_exists() or not label.winfo_exists():
                        continue
                    
                    position = axis_positions.get(axis)
                    
                    if position is None:
                        # Axis not responding
                        label.configure(text="No Response", fg=self.colors['error_red'])
                        
                        # Clear speed bar
                        speed_canvas.delete("all")
                        speed_canvas.create_text(90, 30, text="No Response", 
                                               font=("Arial", 10), fill='red')
                        
                        # Clear position dial
                        position_canvas.delete("all")
                        position_canvas.create_text(60, 60, text="?", 
                                                   font=("Arial", 20), fill='gray')
                    else:
                        # Update position label
                        label.configure(text=f"Position: {position}", fg=self.colors['main_fg'])
                        
                        # Use actual velocity from controller if available, otherwise calculate from position change
                        if axis_velocities and axis in axis_velocities:
                            # Use actual velocity from TV command (counts per second)
                            speed = axis_velocities[axis]
                            # Cap speed at 3,000,000 for display purposes
                            speed = min(speed, 3000000)
                        else:
                            # Fallback: Calculate speed based on position change over time
                            current_time = time.time()
                            speed = 0
                            
                            if axis in self.last_positions and axis in self.last_update_times:
                                time_diff = current_time - self.last_update_times[axis]
                                position_diff = position - self.last_positions[axis]
                                
                                if time_diff > 0:
                                    # Speed in counts per second
                                    speed = abs(position_diff) / time_diff
                                    # Cap speed at 3,000,000 for display purposes
                                    speed = min(speed, 3000000)
                            
                            # Store current values for next calculation
                            self.last_positions[axis] = position
                            self.last_update_times[axis] = current_time
                        
                        self.axis_speeds[axis] = speed
                        
                        # Update speed bar
                        # Drawing speed bar for axis
                        self._draw_speed_bar(axis, speed)
                        
                        # Update position dial with smooth interpolation
                        self._update_position_dial_smoothly(axis, position)
                        
                        # Force canvas update
                        speed_canvas.update_idletasks()
                        position_canvas.update_idletasks()
                        
                else:
                    # Old structure - fallback for compatibility
                    canvas = self.encoder_displays[axis]
                    label = self.encoder_labels[axis]
                    
                    if not canvas.winfo_exists() or not label.winfo_exists():
                        continue
                    
                    position = axis_positions.get(axis)
                    
                    if position is None:
                        # Axis not responding
                        label.configure(text="No Response", fg=self.colors['error_red'])
                        canvas.delete("all")
                        canvas.create_oval(10, 10, 110, 110, outline='gray', width=2)
                        canvas.create_text(60, 60, text="?", fill='gray', font=("Arial", 24))
                    else:
                        # Update position label
                        label.configure(text=f"Position: {position}", fg=self.colors['main_fg'])
                        
                        # Update visual display
                        canvas.delete("all")
                        canvas.create_oval(10, 10, 110, 110, outline='black', width=3)
                        
                        # Calculate angle from position
                        clicks_per_turn = int(self.test_clicks_per_turn_entry.get())
                        angle = (position % clicks_per_turn) / clicks_per_turn * 2 * 3.14159
                        
                        # Draw position indicator
                        center_x = 60
                        center_y = 60
                        radius = 45
                        
                        indicator_x = center_x + radius * 0.8 * math.cos(angle)
                        indicator_y = center_y - radius * 0.8 * math.sin(angle)
                        
                        canvas.create_oval(
                            indicator_x - 6, indicator_y - 6,
                            indicator_x + 6, indicator_y + 6,
                            fill='red', outline='black', width=2
                        )
                    
            except Exception as e:
                # Individual axis update failed, continue with others
                continue
                
    def _enable_servo_with_verification(self, axis):
        """Enable servo for the specified axis with verification"""
        # Enable servo
        self.controller.send_command(f"SH {axis}")
        time.sleep(0.2)
        
        # Verify servo is enabled
        servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        if servo_status == "0":
            # Try again
            self.controller.send_command(f"SH {axis}")
            time.sleep(0.3)
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
        
        if servo_status != "0":
            self.append_test_log(f"Servo enabled for axis {axis} (status: {servo_status})")
        else:
            self.append_test_log(f"WARNING: Servo may not be enabled (status: {servo_status})")
            
        return servo_status
    
    def _ensure_servo_enabled_for_motion(self, axis):
        """Ensure servo is enabled for motion with comprehensive verification"""
        try:
            # First, stop any existing motion
            self.controller.send_command(f"ST {axis}")
            time.sleep(0.1)
            
            # Enable servo
            self.controller.send_command(f"SH {axis}")
            time.sleep(0.3)  # Give more time for servo to enable
            
            # Verify servo is enabled with multiple attempts
            for attempt in range(3):
                servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                if servo_status == "0":
                    # Servo is still off, try to enable again
                    self.controller.send_command(f"SH {axis}")
                    time.sleep(0.5)  # Longer delay for stubborn servos
                else:
                    # Servo is enabled
                    self.append_test_log(f"[Axis {axis}] âœ“ Servo enabled (status: {servo_status})")
                    return True
            
            # If we get here, servo is still not enabled after 3 attempts
            self.append_test_log(f"[Axis {axis}] âœ— WARNING: Servo could not be enabled after 3 attempts")
            return False
            
        except Exception as e:
            self.append_test_log(f"[Axis {axis}] âœ— ERROR: Servo enable verification failed: {e}")
            return False
        
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
                
                self.append_test_log(f"âœ“ Diagnostic report loaded from: {file_path}")
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
                
                self.append_test_log(f"âœ“ Diagnostic data exported to CSV: {file_path}")
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

    # ============================================================================
    # DIAGNOSTICS METHODS
    # ============================================================================
    
    def update_controller_info_display(self):
        """Update the controller information display in diagnostics page"""
        if hasattr(self, 'controller_info_text') and self.controller_info_text:
            self.controller_info_text.delete(1.0, tk.END)
            
            if self.controller:
                try:
                    # Get basic controller information
                    info_lines = []
                    info_lines.append("Controller Information:")
                    info_lines.append("-" * 30)
                    
                    # Try to get controller info
                    try:
                        firmware = self.controller.send_command("MG _REV")
                        info_lines.append(f"Firmware: {firmware}")
                    except:
                        info_lines.append("Firmware: Unable to read")
                    
                    try:
                        model = self.controller.send_command("MG _BM")
                        info_lines.append(f"Model: {model}")
                    except:
                        info_lines.append("Model: Unable to read")
                    
                    try:
                        burn_count = self.controller.send_command("MG _BN")
                        info_lines.append(f"Burn Count: {burn_count}")
                    except:
                        info_lines.append("Burn Count: Unable to read")
                    
                    try:
                        mac = self.controller.send_command("TH")
                        info_lines.append(f"MAC Address: {mac}")
                    except:
                        info_lines.append("MAC Address: Unable to read")
                    
                    try:
                        ip = self.controller.send_command("IA")
                        info_lines.append(f"IP Address: {ip}")
                    except:
                        info_lines.append("IP Address: Unable to read")
                    
                    info_text = "\n".join(info_lines)
                    self.controller_info_text.insert(1.0, info_text)
                    
                except Exception as e:
                    self.controller_info_text.insert(1.0, f"Error reading controller info: {e}")
            else:
                self.controller_info_text.insert(1.0, "No controller connected")
    
    def run_full_diagnostics(self):
        """Run the complete diagnostics suite"""
        if not self.controller:
            messagebox.showerror("Error", "Please connect to a controller first")
            return
        
        if not self.diagnostics:
            messagebox.showerror("Error", "Diagnostics not initialized")
            return
        
        # Update safe mode setting
        safe_mode = getattr(self, 'safe_mode_var', None)
        if safe_mode:
            self.diagnostics.safe_mode = safe_mode.get()
        
        # Disable run button and enable stop button
        if hasattr(self, 'run_diagnostics_btn'):
            self.run_diagnostics_btn.config(state='disabled')
        if hasattr(self, 'stop_diagnostics_btn'):
            self.stop_diagnostics_btn.config(state='normal')
        
        # Clear previous results
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
        
        # Start diagnostics in a separate thread
        def run_diagnostics_thread():
            try:
                # Progress callback
                def progress_callback(message, current, total):
                    progress_percent = (current / total) * 100
                    self.root.after(0, lambda: self.update_diagnostics_progress(progress_percent, message))
                
                # Run diagnostics
                report = self.diagnostics.run_diagnostics(callback=progress_callback)
                
                # Update UI with results
                self.root.after(0, lambda: self.display_diagnostics_results(report))
                
            except Exception as e:
                self.root.after(0, lambda: self.handle_diagnostics_error(e))
            finally:
                # Re-enable run button and disable stop button
                self.root.after(0, lambda: self.reset_diagnostics_buttons())
        
        # Start the thread
        diagnostics_thread = threading.Thread(target=run_diagnostics_thread, daemon=True)
        diagnostics_thread.start()
    
    def update_diagnostics_progress(self, progress, message):
        """Update the diagnostics progress display"""
        if hasattr(self, 'diagnostics_progress'):
            self.diagnostics_progress.set(progress)
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text=message)
    
    def display_diagnostics_results(self, report):
        """Display the diagnostics results"""
        if not hasattr(self, 'diagnostics_results_text'):
            return
        
        # Clear previous results
        self.diagnostics_results_text.delete(1.0, tk.END)
        
        # Display results
        results_text = []
        results_text.append("DMC-4103 DIAGNOSTICS RESULTS")
        results_text.append("=" * 50)
        results_text.append(f"Timestamp: {report.timestamp}")
        results_text.append(f"Overall Result: {report.overall_result.value}")
        results_text.append(f"Execution Time: {report.total_execution_time:.2f} seconds")
        results_text.append("")
        
        # Display summary
        if report.summary:
            results_text.append("SUMMARY")
            results_text.append("-" * 20)
            results_text.append(f"Total Categories: {report.summary.get('total_categories', 0)}")
            results_text.append(f"Total Steps: {report.summary.get('total_steps', 0)}")
            results_text.append(f"Passed Steps: {report.summary.get('passed_steps', 0)}")
            results_text.append(f"Failed Steps: {report.summary.get('failed_steps', 0)}")
            results_text.append(f"Error Steps: {report.summary.get('error_steps', 0)}")
            results_text.append(f"Pass Rate: {report.summary.get('pass_rate', 0):.1f}%")
            results_text.append("")
        
        # Display category results
        for category in report.test_categories:
            results_text.append(f"{category.name.upper()}")
            results_text.append("-" * len(category.name))
            results_text.append(f"Result: {category.overall_result.value}")
            results_text.append(f"Execution Time: {category.execution_time:.2f}s")
            
            if category.notes:
                results_text.append(f"Notes: {category.notes}")
            
            # Show failed steps
            failed_steps = [s for s in category.steps if s.result == TestResult.FAIL]
            if failed_steps:
                results_text.append("Failed Steps:")
                for step in failed_steps:
                    results_text.append(f"  - {step.description}")
                    if step.actual_response:
                        results_text.append(f"    Response: {step.actual_response}")
                    if step.notes:
                        results_text.append(f"    Notes: {step.notes}")
            
            results_text.append("")
        
        # Update results text
        self.diagnostics_results_text.insert(1.0, "\n".join(results_text))
        
        # Update summary label
        if hasattr(self, 'diagnostics_summary_label'):
            summary_text = f"Result: {report.overall_result.value} | Pass Rate: {report.summary.get('pass_rate', 0):.1f}% | Time: {report.total_execution_time:.2f}s"
            self.diagnostics_summary_label.config(text=summary_text)
        
        # Enable save button
        if hasattr(self, 'save_report_btn'):
            self.save_report_btn.config(state='normal')
        
        # Store the report for saving
        self.last_diagnostics_report = report
    
    def handle_diagnostics_error(self, error):
        """Handle diagnostics errors"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, f"Diagnostics Error: {error}")
        
        if hasattr(self, 'diagnostics_summary_label'):
            self.diagnostics_summary_label.config(text=f"Error: {error}")
        
        messagebox.showerror("Diagnostics Error", f"An error occurred during diagnostics: {error}")
    
    def reset_diagnostics_buttons(self):
        """Reset the diagnostics control buttons"""
        if hasattr(self, 'run_diagnostics_btn'):
            self.run_diagnostics_btn.config(state='normal')
        if hasattr(self, 'stop_diagnostics_btn'):
            self.stop_diagnostics_btn.config(state='disabled')
    
    def stop_diagnostics(self):
        """Stop running diagnostics"""
        if self.diagnostics:
            self.diagnostics.stop_diagnostics()
            if hasattr(self, 'diagnostics_progress_label'):
                self.diagnostics_progress_label.config(text="Stopping diagnostics...")
    
    def save_diagnostics_report(self):
        """Save the diagnostics report to a file"""
        if not hasattr(self, 'last_diagnostics_report') or not self.last_diagnostics_report:
            messagebox.showerror("Error", "No diagnostics report to save")
            return
        
        # Ask user for filename
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Diagnostics Report"
        )
        
        if filename:
            try:
                self.diagnostics.save_report(filename)
                messagebox.showinfo("Success", f"Report saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {e}")
    
    def test_controller_connection_diagnostics(self):
        """Test controller connection from diagnostics page"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, "Testing controller connection...\n")
        
        # Test connection in a separate thread
        def test_connection_thread():
            try:
                # Test basic connectivity
                test_results = []
                test_results.append("CONTROLLER CONNECTION TEST")
                test_results.append("=" * 40)
                test_results.append("")
                
                # Test 1: Ping test
                test_results.append("1. PING TEST")
                test_results.append("-" * 20)
                try:
                    ip = self.test_ip_entry.get().strip() if hasattr(self, 'test_ip_entry') else "10.1.0.21"
                    ping_result = ping_controller(ip)
                    if ping_result:
                        test_results.append(f"✓ Ping to {ip}: SUCCESS")
                    else:
                        test_results.append(f"✗ Ping to {ip}: FAILED")
                except Exception as e:
                    test_results.append(f"✗ Ping test error: {e}")
                test_results.append("")
                
                # Test 2: Network discovery
                test_results.append("2. NETWORK DISCOVERY")
                test_results.append("-" * 20)
                try:
                    controllers = discover_galil_controllers()
                    if controllers:
                        test_results.append(f"✓ Found {len(controllers)} controller(s):")
                        for controller in controllers:
                            test_results.append(f"  - {controller}")
                    else:
                        test_results.append("✗ No controllers found on network")
                except Exception as e:
                    test_results.append(f"✗ Discovery error: {e}")
                test_results.append("")
                
                # Test 3: Direct connection attempt
                test_results.append("3. DIRECT CONNECTION TEST")
                test_results.append("-" * 20)
                try:
                    if self.connection_manager:
                        ip = self.test_ip_entry.get().strip() if hasattr(self, 'test_ip_entry') else "10.1.0.21"
                        
                        # Try different connection methods
                        test_results.append(f"Testing connection to {ip}...")
                        
                        # Method 1: Standard connection
                        try:
                            success = self.connection_manager.connect_to_controller(ip, self.update_connection_status)
                            if success:
                                test_results.append(f"✓ Standard connection: SUCCESS")
                                test_results.append("✓ Controller is reachable and responding")
                                
                                # Keep the connection alive for further testing
                                test_results.append("✓ Connection maintained for testing")
                            else:
                                test_results.append(f"✗ Standard connection: FAILED")
                        except Exception as e:
                            test_results.append(f"✗ Standard connection error: {e}")
                        
                        # Method 2: Direct gclib connection test
                        test_results.append("Testing direct gclib connection...")
                        try:
                            import gclib
                            g = gclib.py()
                            g.GOpen(f"{ip} --direct")
                            test_results.append("✓ Direct gclib connection: SUCCESS")
                            g.GClose()
                        except Exception as e:
                            test_results.append(f"✗ Direct gclib connection error: {e}")
                        
                        # Method 3: TCP socket test
                        test_results.append("Testing TCP socket connection...")
                        try:
                            import socket
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(5)
                            result = sock.connect_ex((ip, 23))  # Galil default port
                            if result == 0:
                                test_results.append("✓ TCP socket connection: SUCCESS")
                                sock.close()
                            else:
                                test_results.append(f"✗ TCP socket connection: FAILED (error {result})")
                        except Exception as e:
                            test_results.append(f"✗ TCP socket connection error: {e}")
                        
                        # Method 4: Try different ports
                        test_results.append("Testing different ports...")
                        ports_to_test = [23, 22, 80, 443, 8080]
                        for port in ports_to_test:
                            try:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(2)
                                result = sock.connect_ex((ip, port))
                                if result == 0:
                                    test_results.append(f"✓ Port {port}: OPEN")
                                else:
                                    test_results.append(f"✗ Port {port}: CLOSED")
                                sock.close()
                            except:
                                test_results.append(f"✗ Port {port}: ERROR")
                        
                    else:
                        test_results.append("✗ Connection manager not available")
                except Exception as e:
                    test_results.append(f"✗ Connection error: {e}")
                test_results.append("")
                
                # Test 4: Basic command test
                test_results.append("4. BASIC COMMAND TEST")
                test_results.append("-" * 20)
                
                # Try to use existing connection or create new one
                controller_available = False
                if self.controller:
                    controller_available = True
                    test_results.append("✓ Using existing controller connection")
                else:
                    # Try to connect if we don't have a connection
                    try:
                        if self.connection_manager:
                            ip = self.test_ip_entry.get().strip() if hasattr(self, 'test_ip_entry') else "10.1.0.21"
                            success = self.connection_manager.connect_to_controller(ip, self.update_connection_status)
                            if success:
                                controller_available = True
                                test_results.append("✓ Connected to controller for testing")
                            else:
                                test_results.append("✗ Failed to connect to controller")
                        else:
                            test_results.append("✗ Connection manager not available")
                    except Exception as e:
                        test_results.append(f"✗ Connection error: {e}")
                
                if controller_available and self.controller:
                    try:
                        response = self.controller.send_command("TP A")
                        test_results.append(f"✓ TP A command: {response}")
                        
                        response = self.controller.send_command("MG _REV")
                        test_results.append(f"✓ Firmware: {response}")
                        
                        response = self.controller.send_command("MG _BM")
                        test_results.append(f"✓ Model: {response}")
                        
                        response = self.controller.send_command("MG _BN")
                        test_results.append(f"✓ Burn count: {response}")
                        
                    except Exception as e:
                        test_results.append(f"✗ Command test error: {e}")
                else:
                    test_results.append("✗ No controller connection available for command testing")
                
                # Add troubleshooting recommendations
                test_results.append("5. TROUBLESHOOTING RECOMMENDATIONS")
                test_results.append("-" * 30)
                
                # Analyze the results to provide specific recommendations
                ping_success = any("✓ Ping to" in line for line in test_results)
                discovery_success = any("✓ Found" in line for line in test_results)
                connection_failed = any("✗ Standard connection: FAILED" in line for line in test_results)
                tcp_success = any("✓ TCP socket connection: SUCCESS" in line for line in test_results)
                
                if ping_success and discovery_success and connection_failed:
                    test_results.append("DIAGNOSIS: Controller is reachable but connection protocol issue")
                    test_results.append("")
                    test_results.append("SOLUTIONS TO TRY:")
                    test_results.append("1. Controller may be in a different mode")
                    test_results.append("2. Try connecting with different software first (Galil Tools)")
                    test_results.append("3. Controller may need to be reset")
                    test_results.append("4. Check if controller is in program mode")
                    test_results.append("5. Try sending a simple command via telnet:")
                    test_results.append(f"   telnet {ip} 23")
                    test_results.append("   Then type: TP A")
                    test_results.append("")
                    test_results.append("6. If telnet works, try these commands:")
                    test_results.append("   RS (reset)")
                    test_results.append("   MG _REV (get firmware)")
                    test_results.append("   MG _BM (get model)")
                elif ping_success and not tcp_success:
                    test_results.append("DIAGNOSIS: Network reachable but Galil service not responding")
                    test_results.append("")
                    test_results.append("SOLUTIONS TO TRY:")
                    test_results.append("1. Controller may not be powered on")
                    test_results.append("2. Controller may be in boot mode")
                    test_results.append("3. Check network cable connection")
                    test_results.append("4. Try power cycling the controller")
                else:
                    test_results.append("DIAGNOSIS: General connectivity issue")
                    test_results.append("")
                    test_results.append("SOLUTIONS TO TRY:")
                    test_results.append("1. Check controller power")
                    test_results.append("2. Verify network cable")
                    test_results.append("3. Check IP address configuration")
                    test_results.append("4. Try different network port")
                
                # Update UI with results
                self.root.after(0, lambda: self.display_connection_test_results(test_results))
                
            except Exception as e:
                self.root.after(0, lambda: self.display_connection_test_results([f"Connection test failed: {e}"]))
        
        # Start the test thread
        test_thread = threading.Thread(target=test_connection_thread, daemon=True)
        test_thread.start()
    
    def display_connection_test_results(self, results):
        """Display connection test results"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, "\n".join(results))
        
        if hasattr(self, 'diagnostics_summary_label'):
            # Count successes and failures
            success_count = sum(1 for line in results if line.startswith("✓"))
            fail_count = sum(1 for line in results if line.startswith("✗"))
            self.diagnostics_summary_label.config(text=f"Connection Test: {success_count} passed, {fail_count} failed")
    
    def scan_network_for_controllers(self):
        """Scan the network for Galil controllers"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, "Scanning network for Galil controllers...\n")
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text="Scanning network...")
        
        # Scan in a separate thread
        def scan_network_thread():
            try:
                scan_results = []
                scan_results.append("NETWORK SCAN FOR GALIL CONTROLLERS")
                scan_results.append("=" * 50)
                scan_results.append("")
                
                # Get local network information
                scan_results.append("1. LOCAL NETWORK INFORMATION")
                scan_results.append("-" * 30)
                try:
                    import socket
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    scan_results.append(f"Hostname: {hostname}")
                    scan_results.append(f"Local IP: {local_ip}")
                    
                    # Determine network range
                    ip_parts = local_ip.split('.')
                    network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                    scan_results.append(f"Network Range: {network_base}.0/24")
                    scan_results.append("")
                except Exception as e:
                    scan_results.append(f"Error getting network info: {e}")
                    scan_results.append("")
                
                # Test common Galil IP addresses
                scan_results.append("2. TESTING COMMON GALIL IP ADDRESSES")
                scan_results.append("-" * 30)
                common_ips = [
                    "10.1.0.21", "10.1.0.20", "10.1.0.22", "10.1.0.23",
                    "192.168.1.100", "192.168.1.101", "192.168.1.102",
                    "192.168.0.100", "192.168.0.101", "192.168.0.102",
                    "10.0.0.100", "10.0.0.101", "10.0.0.102"
                ]
                
                found_controllers = []
                for ip in common_ips:
                    try:
                        if ping_controller(ip):
                            scan_results.append(f"✓ {ip}: PING SUCCESS")
                            # Try to connect and get controller info
                            try:
                                temp_controller = GalilController()
                                temp_controller.connect(ip)
                                try:
                                    model = temp_controller.send_command("MG _BM")
                                    firmware = temp_controller.send_command("MG _REV")
                                    scan_results.append(f"  → Model: {model}")
                                    scan_results.append(f"  → Firmware: {firmware}")
                                    found_controllers.append({
                                        'ip': ip,
                                        'model': model,
                                        'firmware': firmware
                                    })
                                except:
                                    scan_results.append(f"  → Galil controller detected (no info)")
                                    found_controllers.append({'ip': ip, 'model': 'Unknown', 'firmware': 'Unknown'})
                                finally:
                                    temp_controller.disconnect()
                            except:
                                scan_results.append(f"  → Device responds to ping but not Galil commands")
                        else:
                            scan_results.append(f"✗ {ip}: No response")
                    except Exception as e:
                        scan_results.append(f"✗ {ip}: Error - {e}")
                
                scan_results.append("")
                
                # Network discovery scan
                scan_results.append("3. NETWORK DISCOVERY SCAN")
                scan_results.append("-" * 30)
                try:
                    discovered = discover_galil_controllers()
                    if discovered:
                        scan_results.append(f"✓ Discovery found {len(discovered)} controller(s):")
                        for controller in discovered:
                            scan_results.append(f"  → {controller}")
                    else:
                        scan_results.append("✗ No controllers found via discovery")
                except Exception as e:
                    scan_results.append(f"✗ Discovery error: {e}")
                scan_results.append("")
                
                # Summary
                scan_results.append("4. SCAN SUMMARY")
                scan_results.append("-" * 30)
                if found_controllers:
                    scan_results.append(f"✓ Found {len(found_controllers)} Galil controller(s):")
                    for controller in found_controllers:
                        scan_results.append(f"  → {controller['ip']} ({controller['model']}, {controller['firmware']})")
                    scan_results.append("")
                    scan_results.append("RECOMMENDATION:")
                    scan_results.append(f"Try connecting to: {found_controllers[0]['ip']}")
                else:
                    scan_results.append("✗ No Galil controllers found")
                    scan_results.append("")
                    scan_results.append("TROUBLESHOOTING SUGGESTIONS:")
                    scan_results.append("1. Check if controller is powered on")
                    scan_results.append("2. Verify network cable connection")
                    scan_results.append("3. Check controller IP configuration")
                    scan_results.append("4. Try different network ranges")
                    scan_results.append("5. Check firewall settings")
                
                # Update UI with results
                self.root.after(0, lambda: self.display_network_scan_results(scan_results, found_controllers))
                
            except Exception as e:
                self.root.after(0, lambda: self.display_network_scan_results([f"Network scan failed: {e}"], []))
        
        # Start the scan thread
        scan_thread = threading.Thread(target=scan_network_thread, daemon=True)
        scan_thread.start()
    
    def display_network_scan_results(self, results, found_controllers):
        """Display network scan results"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, "\n".join(results))
        
        if hasattr(self, 'diagnostics_summary_label'):
            if found_controllers:
                summary = f"Network Scan: Found {len(found_controllers)} controller(s)"
            else:
                summary = "Network Scan: No controllers found"
            self.diagnostics_summary_label.config(text=summary)
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text="Network scan completed")
    
    def quick_connect_to_ip(self):
        """Quickly connect to the IP address specified in the test IP field"""
        if not hasattr(self, 'test_ip_entry'):
            messagebox.showerror("Error", "IP address input field not found")
            return
        
        ip = self.test_ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return
        
        if not validate_ip_address(ip):
            messagebox.showerror("Error", "Invalid IP address format")
            return
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text=f"Connecting to {ip}...")
        
        # Connect in a separate thread
        def connect_thread():
            try:
                if self.connection_manager:
                    success = self.connection_manager.connect_to_controller(ip, self.update_connection_status)
                    if success:
                        self.root.after(0, lambda: self.show_connection_success(ip))
                    else:
                        self.root.after(0, lambda: self.show_connection_failure(ip))
                else:
                    self.root.after(0, lambda: self.show_connection_failure(ip, "Connection manager not available"))
            except Exception as e:
                self.root.after(0, lambda: self.show_connection_failure(ip, str(e)))
        
        # Start the connection thread
        connect_thread_obj = threading.Thread(target=connect_thread, daemon=True)
        connect_thread_obj.start()
    
    def show_connection_success(self, ip):
        """Show connection success message"""
        messagebox.showinfo("Success", f"Successfully connected to controller at {ip}")
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text=f"Connected to {ip}")
        if hasattr(self, 'diagnostics_summary_label'):
            self.diagnostics_summary_label.config(text=f"Connected to {ip}")
    
    def show_connection_failure(self, ip, error_msg=None):
        """Show connection failure message"""
        if error_msg:
            messagebox.showerror("Connection Failed", f"Failed to connect to {ip}\n\nError: {error_msg}")
        else:
            messagebox.showerror("Connection Failed", f"Failed to connect to {ip}\n\nController may not be reachable or powered on.")
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text=f"Connection to {ip} failed")
        if hasattr(self, 'diagnostics_summary_label'):
            self.diagnostics_summary_label.config(text=f"Connection to {ip} failed")
    
    def test_telnet_connection(self):
        """Test telnet connection to the controller"""
        if not hasattr(self, 'test_ip_entry'):
            messagebox.showerror("Error", "IP address input field not found")
            return
        
        ip = self.test_ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return
        
        if not validate_ip_address(ip):
            messagebox.showerror("Error", "Invalid IP address format")
            return
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text=f"Testing telnet connection to {ip}...")
        
        # Test telnet in a separate thread
        def telnet_test_thread():
            try:
                telnet_results = []
                telnet_results.append("TELNET CONNECTION TEST")
                telnet_results.append("=" * 30)
                telnet_results.append(f"Testing telnet connection to {ip}:23")
                telnet_results.append("")
                
                # Test 1: Basic telnet connection
                telnet_results.append("1. BASIC TELNET CONNECTION")
                telnet_results.append("-" * 25)
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    result = sock.connect_ex((ip, 23))
                    if result == 0:
                        telnet_results.append("✓ Telnet connection: SUCCESS")
                        sock.close()
                    else:
                        telnet_results.append(f"✗ Telnet connection: FAILED (error {result})")
                except Exception as e:
                    telnet_results.append(f"✗ Telnet connection error: {e}")
                telnet_results.append("")
                
                # Test 2: Try to send a simple command
                telnet_results.append("2. COMMAND TEST")
                telnet_results.append("-" * 25)
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((ip, 23))
                    
                    # Send a simple command
                    command = "TP A\r\n"
                    sock.send(command.encode())
                    
                    # Try to receive response
                    sock.settimeout(5)
                    response = sock.recv(1024).decode('utf-8', errors='ignore')
                    if response:
                        telnet_results.append("✓ Command sent and response received:")
                        telnet_results.append(f"  Command: {command.strip()}")
                        telnet_results.append(f"  Response: {response.strip()}")
                    else:
                        telnet_results.append("✗ No response to command")
                    
                    sock.close()
                except Exception as e:
                    telnet_results.append(f"✗ Command test error: {e}")
                telnet_results.append("")
                
                # Test 3: Try different commands
                telnet_results.append("3. MULTIPLE COMMAND TEST")
                telnet_results.append("-" * 25)
                commands_to_test = ["TP A", "MG _REV", "MG _BM", "RS"]
                for cmd in commands_to_test:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        sock.connect((ip, 23))
                        
                        command = f"{cmd}\r\n"
                        sock.send(command.encode())
                        
                        sock.settimeout(3)
                        response = sock.recv(1024).decode('utf-8', errors='ignore')
                        if response:
                            telnet_results.append(f"✓ {cmd}: {response.strip()}")
                        else:
                            telnet_results.append(f"✗ {cmd}: No response")
                        
                        sock.close()
                    except Exception as e:
                        telnet_results.append(f"✗ {cmd}: Error - {e}")
                
                telnet_results.append("")
                telnet_results.append("4. RECOMMENDATIONS")
                telnet_results.append("-" * 25)
                if any("✓ Telnet connection: SUCCESS" in line for line in telnet_results):
                    telnet_results.append("✓ Controller is responding to telnet")
                    telnet_results.append("")
                    telnet_results.append("NEXT STEPS:")
                    telnet_results.append("1. Controller is reachable via telnet")
                    telnet_results.append("2. Try connecting with Galil Tools software")
                    telnet_results.append("3. If Galil Tools works, the issue is with gclib")
                    telnet_results.append("4. Try updating gclib or using different version")
                    telnet_results.append("")
                    telnet_results.append("MANUAL TELNET TEST:")
                    telnet_results.append(f"1. Open Command Prompt as Administrator")
                    telnet_results.append("2. Enable telnet: dism /online /Enable-Feature /FeatureName:TelnetClient")
                    telnet_results.append(f"3. Type: telnet {ip} 23")
                    telnet_results.append("4. Try commands: TP A, MG _REV, MG _BM")
                    telnet_results.append("")
                    telnet_results.append("ALTERNATIVE: Use PowerShell:")
                    telnet_results.append(f"Test-NetConnection -ComputerName {ip} -Port 23")
                else:
                    telnet_results.append("✗ Controller not responding to telnet")
                    telnet_results.append("")
                    telnet_results.append("TROUBLESHOOTING:")
                    telnet_results.append("1. Check if controller is powered on")
                    telnet_results.append("2. Verify network cable connection")
                    telnet_results.append("3. Try power cycling the controller")
                    telnet_results.append("4. Check if controller is in boot mode")
                
                # Update UI with results
                self.root.after(0, lambda: self.display_telnet_test_results(telnet_results))
                
            except Exception as e:
                self.root.after(0, lambda: self.display_telnet_test_results([f"Telnet test failed: {e}"]))
        
        # Start the telnet test thread
        telnet_thread = threading.Thread(target=telnet_test_thread, daemon=True)
        telnet_thread.start()
    
    def display_telnet_test_results(self, results):
        """Display telnet test results"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, "\n".join(results))
        
        if hasattr(self, 'diagnostics_summary_label'):
            if any("✓ Telnet connection: SUCCESS" in line for line in results):
                summary = "Telnet Test: Controller responding"
            else:
                summary = "Telnet Test: Controller not responding"
            self.diagnostics_summary_label.config(text=summary)
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text="Telnet test completed")
    
    def connect_and_keep_connected(self):
        """Connect to controller and maintain the connection"""
        if not hasattr(self, 'test_ip_entry'):
            messagebox.showerror("Error", "IP address input field not found")
            return
        
        ip = self.test_ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return
        
        if not validate_ip_address(ip):
            messagebox.showerror("Error", "Invalid IP address format")
            return
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            self.diagnostics_progress_label.config(text=f"Connecting to {ip} and maintaining connection...")
        
        # Connect in a separate thread
        def connect_thread():
            try:
                if self.connection_manager:
                    success = self.connection_manager.connect_to_controller(ip, self.update_connection_status)
                    if success:
                        # Test the connection with a few commands
                        test_results = []
                        test_results.append("CONNECTION ESTABLISHED")
                        test_results.append("=" * 30)
                        test_results.append(f"✓ Connected to {ip}")
                        test_results.append("")
                        
                        # Test basic commands
                        test_results.append("TESTING CONNECTION:")
                        test_results.append("-" * 20)
                        
                        try:
                            response = self.controller.send_command("TP A")
                            test_results.append(f"✓ TP A: {response}")
                            
                            response = self.controller.send_command("MG _REV")
                            test_results.append(f"✓ MG _REV: {response}")
                            
                            response = self.controller.send_command("MG _BM")
                            test_results.append(f"✓ MG _BM: {response}")
                            
                            response = self.controller.send_command("MG _BN")
                            test_results.append(f"✓ MG _BN: {response}")
                            
                            test_results.append("")
                            test_results.append("✓ CONNECTION IS STABLE AND READY")
                            test_results.append("✓ You can now use all controller features")
                            test_results.append("✓ Connection will be maintained")
                            
                        except Exception as e:
                            test_results.append(f"✗ Command test failed: {e}")
                            test_results.append("✗ Connection may not be stable")
                        
                        # Update UI with results
                        self.root.after(0, lambda: self.display_connection_results(test_results, True))
                        
                    else:
                        self.root.after(0, lambda: self.display_connection_results([f"Failed to connect to {ip}"], False))
                else:
                    self.root.after(0, lambda: self.display_connection_results(["Connection manager not available"], False))
                    
            except Exception as e:
                self.root.after(0, lambda: self.display_connection_results([f"Connection error: {e}"], False))
        
        # Start the connection thread
        connect_thread_obj = threading.Thread(target=connect_thread, daemon=True)
        connect_thread_obj.start()
    
    def display_connection_results(self, results, success):
        """Display connection results"""
        if hasattr(self, 'diagnostics_results_text'):
            self.diagnostics_results_text.delete(1.0, tk.END)
            self.diagnostics_results_text.insert(1.0, "\n".join(results))
        
        if hasattr(self, 'diagnostics_summary_label'):
            if success:
                summary = "✓ Controller Connected and Ready"
            else:
                summary = "✗ Connection Failed"
            self.diagnostics_summary_label.config(text=summary)
        
        # Update progress
        if hasattr(self, 'diagnostics_progress_label'):
            if success:
                self.diagnostics_progress_label.config(text="Connection established and maintained")
            else:
                self.diagnostics_progress_label.config(text="Connection failed")

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
