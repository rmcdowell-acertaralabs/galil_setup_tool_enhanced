"""
IO Setup Dialog for Limit and Home Switches Configuration
Shows real-time switch status and allows configuration
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time

class IOSetupDialog:
    """Dialog for configuring limit and home switches"""
    
    def __init__(self, parent, colors, main_app):
        self.parent = parent
        self.colors = colors
        self.main_app = main_app
        
        # State tracking
        self.update_running = False
        self.update_thread = None
        self.switch_status = {}  # {axis: {type: bool}}
        self.last_switch_values = {}  # For debouncing
        self.switch_stability_count = {}  # Count consecutive stable readings
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Step by Step")
        self.dialog.geometry("750x600")
        self.dialog.configure(bg=self.colors['main_bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        self.create_widgets()
        self.start_switch_updates()
        
        # Update dialog size after widgets are created, then center
        self.dialog.update_idletasks()
        self.dialog.minsize(750, 600)
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Title
        title_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        title_frame.pack(fill='x', pady=(15, 10), padx=20)
        
        title = tk.Label(title_frame, text="Limit and Home Switches Setup",
                        font=("Arial", 14, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack()
        
        # Main content area
        content_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left side - Switch grid
        left_frame = tk.Frame(content_frame, bg=self.colors['main_bg'])
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 20))
        
        # Grid title
        grid_title = tk.Label(left_frame, text="Switch Status:",
                             font=("Arial", 10, "bold"),
                             bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        grid_title.pack(anchor='w', pady=(0, 10))
        
        # Create switch grid
        self.create_switch_grid(left_frame)
        
        # Action buttons
        button_frame = tk.Frame(left_frame, bg=self.colors['main_bg'])
        button_frame.pack(fill='x', pady=(20, 0))
        
        limit_btn = tk.Button(button_frame, text="Limit",
                             font=("Arial", 10, "bold"),
                             bg=self.colors['accent_blue'], fg='white',
                             command=self.limit_action,
                             width=12, height=2)
        limit_btn.pack(side='left', padx=(0, 10))
        
        # Add tooltip for Limit button
        self.create_tooltip(limit_btn, "Invert Limit Switch Polarity")
        
        home_btn = tk.Button(button_frame, text="Home",
                            font=("Arial", 10, "bold"),
                            bg=self.colors['accent_blue'], fg='white',
                            command=self.home_action,
                            width=12, height=2)
        home_btn.pack(side='left')
        
        # Add tooltip for Home button
        self.create_tooltip(home_btn, "Invert Home Switch Polarity")
        
        # Right side - Instructions
        right_frame = tk.Frame(content_frame, bg=self.colors['main_bg'])
        right_frame.pack(side='right', fill='y')
        right_frame.config(width=300)
        
        instructions_title = tk.Label(right_frame, text="Instructions:",
                                     font=("Arial", 10, "bold"),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        instructions_title.pack(anchor='w', pady=(0, 10))
        
        instructions_text = (
            "1. Ensure your limit and home switches are correctly wired. "
            "See Limit and Home switch wiring.\n\n"
            "2. Ensure that all switches are inactive (green). "
            "Invert the polarity of limit or home switches as needed.\n\n"
            "3. If it is necessary to individually invert an axis, "
            "it will have to be manually rewired.\n\n"
            "4. Once all switches are inactive (green), manually activate "
            "each home and limit switch to verify working status."
        )
        
        instructions_label = tk.Label(right_frame, text=instructions_text,
                                     font=("Arial", 9),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     justify='left', anchor='w', wraplength=280)
        instructions_label.pack(anchor='w')
        
        # Make "Limit and Home switch wiring" clickable
        link_frame = tk.Frame(right_frame, bg=self.colors['main_bg'])
        link_frame.pack(anchor='w', pady=(5, 0))
        
        link_text = tk.Label(link_frame, text="Limit and Home switch wiring",
                            font=("Arial", 9, "underline"),
                            bg=self.colors['main_bg'], fg='blue',
                            cursor='hand2')
        link_text.pack(anchor='w')
        link_text.bind('<Button-1>', lambda e: self.show_wiring_info())
        
        # Navigation buttons
        nav_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        nav_frame.pack(side='bottom', fill='x', pady=(10, 15), padx=20)
        
        # Back button
        back_btn = tk.Button(nav_frame, text="< Back",
                            font=("Arial", 10, "bold"),
                            bg=self.colors['card_bg'], fg=self.colors['main_fg'],
                            command=self.go_back,
                            width=10)
        back_btn.pack(side='left')
        
        # Next button
        next_btn = tk.Button(nav_frame, text="Next >",
                            font=("Arial", 10, "bold"),
                            bg=self.colors['success_green'], fg='white',
                            command=self.go_next,
                            width=10)
        next_btn.pack(side='right')
    
    def create_switch_grid(self, parent):
        """Create the switch status grid"""
        grid_frame = tk.Frame(parent, bg=self.colors['card_bg'], relief='solid', bd=2)
        grid_frame.pack(fill='both', expand=True)
        
        # Header row
        header_frame = tk.Frame(grid_frame, bg=self.colors['card_bg'])
        header_frame.pack(fill='x', pady=10, padx=10)
        
        # Empty cell for axis labels
        tk.Label(header_frame, text="", width=8, bg=self.colors['card_bg']).grid(row=0, column=0)
        
        # Column headers
        headers = [("←", "Negative Limit"), ("⌂", "Home"), ("→", "Positive Limit")]
        for col, (icon, tooltip) in enumerate(headers, 1):
            header_cell = tk.Frame(header_frame, bg=self.colors['card_bg'])
            header_cell.grid(row=0, column=col, padx=15)
            
            tk.Label(header_cell, text=icon, font=("Arial", 14, "bold"),
                    bg=self.colors['card_bg'], fg=self.colors['main_fg']).pack()
            tk.Label(header_cell, text=tooltip.split()[0], font=("Arial", 8),
                    bg=self.colors['card_bg'], fg=self.colors['main_fg']).pack()
        
        # Switch indicators storage
        self.switch_indicators = {}
        
        # Create rows for each axis
        for row, axis in enumerate(['A', 'B', 'C', 'D'], 1):
            row_frame = tk.Frame(grid_frame, bg=self.colors['card_bg'])
            row_frame.pack(fill='x', padx=10, pady=8)
            
            # Axis label
            axis_label = tk.Label(row_frame, text=axis, font=("Arial", 12, "bold"),
                                 bg=self.colors['card_bg'], fg=self.colors['main_fg'], width=8)
            axis_label.grid(row=0, column=0)
            
            # Initialize switch status
            if axis not in self.switch_status:
                self.switch_status[axis] = {
                    'negative': False,
                    'home': False,
                    'positive': False
                }
            
            # Create indicators for each switch type
            self.switch_indicators[axis] = {}
            
            switch_types = ['negative', 'home', 'positive']
            for col, switch_type in enumerate(switch_types, 1):
                indicator_frame = tk.Frame(row_frame, bg=self.colors['card_bg'])
                indicator_frame.grid(row=0, column=col, padx=15)
                
                # Circular indicator
                canvas = tk.Canvas(indicator_frame, width=30, height=30, 
                                 bg=self.colors['card_bg'], highlightthickness=0)
                canvas.pack()
                
                # Draw circle (initially green for inactive)
                circle = canvas.create_oval(5, 5, 25, 25, fill='green', outline='black', width=2)
                
                self.switch_indicators[axis][switch_type] = {
                    'canvas': canvas,
                    'circle': circle
                }
    
    def update_switch_indicator(self, axis, switch_type, active):
        """Update a switch indicator color"""
        if axis in self.switch_indicators and switch_type in self.switch_indicators[axis]:
            canvas = self.switch_indicators[axis][switch_type]['canvas']
            circle = self.switch_indicators[axis][switch_type]['circle']
            
            # Only update if status actually changed
            current_status = self.switch_status.get(axis, {}).get(switch_type, None)
            if current_status == active:
                return  # No change, skip update
            
            # Determine color based on switch type
            if switch_type == 'home':
                # Home switches: Green = inactive, Yellow = active
                color = 'yellow' if active else 'green'
            else:
                # Limit switches: Green = inactive, Red = active
                color = 'red' if active else 'green'
            
            canvas.itemconfig(circle, fill=color)
            
            # Update status tracking
            if axis not in self.switch_status:
                self.switch_status[axis] = {}
            self.switch_status[axis][switch_type] = active
            
            # Log switch state changes for debugging
            if self.main_app:
                switch_name = f"{switch_type} limit" if switch_type != 'home' else "home"
                self.main_app.append_test_log(f"Switch {axis} {switch_name}: {'ACTIVE' if active else 'inactive'}")
    
    def start_switch_updates(self):
        """Start real-time switch status updates"""
        if not self.main_app or not self.main_app.controller:
            return
        
        self.update_running = True
        self._debug_counter = 0  # Initialize debug counter
        self.update_thread = threading.Thread(target=self.update_switch_loop, daemon=True)
        self.update_thread.start()
        
        # Log startup
        if self.main_app:
            self.main_app.append_test_log("I/O switch monitoring started")
    
    def update_switch_loop(self):
        """Update switch status in real-time with debouncing"""
        DEBOUNCE_COUNT = 3  # Require 3 consecutive readings to change state
        
        while self.update_running:
            try:
                if self.main_app and self.main_app.controller:
                    for axis in ['A', 'B', 'C', 'D']:
                        try:
                            # Initialize tracking for this axis if needed
                            if axis not in self.last_switch_values:
                                self.last_switch_values[axis] = {'negative': False, 'home': False, 'positive': False}
                                self.switch_stability_count[axis] = {'negative': 0, 'home': 0, 'positive': 0}
                            
                            # Read axis switch status using TS command (try both validated and unvalidated)
                            ts_response = None
                            try:
                                ts_response = self.main_app.controller.send_command_unvalidated(f"MG _TS{axis}")
                            except:
                                try:
                                    ts_response = self.main_app.controller.send_command(f"MG _TS{axis}")
                                except:
                                    pass
                            
                            if ts_response and ts_response.strip() != '?' and not ts_response.strip().startswith('?'):
                                try:
                                    # Clean the response - handle cases like "0\r\n: 15.0000"
                                    clean_response = ts_response.strip()
                                    # Remove any carriage returns and newlines, then extract number
                                    clean_response = clean_response.replace('\r', '').replace('\n', ' ')
                                    # If there's a colon, take the part after it
                                    if ':' in clean_response:
                                        clean_response = clean_response.split(':')[-1].strip()
                                    # Take first number if there are multiple
                                    if ',' in clean_response:
                                        clean_response = clean_response.split(',')[0]
                                    # Extract just the numeric part
                                    import re
                                    numbers = re.findall(r'-?\d+\.?\d*', clean_response)
                                    if numbers:
                                        ts_value = int(float(numbers[0]))
                                    else:
                                        continue
                                    
                                    # Parse TS bits
                                    # Bit 3: Forward limit inactive (invert for active status)
                                    # Bit 2: Reverse limit inactive (invert for active status)
                                    # Bit 1: Home switch active
                                    positive_active = not bool((ts_value >> 3) & 1)  # 0 when inactive
                                    negative_active = not bool((ts_value >> 2) & 1)  # 0 when inactive
                                    home_active = bool((ts_value >> 1) & 1)  # 1 when active
                                    
                                    # Debug: log switch states on first axis only to avoid spam
                                    if axis == 'A' and hasattr(self, '_debug_counter'):
                                        self._debug_counter += 1
                                        if self._debug_counter % 50 == 0:  # Log every 5 seconds
                                            if self.main_app:
                                                self.main_app.append_test_log(f"Switch status A: TS={ts_value} (pos={positive_active}, neg={negative_active}, home={home_active})")
                                    elif axis == 'A' and not hasattr(self, '_debug_counter'):
                                        self._debug_counter = 0
                                    
                                    # Debounce each switch type
                                    for switch_type, current_state in [('negative', negative_active), 
                                                                       ('home', home_active), 
                                                                       ('positive', positive_active)]:
                                        last_state = self.last_switch_values[axis][switch_type]
                                        
                                        if current_state == last_state:
                                            # State is stable, increment counter
                                            self.switch_stability_count[axis][switch_type] += 1
                                            # Only update if state is stable for DEBOUNCE_COUNT readings
                                            if self.switch_stability_count[axis][switch_type] == DEBOUNCE_COUNT:
                                                # Update UI (must be in main thread)
                                                if self.dialog.winfo_exists():
                                                    self.dialog.after(0, lambda a=axis, t=switch_type, s=current_state:
                                                                     self.update_switch_indicator(a, t, s))
                                                # Update last_state after confirming stability
                                                self.last_switch_values[axis][switch_type] = current_state
                                        else:
                                            # State changed, reset counter
                                            self.switch_stability_count[axis][switch_type] = 0
                                            # Don't update last_state yet - wait for stability
                                
                                except (ValueError, IndexError, TypeError) as e:
                                    # Skip this reading if parsing fails
                                    if axis == 'A' and self.main_app:
                                        if not hasattr(self, '_parse_error_count'):
                                            self._parse_error_count = 0
                                        self._parse_error_count += 1
                                        if self._parse_error_count <= 3:
                                            self.main_app.append_test_log(f"Switch parse error: {e}")
                                    continue
                        except:
                            pass
            except Exception as e:
                pass
            
            time.sleep(0.1)  # Update 10 times per second for better debouncing
    
    def limit_action(self):
        """Handle Limit button click - invert limit switch polarity"""
        if not self.main_app or not self.main_app.controller:
            messagebox.showerror("Error", "No controller connected")
            return
        
        try:
            # CN is a global command: CN n0,n1,n2,n3,n4
            # n0: Limit switches (-1 = active low, 1 = active high)
            # Get current CN values
            cn0_response = self.main_app.controller.send_command("MG _CN0")
            cn1_response = self.main_app.controller.send_command("MG _CN1")
            
            cn0 = int(float(cn0_response.split(',')[0] if cn0_response else "-1"))
            cn1 = int(float(cn1_response.split(',')[0] if cn1_response else "-1"))
            
            # Toggle limit switch polarity (n0)
            new_cn0 = -cn0 if cn0 != 0 else 1  # Toggle between -1 and 1
            
            # Apply new CN command with all parameters
            # We keep other values the same (cn1 for home, and defaults for n2,n3,n4)
            self.main_app.controller.send_command(f"CN {new_cn0},{cn1},-1,0,0")
            
            if self.main_app:
                self.main_app.append_test_log(f"Limit switch polarity inverted (CN0: {cn0} -> {new_cn0})")
            
            messagebox.showinfo("Limit Switches", "Limit switch polarity inverted for all axes")
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Limit switch inversion failed: {e}")
            messagebox.showerror("Error", f"Failed to invert limit switches: {e}")
    
    def home_action(self):
        """Handle Home button click - invert home switch polarity"""
        if not self.main_app or not self.main_app.controller:
            messagebox.showerror("Error", "No controller connected")
            return
        
        try:
            # CN is a global command: CN n0,n1,n2,n3,n4
            # n1: Home switches (-1 = default, 1 = inverted)
            # Get current CN values
            cn0_response = self.main_app.controller.send_command("MG _CN0")
            cn1_response = self.main_app.controller.send_command("MG _CN1")
            
            cn0 = int(float(cn0_response.split(',')[0] if cn0_response else "-1"))
            cn1 = int(float(cn1_response.split(',')[0] if cn1_response else "-1"))
            
            # Toggle home switch polarity (n1)
            new_cn1 = -cn1 if cn1 != 0 else 1  # Toggle between -1 and 1
            
            # Apply new CN command with all parameters
            self.main_app.controller.send_command(f"CN {cn0},{new_cn1},-1,0,0")
            
            if self.main_app:
                self.main_app.append_test_log(f"Home switch polarity inverted (CN1: {cn1} -> {new_cn1})")
            
            messagebox.showinfo("Home Switches", "Home switch polarity inverted for all axes")
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Home switch inversion failed: {e}")
            messagebox.showerror("Error", f"Failed to invert home switches: {e}")
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, bg="yellow", font=("Arial", 9),
                           relief='solid', borderwidth=1, padx=5, pady=3)
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
    
    def show_wiring_info(self):
        """Show wiring information"""
        info_text = (
            "Limit and Home Switch Wiring:\n\n"
            "Negative Limit Switch: Connected to controller input\n"
            "Home Switch: Connected to controller input\n"
            "Positive Limit Switch: Connected to controller input\n\n"
            "Refer to controller documentation for specific pin assignments."
        )
        messagebox.showinfo("Wiring Information", info_text)
    
    def go_back(self):
        """Go back to previous step"""
        self.on_close()
    
    def go_next(self):
        """Proceed to next step"""
        self.on_close()
    
    def on_close(self):
        """Handle dialog close"""
        self.update_running = False
        if self.update_thread and self.update_thread.is_alive():
            time.sleep(0.2)
        
        if hasattr(self, 'dialog') and self.dialog.winfo_exists():
            self.dialog.destroy()

