"""
GUI Framework for Galil Setup Tool

This module contains all the GUI framework functions that were previously
in main.py, organized for better code structure and maintainability.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

class GUIFramework:
    """Class containing all GUI framework functions"""
    
    def __init__(self, root, colors, log_callback=None, main_app=None):
        """
        Initialize the GUI framework
        
        Args:
            root: The main Tkinter root window
            colors: Color scheme dictionary
            log_callback: Optional callback function for logging messages
            main_app: Reference to the main application instance
        """
        self.root = root
        self.colors = colors
        self.log_callback = log_callback or self._default_log
        self.main_app = main_app
        
        # Initialize GUI state variables
        self.main_content = None
        self.sidebar = None
        self.header = None
        self.canvas = None
        self.scrollbar = None
        self.current_page = None
        
        # Encoder display tracking
        self.encoder_displays = {}
        self.encoder_labels = {}
        
        # Auto-update state
        self.auto_update_running = False
        self.auto_update_thread = None
        
    def _default_log(self, message: str):
        """Default logging function if no callback provided"""
        print(message)
    
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="lightyellow", 
                           font=("Arial", 8), relief="solid", borderwidth=1)
            label.pack()
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def log(self, message: str):
        """Log a message using the callback"""
        self.log_callback(message)
    
    def setup_ui(self):
        """Setup the main UI with Acertara-style layout"""
        # Configure grid weights - add row for persistent log
        self.root.grid_rowconfigure(0, weight=1)  # Main content area
        self.root.grid_rowconfigure(1, weight=0)  # Persistent log area (fixed height)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create header
        self.create_header()
        
        # Create main content area
        self.create_main_content()
        
        # Create persistent log at bottom
        self.create_persistent_log()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for all text widgets"""
        # Find the widget under the mouse cursor
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        
        # If it's a text widget, scroll it
        if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
            # Determine scroll direction
            if event.delta:
                # Windows
                delta = -1 if event.delta > 0 else 1
            else:
                # Linux
                delta = -1 if event.num == 4 else 1
            
            # Scroll the text widget
            widget.yview_scroll(delta, "units")
        
        # If it's a canvas, scroll it
        elif isinstance(widget, tk.Canvas):
            if event.delta:
                # Windows
                delta = -1 if event.delta > 0 else 1
            else:
                # Linux
                delta = -1 if event.num == 4 else 1
            
            # Scroll the canvas
            widget.yview_scroll(delta, "units")
        
        # Fallback: scroll the main canvas if no specific widget found
        else:
            if hasattr(self, 'canvas') and self.canvas:
                if event.delta:
                    # Windows
                    delta = -1 if event.delta > 0 else 1
                else:
                    # Linux
                    delta = -1 if event.num == 4 else 1
                
                # Scroll the main canvas
                self.canvas.yview_scroll(delta, "units")
    
    def create_sidebar(self):
        """Create the sidebar with navigation buttons"""
        # Create sidebar frame
        self.sidebar = tk.Frame(self.root, bg=self.colors['sidebar_bg'], width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Sidebar title
        title = tk.Label(self.sidebar, text="Galil Setup Tool", 
                        font=("Arial", 16, "bold"), 
                        bg=self.colors['sidebar_bg'], fg=self.colors['sidebar_fg'])
        title.pack(pady=(20, 30))
        
        # Navigation buttons
        nav_buttons = [
            ("Motor Tuning", self.main_app.show_motor_tuning if self.main_app else None),
            ("Network Config", self.main_app.show_network_config if self.main_app else None),
            ("Controller Testing", self.main_app.show_controller_testing if self.main_app else None),
            ("Visual Testing", self.main_app.show_visual_testing if self.main_app else None),
            ("Settings", self.main_app.show_settings if self.main_app else None)
        ]
        
        for text, command in nav_buttons:
            btn = tk.Button(self.sidebar, text=text, command=command,
                           font=("Arial", 12), bg=self.colors['accent_blue'], 
                           fg='white', relief='flat', padx=20, pady=10)
            btn.pack(fill='x', padx=20, pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.colors['success_green']))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self.colors['accent_blue']))
    
    def create_header(self):
        """Create the header with connection status"""
        self.header = tk.Frame(self.root, bg=self.colors['header_bg'], height=60)
        self.header.grid(row=0, column=1, sticky="ew", padx=(0, 0))
        self.header.grid_propagate(False)
        
        # Connection status
        self.connection_status = tk.Label(self.header, text="Disconnected", 
                                        font=("Arial", 12, "bold"), 
                                        bg=self.colors['header_bg'], fg=self.colors['error_red'])
        self.connection_status.pack(side='right', padx=20, pady=15)
        
        # IP address display
        self.ip_display = tk.Label(self.header, text="IP: Not Set", 
                                 font=("Arial", 10), 
                                 bg=self.colors['header_bg'], fg=self.colors['header_fg'])
        self.ip_display.pack(side='right', padx=(0, 20), pady=15)
    
    def create_main_content(self):
        """Create the main content area with scrolling"""
        # Create main content frame
        main_frame = tk.Frame(self.root, bg=self.colors['main_bg'])
        main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=(60, 0))
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(main_frame, bg=self.colors['main_bg'], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors['main_bg'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Grid the canvas and scrollbar
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind mouse wheel to canvas and scrollable frame
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        
        # Bind canvas configure event
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Create main content area
        self.main_content = self.scrollable_frame
        
        # Bind window resize event
        self.root.bind("<Configure>", self._on_window_resize)
    
    def _on_frame_configure(self, event=None):
        """Handle frame configuration changes"""
        # Update scroll region when frame size changes
        if self.canvas:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Handle canvas configuration changes"""
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update canvas window width
        self._update_canvas_window_width()
    
    def _on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            # Update scrollbar visibility
            self._update_scrollbar_visibility()
            
            # Update page scroll region
            self._update_page_scroll_region()
    
    def _update_scrollbar_visibility(self):
        """Update scrollbar visibility based on content"""
        if not self.canvas or not self.scrollbar:
            return
            
        # Get canvas and scrollable frame dimensions
        canvas_height = self.canvas.winfo_height()
        frame_height = self.scrollable_frame.winfo_reqheight()
        
        # Show/hide scrollbar based on content
        if frame_height > canvas_height:
            self.scrollbar.grid()
        else:
            self.scrollbar.grid_remove()
    
    def _update_page_scroll_region(self):
        """Update the scroll region for the current page"""
        if self.canvas:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self._update_scrollbar_visibility()
    
    def _configure_page_sections(self):
        """Configure page sections for proper display"""
        if not self.main_content:
            return
            
        # Configure all frames in the main content
        for widget in self.main_content.winfo_children():
            if isinstance(widget, tk.Frame):
                self._configure_content_scaling(widget)
    
    def _ensure_button_visibility(self):
        """Ensure all buttons are visible and properly configured"""
        if not self.main_content:
            return
            
        # Find all buttons
        buttons = []
        self._find_all_buttons(self.main_content, buttons)
        
        # Configure each button
        for button in buttons:
            self._configure_button_visibility(button)
    
    def _find_all_buttons(self, parent_widget, button_list):
        """Recursively find all buttons in a widget hierarchy"""
        for widget in parent_widget.winfo_children():
            if isinstance(widget, tk.Button):
                button_list.append(widget)
            elif isinstance(widget, (tk.Frame, tk.Toplevel)):
                self._find_all_buttons(widget, button_list)
    
    def _configure_button_visibility(self, button):
        """Configure button visibility and scaling"""
        try:
            # Ensure button is visible
            button.update_idletasks()
            
            # Configure text scaling
            self._configure_button_text_scaling(button)
            
            # Configure child widgets
            self._configure_child_widgets(button)
            
        except tk.TclError:
            # Widget was destroyed, ignore
            pass
    
    def _configure_child_widgets(self, parent_widget):
        """Configure child widgets for proper display"""
        try:
            for widget in parent_widget.winfo_children():
                if isinstance(widget, tk.Frame):
                    self._configure_content_scaling(widget)
                elif isinstance(widget, tk.Button):
                    self._configure_button_text_scaling(widget)
        except tk.TclError:
            # Widget was destroyed, ignore
            pass
    
    def _configure_button_text_scaling(self, button):
        """Configure button text scaling based on available space"""
        try:
            # Get button text
            text = button.cget("text")
            if not text:
                return
            
            # Calculate appropriate font size
            font_size = self._calculate_button_font_size(text)
            
            # Update button font
            button.configure(font=("Arial", font_size))
            
        except tk.TclError:
            # Widget was destroyed, ignore
            pass
    
    def _calculate_button_font_size(self, text):
        """Calculate appropriate font size for button text"""
        # Base font size
        base_size = 12
        
        # Adjust based on text length
        if len(text) > 20:
            return max(8, base_size - 2)
        elif len(text) > 15:
            return max(9, base_size - 1)
        else:
            return base_size
    
    def _create_missing_encoder_label(self, axis):
        """Create missing encoder label for an axis"""
        if axis not in self.encoder_labels:
            self.encoder_labels[axis] = tk.Label(
                self.main_content, 
                text=f"Axis {axis}", 
                font=("Arial", 12, "bold"),
                bg=self.colors['main_bg'], 
                fg=self.colors['main_fg']
            )
            self.encoder_labels[axis].pack(pady=5)
    
    def _force_update_encoder_displays(self):
        """Force update of all encoder displays"""
        if not self.encoder_displays:
            return
            
        for axis in self.encoder_displays:
            try:
                if isinstance(self.encoder_displays[axis], dict):
                    # New structure with speed and position canvases
                    speed_canvas = self.encoder_displays[axis].get('speed')
                    position_canvas = self.encoder_displays[axis].get('position')
                    
                    if speed_canvas and speed_canvas.winfo_exists():
                        speed_canvas.delete("all")
                        speed_canvas.create_text(90, 30, text="?", fill='gray', font=("Arial", 10))
                    
                    if position_canvas and position_canvas.winfo_exists():
                        position_canvas.delete("all")
                        position_canvas.create_text(60, 60, text="?", fill='gray', font=("Arial", 20))
                else:
                    # Old structure - fallback for compatibility
                    if axis in self.encoder_displays and self.encoder_displays[axis].winfo_exists():
                        self.encoder_displays[axis].delete("all")
                        self.encoder_displays[axis].create_oval(10, 10, 140, 140, outline='gray', width=1)
                        self.encoder_displays[axis].create_text(75, 75, text="?", fill='gray', font=("Arial", 20))
            except tk.TclError:
                # Widget was destroyed, ignore
                pass
    
    def _ensure_all_axes_visible(self):
        """Ensure all axis displays are visible"""
        for axis in ['A', 'B', 'C', 'D']:
            self._create_missing_encoder_label(axis)
            if axis in self.encoder_displays:
                try:
                    if isinstance(self.encoder_displays[axis], dict):
                        # New structure
                        speed_canvas = self.encoder_displays[axis].get('speed')
                        position_canvas = self.encoder_displays[axis].get('position')
                        
                        if speed_canvas:
                            speed_canvas.update_idletasks()
                            speed_canvas.update()
                        if position_canvas:
                            position_canvas.update_idletasks()
                            position_canvas.update()
                    else:
                        # Old structure
                        self.encoder_displays[axis].update_idletasks()
                        self.encoder_displays[axis].update()
                except tk.TclError:
                    # Widget was destroyed, ignore
                    pass
    
    def _draw_speed_bar(self, axis, speed):
        """Draw the half-moon speed bar with gradient from green to red"""
        if axis not in self.encoder_displays or 'speed' not in self.encoder_displays[axis]:
            return
            
        canvas = self.encoder_displays[axis]['speed']
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
            import math
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
    
    def _initialize_encoder_display(self, axis):
        """Initialize the speed bar and position dial for an axis"""
        if axis not in self.encoder_displays:
            return
        self._draw_speed_bar(axis, 0)
        self._draw_position_dial(axis, 0)
    
    def _draw_position_dial(self, axis, position):
        """Draw the clock-like position dial with tick marks and needle"""
        if axis not in self.encoder_displays or 'position' not in self.encoder_displays[axis]:
            return
            
        canvas = self.encoder_displays[axis]['position']
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
        import math
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
    
    def _update_canvas_window_width(self):
        """Update canvas window width to match canvas width"""
        if self.canvas:
            canvas_width = self.canvas.winfo_width()
            self.canvas.itemconfig(self.canvas.find_all()[0], width=canvas_width)
    
    def _configure_content_scaling(self, frame):
        """Configure content scaling for a frame"""
        try:
            # Update frame
            frame.update_idletasks()
            
            # Configure child widgets
            self._configure_widget_scaling(frame, frame)
            
        except tk.TclError:
            # Widget was destroyed, ignore
            pass
    
    def _configure_widget_scaling(self, widget, parent_frame):
        """Configure widget scaling within a frame"""
        try:
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame):
                    self._configure_content_scaling(child)
                elif isinstance(child, tk.Button):
                    self._configure_button_text_scaling(child)
        except tk.TclError:
            # Widget was destroyed, ignore
            pass
    
    def create_persistent_log(self):
        """Create persistent log interface"""
        # Create log frame
        log_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        log_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Log title
        title = tk.Label(log_frame, text="Persistent Log", 
                        font=("Arial", 18, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 10))
        
        # Log text area
        self.persistent_log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=20, 
            width=80,
            font=("Consolas", 10),
            bg='black',
            fg='green',
            insertbackground='white'
        )
        self.persistent_log_text.pack(fill='both', expand=True, pady=(0, 10))
        
        # Log controls
        controls_frame = tk.Frame(log_frame, bg=self.colors['main_bg'])
        controls_frame.pack(fill='x', pady=(0, 10))
        
        # Toggle button
        self.log_toggle_btn = tk.Button(
            controls_frame, 
            text="Start Logging", 
            command=self.toggle_persistent_log,
            bg=self.colors['accent_blue'], 
            fg='white',
            font=("Arial", 12)
        )
        self.log_toggle_btn.pack(side='left', padx=(0, 10))
        
        # Copy button
        copy_btn = tk.Button(
            controls_frame, 
            text="Copy Log", 
            command=self.copy_persistent_log,
            bg=self.colors['success_green'], 
            fg='white',
            font=("Arial", 12)
        )
        copy_btn.pack(side='left', padx=(0, 10))
        
        # Clear button
        clear_btn = tk.Button(
            controls_frame, 
            text="Clear Log", 
            command=self.clear_persistent_log,
            bg=self.colors['warning_orange'], 
            fg='white',
            font=("Arial", 12)
        )
        clear_btn.pack(side='left')
    
    def toggle_persistent_log(self):
        """Toggle persistent logging on/off"""
        if not hasattr(self, 'persistent_logging'):
            self.persistent_logging = False
        
        self.persistent_logging = not self.persistent_logging
        
        if self.persistent_logging:
            self.log_toggle_btn.config(text="Stop Logging", bg=self.colors['error_red'])
            self.log("Persistent logging started")
        else:
            self.log_toggle_btn.config(text="Start Logging", bg=self.colors['accent_blue'])
            self.log("Persistent logging stopped")
    
    def copy_persistent_log(self):
        """Copy persistent log to clipboard"""
        try:
            log_content = self.persistent_log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            messagebox.showinfo("Success", "Log copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy log: {e}")
    
    def clear_persistent_log(self):
        """Clear the persistent log"""
        self.persistent_log_text.delete(1.0, tk.END)
        self.log("Persistent log cleared")
    
    def clear_main_content(self):
        """Clear the main content area"""
        if self.main_content:
            for widget in self.main_content.winfo_children():
                widget.destroy()
    
    def update_connection_status(self, connected, ip_address=None):
        """Update the connection status display"""
        if connected:
            self.connection_status.config(text="Connected", fg=self.colors['online_green'])
            if ip_address:
                self.ip_display.config(text=f"IP: {ip_address}")
        else:
            self.connection_status.config(text="Disconnected", fg=self.colors['error_red'])
            self.ip_display.config(text="IP: Not Set")
    
    def create_network_interface(self):
        """Create network configuration interface"""
        # Create network frame
        network_frame = tk.Frame(self.main_content, bg=self.colors['main_bg'])
        network_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Network title
        title = tk.Label(network_frame, text="Network Configuration", 
                        font=("Arial", 18, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # IP configuration section
        ip_frame = tk.LabelFrame(network_frame, text="IP Configuration", 
                               font=("Arial", 12, "bold"),
                               bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        ip_frame.pack(fill='x', pady=(0, 20))
        
        # IP address entry
        ip_label = tk.Label(ip_frame, text="IP Address:", 
                           font=("Arial", 12),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        ip_label.pack(anchor='w', padx=10, pady=5)
        
        self.ip_entry = tk.Entry(ip_frame, font=("Arial", 12), width=20)
        self.ip_entry.pack(anchor='w', padx=10, pady=(0, 10))
        self.ip_entry.insert(0, "10.1.0.21")  # Default IP
        
        # Connection buttons
        conn_frame = tk.Frame(ip_frame, bg=self.colors['main_bg'])
        conn_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        connect_btn = tk.Button(conn_frame, text="Connect", 
                               command=self.connect_to_controller,
                               bg=self.colors['accent_blue'], fg='white',
                               font=("Arial", 12))
        connect_btn.pack(side='left', padx=(0, 10))
        
        disconnect_btn = tk.Button(conn_frame, text="Disconnect", 
                                  command=self.disconnect_controller,
                                  bg=self.colors['error_red'], fg='white',
                                  font=("Arial", 12))
        disconnect_btn.pack(side='left', padx=(0, 10))
        
        discover_btn = tk.Button(conn_frame, text="Discover Controllers", 
                                command=self.discover_controllers,
                                bg=self.colors['success_green'], fg='white',
                                font=("Arial", 12))
        discover_btn.pack(side='left')
    
    def set_ip_address(self):
        """Set IP address from entry field"""
        ip = self.ip_entry.get().strip()
        if ip:
            self.log(f"IP address set to: {ip}")
            return ip
        else:
            messagebox.showerror("Error", "Please enter an IP address")
            return None
    
    def burn_ip_to_flash(self):
        """Burn IP address to controller flash memory"""
        ip = self.set_ip_address()
        if ip:
            self.log(f"Burning IP address {ip} to controller flash memory...")
            # Implementation would go here
            messagebox.showinfo("Success", f"IP address {ip} burned to flash memory")
    
    def connect_to_controller(self):
        """Connect to controller - placeholder for main app method"""
        self.log("Connect to controller method called - implement in main app")
    
    def disconnect_controller(self):
        """Disconnect from controller - placeholder for main app method"""
        self.log("Disconnect controller method called - implement in main app")
    
    def discover_controllers(self):
        """Discover controllers - placeholder for main app method"""
        self.log("Discover controllers method called - implement in main app")
    
    
    def show_motion_controls(self):
        """Show motion controls page - placeholder for main app method"""
        self.log("Show motion controls method called - implement in main app")
    
    
    def show_diagnostics(self):
        """Show diagnostics page - placeholder for main app method"""
        self.log("Show diagnostics method called - implement in main app")
    
    def show_network_config(self):
        """Show network config page - placeholder for main app method"""
        self.log("Show network config method called - implement in main app")
    
    def show_controller_testing(self):
        """Show controller testing page - placeholder for main app method"""
        self.log("Show controller testing method called - implement in main app")
    
    def show_settings(self):
        """Show settings page - placeholder for main app method"""
        self.log("Show settings method called - implement in main app")
    
    def clear_main_content(self):
        """Clear the main content area"""
        if self.main_content:
            for widget in self.main_content.winfo_children():
                widget.destroy()
    
    def clear_command_response(self):
        """Clear the command response text area"""
        if hasattr(self, 'command_response_text') and self.command_response_text:
            self.command_response_text.delete(1.0, tk.END)
    
    def clear_persistent_log(self):
        """Clear the persistent log"""
        if hasattr(self, 'persistent_log_text') and self.persistent_log_text:
            self.persistent_log_text.delete(1.0, tk.END)
            self.log("Persistent log cleared")
    
    def copy_persistent_log(self):
        """Copy persistent log to clipboard"""
        try:
            if hasattr(self, 'persistent_log_text') and self.persistent_log_text:
                log_content = self.persistent_log_text.get(1.0, tk.END)
                self.root.clipboard_clear()
                self.root.clipboard_append(log_content)
                messagebox.showinfo("Success", "Log copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy log: {e}")
    
    def toggle_persistent_log(self):
        """Toggle persistent logging on/off"""
        if not hasattr(self, 'persistent_logging'):
            self.persistent_logging = False
        
        self.persistent_logging = not self.persistent_logging
        
        if hasattr(self, 'log_toggle_btn'):
            if self.persistent_logging:
                self.log_toggle_btn.config(text="Stop Logging", bg=self.colors['error_red'])
                self.log("Persistent logging started")
            else:
                self.log_toggle_btn.config(text="Start Logging", bg=self.colors['accent_blue'])
                self.log("Persistent logging stopped")
    
    def copy_motor_setup_log(self):
        """Copy motor setup log to clipboard"""
        try:
            if hasattr(self, 'motor_status_text') and self.motor_status_text:
                log_content = self.motor_status_text.get(1.0, tk.END)
                self.root.clipboard_clear()
                self.root.clipboard_append(log_content)
                messagebox.showinfo("Success", "Motor setup log copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy log: {e}")
    
    def copy_status_log(self):
        """Copy status log to clipboard"""
        try:
            if hasattr(self, 'status_text') and self.status_text:
                log_content = self.status_text.get(1.0, tk.END)
                self.root.clipboard_clear()
                self.root.clipboard_append(log_content)
                messagebox.showinfo("Success", "Status log copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy log: {e}")
    
    def clear_motor_setup_log(self):
        """Clear motor setup log"""
        if hasattr(self, 'motor_status_text') and self.motor_status_text:
            self.motor_status_text.delete(1.0, tk.END)
            self.log("Motor setup log cleared")
    
    def clear_all_software_limits(self):
        """Clear all software limits - placeholder for main app method"""
        self.log("Clear all software limits method called - implement in main app")
    
    def clear_travel_limits(self):
        """Clear travel limits - placeholder for main app method"""
        self.log("Clear travel limits method called - implement in main app")
    
    def toggle_auto_update(self):
        """Toggle auto-update functionality - placeholder for main app method"""
        self.log("Toggle auto-update method called - implement in main app")
    
    def toggle_motion_section(self, event=None):
        """Toggle motion section visibility - placeholder for main app method"""
        self.log("Toggle motion section method called - implement in main app")
    
    def toggle_brushless_section(self, event=None):
        """Toggle brushless section visibility - placeholder for main app method"""
        self.log("Toggle brushless section method called - implement in main app")
    
    def toggle_live_diagnostics(self):
        """Toggle live diagnostics - placeholder for main app method"""
        self.log("Toggle live diagnostics method called - implement in main app")
    
    def toggle_encoder_display(self):
        """Toggle encoder display - placeholder for main app method"""
        self.log("Toggle encoder display method called - implement in main app")
    
    def toggle_automatic_diagnostics(self):
        """Toggle automatic diagnostics - placeholder for main app method"""
        self.log("Toggle automatic diagnostics method called - implement in main app")
    
    def show_compatible_commands(self):
        """Show compatible commands - placeholder for main app method"""
        self.log("Show compatible commands method called - implement in main app")
    
    def copy_axis_a_to_all_axes(self):
        """Copy axis A settings to all axes - placeholder for main app method"""
        self.log("Copy axis A to all axes method called - implement in main app")
    
    
    
    
    def create_motor_tuning_page(self, main_app):
        """Create the Motor Tuning page GUI with motor setup and command interface"""
        # Title
        title = tk.Label(self.scrollable_frame, text="Motor Tuning & Setup", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Motor tuning content
        tuning_frame = tk.Frame(self.scrollable_frame, bg=self.colors['main_bg'])
        tuning_frame.pack(fill='both', expand=True)

        # Motor Setup Section
        motor_setup_frame = tk.LabelFrame(tuning_frame, text="🔧 Motor Setup & Tuning", 
                                        font=("Arial", 12, "bold"),
                                        bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                        relief='solid', bd=1)
        motor_setup_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Motor setup content
        motor_setup_content = tk.Frame(motor_setup_frame, bg=self.colors['main_bg'])
        motor_setup_content.pack(fill='x', padx=15, pady=15)
        
        # Axis selection
        axis_frame = tk.Frame(motor_setup_content, bg=self.colors['main_bg'])
        axis_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(axis_frame, text="Select Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.motor_tuning_axis_var = tk.StringVar(value="A")
        axis_combo = ttk.Combobox(axis_frame, textvariable=main_app.motor_tuning_axis_var, 
                                values=["A", "B", "C", "D"], width=5, state="readonly")
        axis_combo.pack(side='left', padx=(10, 0))
        
        # Motor presets
        preset_frame = tk.Frame(motor_setup_content, bg=self.colors['main_bg'])
        preset_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(preset_frame, text="Motor Presets:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.motor_tuning_preset_var = tk.StringVar(value="axis_a_20k_4p")
        preset_combo = ttk.Combobox(preset_frame, textvariable=main_app.motor_tuning_preset_var,
                                  values=["axis_a_20k_4p", "axis_a_20k_4p_high_voltage", 
                                         "axis_a_20k_4p_bz", "generic_template"],
                                  width=40, state="readonly")
        preset_combo.pack(anchor='w', pady=(5, 0))
        
        # Load preset button
        load_preset_btn = tk.Button(preset_frame, text="📥 Load Preset", 
                                  font=("Arial", 9, "bold"),
                                  bg=self.colors['accent_blue'], fg='white',
                                  command=main_app.load_motor_preset)
        load_preset_btn.pack(anchor='w', pady=(5, 0))
        
        # Motor specifications
        specs_frame = tk.Frame(motor_setup_content, bg=self.colors['main_bg'])
        specs_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(specs_frame, text="Motor Specifications:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        # Encoder counts per rev
        encoder_frame = tk.Frame(specs_frame, bg=self.colors['main_bg'])
        encoder_frame.pack(fill='x', pady=(5, 0))
        
        tk.Label(encoder_frame, text="Encoder Counts/Rev:", font=("Arial", 9),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.motor_tuning_encoder_counts_entry = tk.Entry(encoder_frame, font=("Arial", 9), width=10)
        main_app.motor_tuning_encoder_counts_entry.pack(side='left', padx=(10, 0))
        
        # Pole pairs
        pole_frame = tk.Frame(specs_frame, bg=self.colors['main_bg'])
        pole_frame.pack(fill='x', pady=(5, 0))
        
        tk.Label(pole_frame, text="Pole Pairs:", font=("Arial", 9),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.motor_tuning_pole_pairs_entry = tk.Entry(pole_frame, font=("Arial", 9), width=10)
        main_app.motor_tuning_pole_pairs_entry.pack(side='left', padx=(10, 0))
        
        # Checkboxes for features
        features_frame = tk.Frame(specs_frame, bg=self.colors['main_bg'])
        features_frame.pack(fill='x', pady=(5, 0))
        
        main_app.motor_tuning_has_index_var = tk.BooleanVar(value=False)
        index_check = tk.Checkbutton(features_frame, text="Has Index Pulse",
                                   variable=main_app.motor_tuning_has_index_var,
                                   font=("Arial", 9), bg=self.colors['main_bg'],
                                   fg=self.colors['main_fg'])
        index_check.pack(side='left')
        
        main_app.motor_tuning_has_halls_var = tk.BooleanVar(value=True)
        halls_check = tk.Checkbutton(features_frame, text="Has Hall Sensors",
                                   variable=main_app.motor_tuning_has_halls_var,
                                   font=("Arial", 9), bg=self.colors['main_bg'],
                                   fg=self.colors['main_fg'])
        halls_check.pack(side='left', padx=(20, 0))
        
        # Commutation method
        comm_frame = tk.Frame(motor_setup_content, bg=self.colors['main_bg'])
        comm_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(comm_frame, text="Commutation Method:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.motor_tuning_commutation_method_var = tk.StringVar(value="bx")
        comm_combo = ttk.Combobox(comm_frame, textvariable=main_app.motor_tuning_commutation_method_var,
                                values=["bx", "bz", "bc_bi"],
                                width=30, state="readonly")
        comm_combo.pack(anchor='w', pady=(5, 0))
        
        # Add method descriptions
        method_desc = tk.Label(comm_frame, 
                             text="bx=Minimal Motion, bz=Drive to Electrical Zero, bc_bi=Hall-based",
                             font=("Arial", 8), bg=self.colors['main_bg'], fg=self.colors['secondary_fg'])
        method_desc.pack(anchor='w', pady=(2, 0))
        
        # Setup buttons
        setup_buttons_frame = tk.Frame(motor_setup_content, bg=self.colors['main_bg'])
        setup_buttons_frame.pack(fill='x', pady=(10, 0))
        
        main_app.run_motor_tuning_btn = tk.Button(setup_buttons_frame, text="🚀 Run Complete Setup", 
                                               font=("Arial", 10, "bold"),
                                               bg=self.colors['success_green'], fg='white',
                                               command=main_app.run_motor_tuning)
        main_app.run_motor_tuning_btn.pack(side='left', padx=(0, 10))
        
        main_app.step_by_step_tuning_btn = tk.Button(setup_buttons_frame, text="📋 Step-by-Step Setup", 
                                            font=("Arial", 10, "bold"),
                                            bg=self.colors['accent_blue'], fg='white',
                                            command=main_app.show_step_by_step_tuning)
        main_app.step_by_step_tuning_btn.pack(side='left', padx=(0, 10))
        
        main_app.stop_motor_tuning_btn = tk.Button(setup_buttons_frame, text="⏹️ Stop Setup", 
                                                font=("Arial", 10, "bold"),
                                                bg=self.colors['error_red'], fg='white',
                                                command=main_app.stop_motor_tuning,
                                                state='disabled')
        main_app.stop_motor_tuning_btn.pack(side='left', padx=(0, 10))

        # PID Configuration Section
        pid_frame = tk.LabelFrame(tuning_frame, text="⚙️ PID Configuration", 
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        pid_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # PID content container
        pid_content = tk.Frame(pid_frame, bg=self.colors['main_bg'])
        pid_content.pack(fill='x', padx=15, pady=15)
        
        # Axis selection
        tk.Label(pid_content, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.axis_var = tk.StringVar(value="A")
        axis_combo = ttk.Combobox(pid_content, textvariable=main_app.axis_var, 
                                 values=["A", "B", "C", "D"], width=10)
        axis_combo.pack(anchor='w', pady=(5, 15))
        
        # KP input
        tk.Label(pid_content, text="KP:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.kp_entry = tk.Entry(pid_content, font=("Arial", 10), width=15)
        main_app.kp_entry.pack(anchor='w', pady=(5, 10))
        main_app.kp_entry.insert(0, "10.0")
        
        # KI input
        tk.Label(pid_content, text="KI:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.ki_entry = tk.Entry(pid_content, font=("Arial", 10), width=15)
        main_app.ki_entry.pack(anchor='w', pady=(5, 10))
        main_app.ki_entry.insert(0, "0.1")
        
        # KD input
        tk.Label(pid_content, text="KD:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.kd_entry = tk.Entry(pid_content, font=("Arial", 10), width=15)
        main_app.kd_entry.pack(anchor='w', pady=(5, 15))
        main_app.kd_entry.insert(0, "50.0")
        
        # Tune button
        tune_btn = tk.Button(pid_content, text="Tune Axis", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=main_app.tune_axis)
        tune_btn.pack(anchor='w')

        # Command Interface Section
        command_frame = tk.LabelFrame(tuning_frame, text="💻 Command Interface", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        command_frame.pack(fill='x', pady=(20, 20), padx=10)
        
        # Command interface content
        command_content = tk.Frame(command_frame, bg=self.colors['main_bg'])
        command_content.pack(fill='x', padx=15, pady=15)
        
        # Command input
        cmd_input_frame = tk.Frame(command_content, bg=self.colors['main_bg'])
        cmd_input_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(cmd_input_frame, text="Send Command:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.motor_tuning_command_entry = tk.Entry(cmd_input_frame, font=("Courier", 10), width=30)
        main_app.motor_tuning_command_entry.pack(side='left', padx=(10, 10))
        main_app.motor_tuning_command_entry.bind('<Return>', lambda e: main_app.send_motor_tuning_command())
        
        main_app.send_motor_tuning_command_btn = tk.Button(cmd_input_frame, text="Send", 
                                            font=("Arial", 10, "bold"),
                                            bg=self.colors['accent_blue'], fg='white',
                                            command=main_app.send_motor_tuning_command)
        main_app.send_motor_tuning_command_btn.pack(side='left', padx=(0, 10))
        
        main_app.clear_motor_tuning_commands_btn = tk.Button(cmd_input_frame, text="Clear", 
                                              font=("Arial", 10, "bold"),
                                              bg=self.colors['warning_orange'], fg='white',
                                              command=main_app.clear_motor_tuning_command_history)
        main_app.clear_motor_tuning_commands_btn.pack(side='left')
        
        # Quick command buttons
        quick_cmd_frame = tk.Frame(command_content, bg=self.colors['main_bg'])
        quick_cmd_frame.pack(fill='x', pady=(10, 0))
        
        tk.Label(quick_cmd_frame, text="Quick Commands:", font=("Arial", 9, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        quick_buttons_frame = tk.Frame(quick_cmd_frame, bg=self.colors['main_bg'])
        quick_buttons_frame.pack(fill='x', pady=(5, 0))
        
        # Common commands
        common_commands = [
            ("TPA", "Tell Position A"),
            ("TPB", "Tell Position B"), 
            ("TPC", "Tell Position C"),
            ("TPD", "Tell Position D"),
            ("MOA", "Motor Off A"),
            ("SHA", "Servo Here A"),
            ("QHA", "Query Hall A"),
            ("MG _BMA", "Brushless Modulo A")
        ]
        
        for i, (cmd, desc) in enumerate(common_commands):
            btn = tk.Button(quick_buttons_frame, text=f"{cmd}", 
                          font=("Arial", 8), width=8,
                          bg=self.colors['secondary_bg'], fg=self.colors['main_fg'],
                          command=lambda c=cmd: main_app.insert_motor_tuning_command(c))
            btn.pack(side='left', padx=(0, 5), pady=2)
            
            # Add tooltip description
            self._create_tooltip(btn, desc)
        
        # Command history
        cmd_history_frame = tk.Frame(command_content, bg=self.colors['main_bg'])
        cmd_history_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        tk.Label(cmd_history_frame, text="Command History:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.motor_tuning_command_history_text = tk.Text(cmd_history_frame, height=8, width=80,
                                              font=("Courier", 9), bg=self.colors['card_bg'],
                                              fg=self.colors['main_fg'], relief='solid', bd=1)
        main_app.motor_tuning_command_history_text.pack(fill='both', expand=True, pady=(5, 0))
        
        # Add scrollbar to command history
        cmd_scrollbar = tk.Scrollbar(cmd_history_frame, orient="vertical", 
                                   command=main_app.motor_tuning_command_history_text.yview)
        main_app.motor_tuning_command_history_text.configure(yscrollcommand=cmd_scrollbar.set)
        cmd_scrollbar.pack(side="right", fill="y")
        
        # Motor tuning page complete
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_network_config_page(self, main_app):
        """Create the Network Config page GUI"""
        # Title
        title = tk.Label(self.scrollable_frame, text="Network Configuration", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Main network frame
        network_frame = tk.Frame(self.scrollable_frame, bg=self.colors['main_bg'])
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
        
        main_app.ip_entry = tk.Entry(ip_frame, font=("Arial", 10), width=15)
        main_app.ip_entry.pack(side='left', padx=(10, 0))
        # IP entry starts blank - no default value
        
        # Connect button
        connect_btn = tk.Button(ip_frame, text="Connect", 
                              font=("Arial", 10, "bold"),
                              bg=self.colors['accent_blue'], fg='white',
                              command=main_app.connect_to_controller)
        connect_btn.pack(side='left', padx=(10, 0))
        
        # Discover button
        discover_btn = tk.Button(ip_frame, text="Discover Controllers", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['warning_orange'], fg='white',
                               command=main_app.discover_controllers)
        discover_btn.pack(side='left', padx=(10, 0))
        
        # Quick IP change button (only show when connected)
        main_app.quick_ip_change_btn = tk.Button(ip_frame, text="🔧 Change IP", 
                                               font=("Arial", 10, "bold"),
                                               bg=self.colors['accent_blue'], fg='white',
                                               command=main_app.show_ip_change_walkthrough,
                                               state='disabled')
        main_app.quick_ip_change_btn.pack(side='left', padx=(10, 0))
        
        # Connection status label
        main_app.connection_status_label = tk.Label(ip_frame, text="Not Connected", 
                                              font=("Arial", 10, "bold"),
                                              bg=self.colors['main_bg'], fg=self.colors['error_red'])
        main_app.connection_status_label.pack(side='right', padx=(10, 0))
        
        # Controller Information Section
        controller_info_frame = tk.LabelFrame(network_frame, text="📋 Controller Information", 
                                           font=("Arial", 12, "bold"),
                                           bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                           relief='solid', bd=1)
        controller_info_frame.pack(fill='x', pady=(20, 20), padx=10)
        
        # Controller info content
        controller_info_content = tk.Frame(controller_info_frame, bg=self.colors['main_bg'])
        controller_info_content.pack(fill='x', padx=15, pady=15)
        
        # Current controller IP display
        current_ip_frame = tk.Frame(controller_info_content, bg=self.colors['main_bg'])
        current_ip_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(current_ip_frame, text="Current Controller IP:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.current_controller_ip_label = tk.Label(current_ip_frame, text="Not Connected", 
                                                      font=("Arial", 10, "bold"),
                                                      bg=self.colors['main_bg'], fg=self.colors['error_red'])
        main_app.current_controller_ip_label.pack(side='left', padx=(10, 0))
        
        # Controller details display
        details_frame = tk.Frame(controller_info_content, bg=self.colors['main_bg'])
        details_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(details_frame, text="Controller Details:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(anchor='w')
        
        main_app.controller_details_label = tk.Label(details_frame, text="No controller connected", 
                                                   font=("Arial", 9),
                                                   bg=self.colors['main_bg'], fg=self.colors['secondary_fg'],
                                                   justify='left')
        main_app.controller_details_label.pack(anchor='w', pady=(5, 0))
        
        # Refresh controller info button
        refresh_info_btn = tk.Button(controller_info_content, text="🔄 Refresh Controller Info",
                                   font=("Arial", 9, "bold"),
                                   bg=self.colors['accent_blue'], fg='white',
                                   command=main_app.refresh_controller_info)
        refresh_info_btn.pack(anchor='w', pady=(10, 0))
        
        # COM Port Connection Section
        com_frame = tk.LabelFrame(network_frame, text="🔌 USB/COM Port Connection",
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        com_frame.pack(fill='x', pady=(0, 20), padx=10)

        # COM port content
        com_content = tk.Frame(com_frame, bg=self.colors['main_bg'])
        com_content.pack(fill='x', padx=15, pady=15)

        # COM port description
        com_desc = tk.Label(com_content,
                          text="Connect to Galil controller via USB cable (COM port)",
                          font=("Arial", 10), bg=self.colors['main_bg'],
                          fg=self.colors['main_fg'])
        com_desc.pack(anchor='w', pady=(0, 10))

        # COM port selection
        com_selection_frame = tk.Frame(com_content, bg=self.colors['main_bg'])
        com_selection_frame.pack(fill='x', pady=(0, 10))

        tk.Label(com_selection_frame, text="COM Port:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')

        # COM port dropdown
        main_app.com_port_var = tk.StringVar()
        main_app.com_port_dropdown = tk.ttk.Combobox(com_selection_frame, 
                                                    textvariable=main_app.com_port_var,
                                                    width=10, state="readonly")
        main_app.com_port_dropdown.pack(side='left', padx=(10, 10))

        # Refresh COM ports button
        refresh_com_btn = tk.Button(com_selection_frame, text="🔄 Refresh COM Ports",
                                  font=("Arial", 9, "bold"),
                                  bg=self.colors['accent_blue'], fg='white',
                                  command=main_app.refresh_com_ports)
        refresh_com_btn.pack(side='left', padx=(0, 10))

        # Connect via COM port button
        connect_com_btn = tk.Button(com_selection_frame, text="🔌 Connect via COM Port",
                                  font=("Arial", 10, "bold"),
                                  bg=self.colors['success_green'], fg='white',
                                  command=main_app.connect_via_com_port)
        connect_com_btn.pack(side='left', padx=(0, 10))

        # Diagnose COM port button
        diagnose_com_btn = tk.Button(com_selection_frame, text="🔍 Diagnose COM Port",
                                   font=("Arial", 9, "bold"),
                                   bg=self.colors['warning_orange'], fg='white',
                                   command=main_app.diagnose_com_port)
        diagnose_com_btn.pack(side='left')

        # COM port status
        main_app.com_port_status_label = tk.Label(com_content,
                                                text="Click 'Refresh COM Ports' to detect available ports",
                                                font=("Arial", 9),
                                                bg=self.colors['main_bg'], fg=self.colors['secondary_fg'],
                                                justify='left')
        main_app.com_port_status_label.pack(anchor='w', pady=(10, 0))
        
        # Network Discovery Section
        discovery_frame = tk.LabelFrame(network_frame, text="🔍 Network Discovery", 
                                     font=("Arial", 12, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     relief='solid', bd=1)
        discovery_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Discovery content
        discovery_content = tk.Frame(discovery_frame, bg=self.colors['main_bg'])
        discovery_content.pack(fill='x', padx=15, pady=15)
        
        # Discovery description
        discovery_desc = tk.Label(discovery_content, 
                               text="Find all Galil controllers (network and COM ports) automatically",
                               font=("Arial", 10), bg=self.colors['main_bg'], 
                               fg=self.colors['main_fg'])
        discovery_desc.pack(anchor='w', pady=(0, 10))
        
        # Discovery buttons
        discovery_buttons_frame = tk.Frame(discovery_content, bg=self.colors['main_bg'])
        discovery_buttons_frame.pack(fill='x', pady=(0, 10))
        
        # Discover all button
        discover_btn = tk.Button(discovery_buttons_frame, text="🔍 Discover All Controllers", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['warning_orange'], fg='white',
                               command=main_app.discover_controllers)
        discover_btn.pack(side='left', padx=(0, 10))
        
        # Network only discovery button
        network_discover_btn = tk.Button(discovery_buttons_frame, text="🌐 Network Only",
                                       font=("Arial", 10, "bold"),
                                       bg=self.colors['accent_blue'], fg='white',
                                       command=main_app.discover_network_controllers)
        network_discover_btn.pack(side='left', padx=(0, 10))
        
        # COM port only discovery button
        com_discover_btn = tk.Button(discovery_buttons_frame, text="🔌 COM Ports Only",
                                   font=("Arial", 10, "bold"),
                                   bg=self.colors['success_green'], fg='white',
                                   command=main_app.discover_com_controllers)
        com_discover_btn.pack(side='left', padx=(0, 10))
        
        # Comprehensive search button
        comprehensive_search_btn = tk.Button(discovery_buttons_frame, text="🔍 Comprehensive Search", 
                                           font=("Arial", 10, "bold"),
                                           bg=self.colors['warning_orange'], fg='white',
                                           command=main_app.comprehensive_controller_search)
        comprehensive_search_btn.pack(side='left')
        
        # Discovery results display
        main_app.discovery_results_label = tk.Label(discovery_content, 
                                                   text="Click 'Discover All Controllers' to find controllers",
                                                   font=("Arial", 9),
                                                   bg=self.colors['main_bg'], fg=self.colors['secondary_fg'],
                                                   justify='left', wraplength=600)
        main_app.discovery_results_label.pack(anchor='w', pady=(10, 0))
        
        # Progress indicator (initially hidden)
        main_app.discovery_progress_label = tk.Label(discovery_content, 
                                                    text="⏳ Operation in progress...",
                                                    font=("Arial", 9, "bold"),
                                                    bg=self.colors['main_bg'], fg=self.colors['warning_orange'])
        main_app.discovery_progress_label.pack(anchor='w', pady=(5, 0))
        main_app.discovery_progress_label.pack_forget()  # Hide initially
        
        # IP Address Configuration section (IP only)
        config_frame = tk.LabelFrame(network_frame, text="IP Address Configuration", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        config_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Configuration inputs
        config_content = tk.Frame(config_frame, bg=self.colors['main_bg'])
        config_content.pack(fill='x', padx=15, pady=15)
        
        # IP Address (only)
        ip_config_frame = tk.Frame(config_content, bg=self.colors['main_bg'])
        ip_config_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(ip_config_frame, text="IP Address:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.config_ip_entry = tk.Entry(ip_config_frame, font=("Arial", 10), width=15)
        main_app.config_ip_entry.pack(side='left', padx=(10, 20))
        # Config IP entry starts blank - no default value
        
        # Configuration buttons
        config_buttons_frame = tk.Frame(config_content, bg=self.colors['main_bg'])
        config_buttons_frame.pack(fill='x', pady=(10, 0))
        
        apply_config_btn = tk.Button(config_buttons_frame, text="Apply Configuration", 
                                   font=("Arial", 10, "bold"),
                                   bg=self.colors['success_green'], fg='white',
                                   command=main_app.apply_network_config)
        apply_config_btn.pack(side='left', padx=(0, 10))
        
        reset_config_btn = tk.Button(config_buttons_frame, text="Reset to Defaults", 
                                   font=("Arial", 10, "bold"),
                                   bg=self.colors['warning_orange'], fg='white',
                                   command=main_app.reset_network_config)
        reset_config_btn.pack(side='left', padx=(0, 10))
        
        change_ip_btn = tk.Button(config_buttons_frame, text="🔧 Change Controller IP", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['accent_blue'], fg='white',
                                command=main_app.show_ip_change_walkthrough)
        change_ip_btn.pack(side='left')
        
        # Controller IP Change Section - More Prominent
        ip_change_frame = tk.LabelFrame(network_frame, text="🎯 Controller IP Address Change", 
                                      font=("Arial", 14, "bold"),
                                      bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                      relief='solid', bd=2)
        ip_change_frame.pack(fill='x', pady=(20, 20), padx=10)
        
        # IP Change content
        ip_change_content = tk.Frame(ip_change_frame, bg=self.colors['main_bg'])
        ip_change_content.pack(fill='x', padx=20, pady=20)
        
        # Warning notice
        warning_label = tk.Label(ip_change_content, 
                               text="⚠️ CHANGING CONTROLLER IP WILL CAUSE DISCONNECTION - RECONNECT REQUIRED",
                               font=("Arial", 12, "bold"), 
                               bg=self.colors['warning_orange'], fg='white',
                               relief='raised', bd=2)
        warning_label.pack(fill='x', pady=(0, 15))
        
        # Current network info
        current_info_frame = tk.Frame(ip_change_content, bg=self.colors['main_bg'])
        current_info_frame.pack(fill='x', pady=(0, 15))
        
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network_base = '.'.join(local_ip.split('.')[:-1])
        except:
            local_ip = "Unknown"
            network_base = "192.168.1"
        
        tk.Label(current_info_frame, text=f"Your Computer IP: {local_ip}", 
                font=("Arial", 10, "bold"), bg=self.colors['main_bg'], 
                fg=self.colors['main_fg']).pack(anchor='w')
        # Removed suggested controller IP per requirements
        
        # Quick IP change buttons
        quick_buttons_frame = tk.Frame(ip_change_content, bg=self.colors['main_bg'])
        quick_buttons_frame.pack(fill='x', pady=(0, 15))
        
        # Connect first button
        connect_first_btn = tk.Button(quick_buttons_frame, text="1️⃣ Connect to Controller First", 
                                    font=("Arial", 11, "bold"),
                                    bg=self.colors['warning_orange'], fg='white',
                                    command=main_app.connect_to_controller)
        connect_first_btn.pack(side='left', padx=(0, 10))
        
        # Change IP button (disabled until connected)
        main_app.main_ip_change_btn = tk.Button(quick_buttons_frame, text="2️⃣ Change Controller IP", 
                                              font=("Arial", 11, "bold"),
                                              bg=self.colors['success_green'], fg='white',
                                              command=main_app.show_ip_change_walkthrough,
                                              state='disabled')
        main_app.main_ip_change_btn.pack(side='left', padx=(0, 10))
        
        # Instructions
        instructions_frame = tk.Frame(ip_change_content, bg=self.colors['card_bg'], relief='solid', bd=1)
        instructions_frame.pack(fill='x', pady=(0, 10))
        
        instructions_text = tk.Text(instructions_frame, height=6, wrap='word', 
                                  font=("Arial", 9), bg=self.colors['card_bg'], 
                                  fg=self.colors['main_fg'], relief='flat')
        instructions_text.pack(fill='x', padx=10, pady=10)
        instructions_text.insert('1.0', 
            "STEP-BY-STEP INSTRUCTIONS:\n\n"
            "1. First, connect to your controller using its current IP address\n"
            "2. Click 'Change Controller IP' to open the IP change dialog\n"
            "3. Enter new IP address (suggested: same network as your computer)\n"
            "4. Confirm the change - controller will reset and disconnect\n"
            "5. Reconnect using the new IP address\n\n"
            "This solves network connectivity issues by putting controller on same network as your computer.")
        instructions_text.config(state='disabled')
        
        # Controller Recovery Checklist Section
        recovery_frame = tk.LabelFrame(network_frame, text="🚨 Controller Recovery Checklist", 
                                     font=("Arial", 14, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     relief='solid', bd=2)
        recovery_frame.pack(fill='x', pady=(20, 20), padx=10)
        
        # Recovery content
        recovery_content = tk.Frame(recovery_frame, bg=self.colors['main_bg'])
        recovery_content.pack(fill='x', padx=20, pady=20)
        
        # Recovery description
        recovery_desc = tk.Label(recovery_content, 
                               text="Step-by-step troubleshooting guide for DMC-41x3 controllers when communication fails",
                               font=("Arial", 10), bg=self.colors['main_bg'], 
                               fg=self.colors['main_fg'])
        recovery_desc.pack(anchor='w', pady=(0, 15))
        
        # Recovery checklist button
        recovery_btn = tk.Button(recovery_content, text="🔧 Start Recovery Checklist", 
                               font=("Arial", 12, "bold"),
                               bg=self.colors['error_red'], fg='white',
                               command=main_app.show_recovery_checklist)
        recovery_btn.pack(anchor='w', pady=(0, 10))
        
        # Recovery info
        recovery_info = tk.Label(recovery_content, 
                               text="This checklist guides you through safe recovery procedures:\n"
                                    "• Hardware basics verification\n"
                                    "• Normal communication attempts\n"
                                    "• MRST (factory reset)\n"
                                    "• 19.2 baud jumper\n"
                                    "• UPGD bootloader recovery\n"
                                    "• MO (motors off) for safe comms\n"
                                    "• Advanced troubleshooting steps",
                               font=("Arial", 9), bg=self.colors['main_bg'], 
                               fg=self.colors['secondary_fg'], justify='left')
        recovery_info.pack(anchor='w', pady=(0, 10))
        
        # Network config page complete
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_settings_page(self, main_app):
        """Create the Settings page GUI"""
        # Title
        title = tk.Label(self.scrollable_frame, text="Settings", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Settings content
        settings_frame = tk.Frame(self.scrollable_frame, bg=self.colors['main_bg'])
        settings_frame.pack(fill='both', expand=True)
        
        # General Settings Section
        general_frame = tk.LabelFrame(settings_frame, text="General Settings", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        general_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # General settings content
        general_content = tk.Frame(general_frame, bg=self.colors['main_bg'])
        general_content.pack(fill='x', padx=15, pady=15)
        
        # Auto-connect setting
        auto_connect_frame = tk.Frame(general_content, bg=self.colors['main_bg'])
        auto_connect_frame.pack(fill='x', pady=(0, 10))
        
        main_app.auto_connect_var = tk.BooleanVar(value=True)
        auto_connect_check = tk.Checkbutton(auto_connect_frame, text="Auto-connect to controller on startup", 
                                           font=("Arial", 10),
                                           bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                           variable=main_app.auto_connect_var)
        auto_connect_check.pack(anchor='w')
        
        # Default IP setting
        default_ip_frame = tk.Frame(general_content, bg=self.colors['main_bg'])
        default_ip_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(default_ip_frame, text="Default IP Address:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.default_ip_entry = tk.Entry(default_ip_frame, font=("Arial", 10), width=15)
        main_app.default_ip_entry.pack(side='left', padx=(10, 0))
        main_app.default_ip_entry.insert(0, "10.1.0.21")
        
        # Save settings button
        save_settings_btn = tk.Button(general_content, text="💾 Save Settings", 
                                     font=("Arial", 10, "bold"),
                                     bg=self.colors['success_green'], fg='white',
                                     command=main_app.save_settings)
        save_settings_btn.pack(anchor='w', pady=(10, 0))
        
        # Controller Settings Section
        controller_frame = tk.LabelFrame(settings_frame, text="Controller Settings", 
                                       font=("Arial", 12, "bold"),
                                       bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                       relief='solid', bd=1)
        controller_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Controller settings content
        controller_content = tk.Frame(controller_frame, bg=self.colors['main_bg'])
        controller_content.pack(fill='x', padx=15, pady=15)
        
        # Default motion parameters
        motion_params_frame = tk.Frame(controller_content, bg=self.colors['main_bg'])
        motion_params_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(motion_params_frame, text="Default Speed:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.default_speed_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=10)
        main_app.default_speed_entry.pack(side='left', padx=(10, 20))
        main_app.default_speed_entry.insert(0, "5000")
        
        tk.Label(motion_params_frame, text="Default Acceleration:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.default_accel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=10)
        main_app.default_accel_entry.pack(side='left', padx=(10, 20))
        main_app.default_accel_entry.insert(0, "1000")
        
        tk.Label(motion_params_frame, text="Default Deceleration:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.default_decel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=10)
        main_app.default_decel_entry.pack(side='left', padx=(10, 0))
        main_app.default_decel_entry.insert(0, "2000")
        
        # Apply controller settings button
        apply_controller_btn = tk.Button(controller_content, text="⚙️ Apply Controller Settings", 
                                        font=("Arial", 10, "bold"),
                                        bg=self.colors['accent_blue'], fg='white',
                                        command=main_app.apply_controller_settings)
        apply_controller_btn.pack(anchor='w', pady=(10, 0))
        
        # Settings page complete
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_controller_testing_page(self, main_app):
        """Create the Controller Testing page GUI"""
        # Title
        title = tk.Label(self.scrollable_frame, text="Controller Testing", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Main content frame
        main_frame = tk.Frame(self.scrollable_frame, bg=self.colors['main_bg'])
        main_frame.pack(fill='both', expand=True)
        
        # 1. ENCODER POSITION DISPLAY (TOP)
        encoder_frame = tk.LabelFrame(main_frame, text="Real-time Encoder Positions", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        encoder_frame.pack(fill='x', pady=(0, 10))
        
        # Encoder position display
        encoder_display_frame = tk.Frame(encoder_frame, bg=self.colors['main_bg'])
        encoder_display_frame.pack(fill='x', padx=15, pady=10)
        
        # Create labels for each axis position
        main_app.encoder_labels = {}
        axes = ["A", "B", "C", "D"]
        
        for i, axis in enumerate(axes):
            # Axis label
            axis_label = tk.Label(encoder_display_frame, text=f"Axis {axis}:", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                width=8)
            axis_label.grid(row=i, column=0, padx=(0, 5), pady=5, sticky='w')
            
            # Position value label
            pos_label = tk.Label(encoder_display_frame, text="0", 
                               font=("Consolas", 12, "bold"),
                               bg='white', fg='black', relief='sunken', bd=1,
                               width=12)
            pos_label.grid(row=i, column=1, padx=(0, 10), pady=5, sticky='w')
            main_app.encoder_labels[axis] = pos_label
        
        # Update button
        update_btn = tk.Button(encoder_frame, text="🔄 Update Positions", 
                             font=("Arial", 10, "bold"),
                             bg=self.colors['accent_blue'], fg='white',
                             command=main_app.update_encoder_positions)
        update_btn.pack(pady=(0, 10))
        
        # Test connection button
        test_btn = tk.Button(encoder_frame, text="🔍 Test Connection", 
                           font=("Arial", 10, "bold"),
                           bg=self.colors['success_green'], fg='white',
                           command=main_app.test_controller_connection)
        test_btn.pack(pady=(0, 10))
        
        # Comprehensive motor test button
        comprehensive_test_btn = tk.Button(encoder_frame, text="🧪 Comprehensive Motor Test", 
                                         font=("Arial", 12, "bold"),
                                         bg=self.colors['error_red'], fg='white',
                                         command=main_app.run_comprehensive_motor_test)
        comprehensive_test_btn.pack(pady=(0, 10))
        
        # Auto-update checkbox - HIDDEN per user requirements (encoder always visible, no toggle)
        # main_app.auto_update_var = tk.BooleanVar(value=True)
        # auto_update_check = tk.Checkbutton(encoder_frame, text="Auto-update positions every 0.5 seconds", 
        #                                  font=("Arial", 9),
        #                                  bg=self.colors['main_bg'], fg=self.colors['main_fg'],
        #                                  variable=main_app.auto_update_var,
        #                                  command=main_app.toggle_auto_update)
        # auto_update_check.pack(pady=(0, 10))
        
        # Auto-update is always enabled - no toggle needed
        auto_update_label = tk.Label(encoder_frame, text="Auto-update enabled (always visible)", 
                                   font=("Arial", 9),
                                   bg=self.colors['main_bg'], fg=self.colors['secondary_fg'])
        auto_update_label.pack(pady=(0, 10))
        
        # 2. JOG CONTROLS SECTION
        jog_frame = tk.LabelFrame(main_frame, text="Jog Controls", 
                                font=("Arial", 12, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                relief='solid', bd=1)
        jog_frame.pack(fill='x', pady=(0, 10))
        
        # Axis selection for jog
        jog_axis_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_axis_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(jog_axis_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.jog_axis_var = tk.StringVar(value="A")
        jog_axis_combo = ttk.Combobox(jog_axis_frame, textvariable=main_app.jog_axis_var, 
                                     values=["A", "B", "C", "D"], width=10)
        jog_axis_combo.pack(side='left', padx=(10, 20))
        
        # Jog distance
        tk.Label(jog_axis_frame, text="Distance:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.jog_distance_entry = tk.Entry(jog_axis_frame, font=("Arial", 10), width=10)
        main_app.jog_distance_entry.pack(side='left', padx=(10, 20))
        main_app.jog_distance_entry.insert(0, "1000")
        
        # Jog buttons
        jog_buttons_frame = tk.Frame(jog_frame, bg=self.colors['main_bg'])
        jog_buttons_frame.pack(fill='x', padx=15, pady=(0, 10))
        
        jog_neg_btn = tk.Button(jog_buttons_frame, text="← Jog -", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['warning_orange'], fg='white',
                               command=main_app.jog_negative)
        jog_neg_btn.pack(side='left', padx=(0, 10))
        
        jog_pos_btn = tk.Button(jog_buttons_frame, text="Jog + →", 
                               font=("Arial", 10, "bold"),
                               bg=self.colors['success_green'], fg='white',
                               command=main_app.jog_positive)
        jog_pos_btn.pack(side='left')
        
        # Stop button
        stop_btn = tk.Button(jog_buttons_frame, text="⏹ Stop", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['error_red'], fg='white',
                            command=main_app.stop_all_motion)
        stop_btn.pack(side='right')
        
        # 3. MOTION PARAMETERS SECTION
        params_frame = tk.LabelFrame(main_frame, text="Motion Parameters", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        params_frame.pack(fill='x', pady=(0, 10))
        
        # Speed and acceleration
        motion_params_frame = tk.Frame(params_frame, bg=self.colors['main_bg'])
        motion_params_frame.pack(fill='x', padx=15, pady=10)
        
        # Speed
        tk.Label(motion_params_frame, text="Speed:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=0, sticky='w')
        main_app.speed_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        main_app.speed_entry.grid(row=0, column=1, padx=(10, 20))
        main_app.speed_entry.insert(0, "5000")
        
        # Acceleration
        tk.Label(motion_params_frame, text="Acceleration:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=2, sticky='w')
        main_app.accel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        main_app.accel_entry.grid(row=0, column=3, padx=(10, 20))
        main_app.accel_entry.insert(0, "1000")
        
        # Deceleration
        tk.Label(motion_params_frame, text="Deceleration:", font=("Arial", 10),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).grid(row=0, column=4, sticky='w')
        main_app.decel_entry = tk.Entry(motion_params_frame, font=("Arial", 10), width=15)
        main_app.decel_entry.grid(row=0, column=5, padx=(10, 0))
        main_app.decel_entry.insert(0, "2000")
        
        # Apply button
        apply_btn = tk.Button(params_frame, text="Apply Parameters", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['accent_blue'], fg='white',
                            command=main_app.apply_motion_params)
        apply_btn.pack(pady=(0, 10))
        
        # 4. MOTION TESTING SECTION
        motion_frame = tk.LabelFrame(main_frame, text="Motion Testing", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   relief='solid', bd=1)
        motion_frame.pack(fill='x', pady=(0, 10))
        
        # Motion controls
        motion_controls_frame = tk.Frame(motion_frame, bg=self.colors['main_bg'])
        motion_controls_frame.pack(fill='x', padx=15, pady=10)
        
        # Axis selection
        tk.Label(motion_controls_frame, text="Axis:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.test_axis_var = tk.StringVar(value="A")
        test_axis_combo = ttk.Combobox(motion_controls_frame, textvariable=main_app.test_axis_var, 
                                      values=["A", "B", "C", "D"], width=10)
        test_axis_combo.pack(side='left', padx=(10, 20))
        
        # Distance input
        tk.Label(motion_controls_frame, text="Distance:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.test_distance_entry = tk.Entry(motion_controls_frame, font=("Arial", 10), width=10)
        main_app.test_distance_entry.pack(side='left', padx=(10, 20))
        main_app.test_distance_entry.insert(0, "1000")
        
        # Motion buttons
        motion_buttons_frame = tk.Frame(motion_frame, bg=self.colors['main_bg'])
        motion_buttons_frame.pack(fill='x', padx=15, pady=(0, 10))
        
        move_neg_btn = tk.Button(motion_buttons_frame, text="← Move -", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['warning_orange'], fg='white',
                                command=main_app.test_move_negative)
        move_neg_btn.pack(side='left', padx=(0, 10))
        
        move_pos_btn = tk.Button(motion_buttons_frame, text="Move + →", 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['success_green'], fg='white',
                                command=main_app.test_move_positive)
        move_pos_btn.pack(side='left', padx=(0, 10))
        
        stop_btn = tk.Button(motion_buttons_frame, text="⏹ Stop", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['error_red'], fg='white',
                            command=main_app.stop_all_motion)
        stop_btn.pack(side='left')
        
        # 3. COMMAND TESTING SECTION
        command_frame = tk.LabelFrame(main_frame, text="Command Testing", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                    relief='solid', bd=1)
        command_frame.pack(fill='x', pady=(0, 10))
        
        # Command input
        command_input_frame = tk.Frame(command_frame, bg=self.colors['main_bg'])
        command_input_frame.pack(fill='x', padx=15, pady=10)
        
        tk.Label(command_input_frame, text="Command:", font=("Arial", 10, "bold"),
               bg=self.colors['main_bg'], fg=self.colors['main_fg']).pack(side='left')
        
        main_app.command_entry = tk.Entry(command_input_frame, font=("Arial", 10), width=20)
        main_app.command_entry.pack(side='left', padx=(10, 10))
        main_app.command_entry.insert(0, "TP")
        
        # Send command button
        send_btn = tk.Button(command_input_frame, text="Send Command", 
                            font=("Arial", 10, "bold"),
                            bg=self.colors['accent_blue'], fg='white',
                            command=main_app.send_test_command)
        send_btn.pack(side='left')
        
        # Controller testing page complete
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_visual_testing_page(self, main_app):
        """Create the Visual Testing page GUI"""
        # Title
        title = tk.Label(self.scrollable_frame, text="Visual Motor Testing", 
                        font=("Arial", 24, "bold"), 
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w', pady=(0, 20))
        
        # Description
        desc = tk.Label(self.scrollable_frame, 
                       text="Interactive visual testing with real-time progress tracking and detailed step-by-step monitoring.",
                       font=("Arial", 12),
                       bg=self.colors['main_bg'], fg=self.colors['secondary_fg'],
                       wraplength=800)
        desc.pack(anchor='w', pady=(0, 20))
        
        # Main content frame for visual testing interface
        visual_frame = tk.Frame(self.scrollable_frame, bg=self.colors['main_bg'])
        visual_frame.pack(fill='both', expand=True)
        
        # Create visual testing interface
        from visual_testing_interface import VisualTestingInterface
        self.visual_testing_interface = VisualTestingInterface(visual_frame, self.colors, main_app)
        
        # Visual testing page complete
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_persistent_log(self):
        """Create a persistent log that stays at the bottom of the window across all pages"""
        # Create persistent log frame at bottom of window
        self.persistent_log_frame = tk.Frame(self.root, bg=self.colors['main_bg'], relief='raised', bd=1)
        self.persistent_log_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=(5, 10))
        
        # Configure column weights for the log frame
        self.persistent_log_frame.grid_columnconfigure(1, weight=1)
        
        # Toggle button (always visible)
        self.toggle_log_btn = tk.Button(self.persistent_log_frame, text="📋 Show Log", 
                                      font=("Arial", 10, "bold"),
                                      bg=self.colors['accent_blue'], fg='white',
                                      command=self.toggle_persistent_log)
        self.toggle_log_btn.grid(row=0, column=0, padx=(10, 5), pady=5, sticky='w')
        
        # Log content frame (initially hidden)
        self.log_content_frame = tk.Frame(self.persistent_log_frame, bg=self.colors['main_bg'])
        
        # Log title
        log_title = tk.Label(self.log_content_frame, text="📋 Persistent Log (All Pages)", 
                           font=("Arial", 12, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        log_title.pack(anchor='w', pady=(5, 5))
        
        # Log text area
        self.persistent_log_text = scrolledtext.ScrolledText(self.log_content_frame, 
                                                           height=8, font=("Consolas", 9),
                                                           bg='white', fg='black')
        self.persistent_log_text.pack(fill='both', expand=True, padx=10, pady=(0, 5))
        
        # Log control buttons
        log_buttons_frame = tk.Frame(self.log_content_frame, bg=self.colors['main_bg'])
        log_buttons_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Copy log button
        copy_log_btn = tk.Button(log_buttons_frame, text="📋 Copy Log", 
                               font=("Arial", 9, "bold"),
                               bg=self.colors['accent_blue'], fg='white',
                               command=self.copy_persistent_log)
        copy_log_btn.pack(side='left', padx=(0, 10))
        
        # Clear log button
        clear_log_btn = tk.Button(log_buttons_frame, text="🗑️ Clear Log", 
                                font=("Arial", 9, "bold"),
                                bg=self.colors['warning_orange'], fg='white',
                                command=self.clear_persistent_log)
        clear_log_btn.pack(side='left')
        
        # Initialize log state
        self.persistent_log_visible = False
        
        # Add initial log message
        self.persistent_log_text.insert(tk.END, "=== PERSISTENT LOG STARTED ===\n")
        self.persistent_log_text.insert(tk.END, "This log maintains data across all pages.\n")
        self.persistent_log_text.insert(tk.END, "Use 'Show/Hide Log' to toggle visibility.\n\n")
    
    def toggle_persistent_log(self):
        """Toggle the visibility of the persistent log"""
        if self.persistent_log_visible:
            # Hide log
            self.log_content_frame.grid_remove()
            self.persistent_log_visible = False
            self.toggle_log_btn.configure(text="📋 Show Log")
        else:
            # Show log
            self.log_content_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 5))
            self.persistent_log_visible = True
            self.toggle_log_btn.configure(text="📋 Hide Log")
    
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
    
    def log_message(self, message):
        """Add message to persistent log with timestamp"""
        try:
            if hasattr(self, 'persistent_log_text') and self.persistent_log_text.winfo_exists():
                timestamp = time.strftime('%H:%M:%S')
                self.persistent_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.persistent_log_text.see(tk.END)
            else:
                print(f"DEBUG: Persistent log text widget not available: {message}")
        except Exception as e:
            print(f"DEBUG: Error logging message '{message}': {e}")
