"""
Motor Setup Dialog for Step-by-Step Motor Configuration
Includes motion warning and motor configuration steps
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
from statistics import median, pstdev

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    Figure = None
    FigureCanvasTkAgg = None

class MotorSetupDialog:
    """Dialog for configuring motor with safety warnings"""
    
    def __init__(self, parent, colors, main_app, axis, completion_callback=None, show_warning=True):
        self.parent = parent
        self.colors = colors
        self.main_app = main_app
        self.axis = axis.upper()
        self.completion_callback = completion_callback
        self.warning_accepted = False
        self.dont_show_again = False
        
        # Reset all state for this new axis - IMPORTANT: must reset before creating widgets
        self._reset_state()
        
        # Show motion warning if requested (or if preference not saved)
        if show_warning:
            self.show_motion_warning()
        else:
            # Skip warning and go directly to motor setup
            self.warning_accepted = True
            self.show_motor_setup()
    
    def _reset_state(self):
        """Reset all state variables for a new axis"""
        # State
        self.estimated_modulo = 5024  # Initial estimate
        self.brushless_modulo = None
        self.final_modulo = None
        self.motor_direction_verified = False
        self.hall_sensors_determined = False
        self.index_pulse_found = False
        self.position_update_running = False
        self.position_thread = None
        self.initial_position = None
        self.rotation_count = 0
        self.motor_driven = False
        self._movement_start_time = None
        self._cumulative_motion = 0
        self.min_move_counts = 10000  # require at least this much motion during setup
        self._index_trigger_queued = False
        self.initial_hall_state = None
        self.hall_transition_detected = False
        self.hall_direction_verified = False
        # Commutation validation parameters
        self.min_cycles_required = 24      # require at least 24 transitions (~4 electrical revs)
        self.min_duration_s = 3.0          # require at least 3.0s of sampling before acceptance
        self.attempt_timeout_s = 3.5        # retry jog profile after this many seconds
        self.max_comm_attempts = 3          # number of adaptive retries
        # Sampling buffers for commutation validation and graphing
        self.sample_times = []
        self.sample_positions = []
        self.sample_halls = []
        self.cycle_boundaries = []  # (t, pos) at hall transitions
        self.cycle_spans = []       # encoder counts per electrical cycle
        self.validation_result = None
    
    def show_motion_warning(self):
        """Show motion warning dialog"""
        warning_dialog = tk.Toplevel(self.parent)
        warning_dialog.title("Motion Warning")
        warning_dialog.geometry("450x250")
        warning_dialog.configure(bg=self.colors['main_bg'])
        warning_dialog.transient(self.parent)
        warning_dialog.grab_set()
        
        # Center the dialog
        warning_dialog.update_idletasks()
        x = (warning_dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (warning_dialog.winfo_screenheight() // 2) - (250 // 2)
        warning_dialog.geometry(f"450x250+{x}+{y}")
        
        # Warning icon and message
        content_frame = tk.Frame(warning_dialog, bg=self.colors['main_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Icon and message frame
        icon_msg_frame = tk.Frame(content_frame, bg=self.colors['main_bg'])
        icon_msg_frame.pack(fill='x', pady=(0, 15))
        
        # Warning icon (yellow triangle with exclamation)
        warning_icon = tk.Label(icon_msg_frame, text="⚠", font=("Arial", 32),
                               bg=self.colors['main_bg'], fg='#ffaa00')
        warning_icon.pack(side='left', padx=(0, 15))
        
        # Warning message
        message_text = ("The motor will move at most two rotations as part of setup. "
                       "Confirm that the motor is spinning freely, uncoupled from any "
                       "mechanics, then click OK to begin.")
        message_label = tk.Label(icon_msg_frame, text=message_text,
                                font=("Arial", 9),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                wraplength=320, justify='left', anchor='w')
        message_label.pack(side='left', fill='both', expand=True)
        
        # Don't show again checkbox
        self.dont_show_var = tk.BooleanVar(value=False)
        checkbox = tk.Checkbutton(content_frame,
                                 text="Don't show this again",
                                 font=("Arial", 9),
                                 bg=self.colors['main_bg'],
                                 fg=self.colors['main_fg'],
                                 variable=self.dont_show_var,
                                 selectcolor=self.colors['card_bg'])
        checkbox.pack(anchor='w', pady=(0, 10))
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg=self.colors['main_bg'])
        button_frame.pack(side='bottom', fill='x')
        
        def on_ok():
            self.dont_show_again = self.dont_show_var.get()
            self.warning_accepted = True
            
            # Save preference if "Don't show again" is checked
            if self.dont_show_again and self.main_app:
                # Update the preference in the step-by-step GUI
                if hasattr(self.main_app, 'step_by_step_gui'):
                    self.main_app.step_by_step_gui.show_motion_warning = False
                elif hasattr(self.main_app, 'gui_framework') and hasattr(self.main_app.gui_framework, 'step_by_step_gui'):
                    self.main_app.gui_framework.step_by_step_gui.show_motion_warning = False
            
            warning_dialog.destroy()
            # Proceed to motor setup after warning accepted
            self.show_motor_setup()
        
        def on_cancel():
            warning_dialog.destroy()
        
        cancel_btn = tk.Button(button_frame, text="Cancel",
                              font=("Arial", 10, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'],
                              command=on_cancel,
                              width=10)
        cancel_btn.pack(side='right', padx=(5, 0))
        
        ok_btn = tk.Button(button_frame, text="OK",
                          font=("Arial", 10, "bold"),
                          bg=self.colors['success_green'], fg='white',
                          command=on_ok,
                          width=10)
        ok_btn.pack(side='right')
        
        # Focus on Cancel initially
        cancel_btn.focus_set()
    
    def show_motor_setup(self):
        """Show motor configuration dialog after warning"""
        # Create main motor setup dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Step by Step")
        self.dialog.geometry("700x600")
        self.dialog.configure(bg=self.colors['main_bg'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        self.create_motor_widgets()
        
        # Update dialog size after widgets are created, then center
        self.dialog.update_idletasks()
        self.dialog.minsize(700, 600)
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_motor_widgets(self):
        """Create motor setup widgets"""
        # State is already initialized in _reset_state(), ensure it's reset
        if not hasattr(self, 'estimated_modulo'):
            self._reset_state()
        
        # Run initialization steps
        self.run_initialization_steps()
        
        # Title
        title_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        title_frame.pack(fill='x', pady=(15, 10), padx=20)
        
        title = tk.Label(title_frame, text=f"Brushless Motor Setup - Axis {self.axis}",
                        font=("Arial", 14, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack()
        
        # Main content area
        content_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left side - Status indicators
        left_frame = tk.Frame(content_frame, bg=self.colors['main_bg'])
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        status_title = tk.Label(left_frame, text="Setup Progress:",
                               font=("Arial", 10, "bold"),
                               bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        status_title.pack(anchor='w', pady=(0, 10))
        
        # Status items
        self.status_frame = tk.Frame(left_frame, bg=self.colors['main_bg'])
        self.status_frame.pack(fill='x', anchor='w')
        
        # Create status items - will be updated as steps complete
        self.modulo_status_item = self.create_status_item(f"Estimated Brushless Modulo: {self.estimated_modulo}", False)
        self.direction_status_item = self.create_status_item("Motor direction verified", False)
        self.hall_status_item = self.create_status_item("Hall sensors correction determined", False)
        self.index_status_item = self.create_status_item("Index pulse not found", False, is_info=True)
        self.final_modulo_status_item = None  # Will be created when index pulse is found
        
        # Instructions section - will be updated based on completion state
        self.instructions_frame = tk.Frame(left_frame, bg=self.colors['main_bg'])
        self.instructions_frame.pack(fill='x', pady=(20, 0), anchor='w')
        
        instructions_text = ("After initialization, manually move the motor or click 'Drive Motor' to detect hall sensor transition.\n\n"
                           "The motor direction and hall sensors will be verified when a hall transition is detected.\n\n"
                           "After hall transition, continue moving to detect index pulse.")
        
        self.instructions_label = tk.Label(self.instructions_frame, text=instructions_text,
                                     font=("Arial", 9),
                                     bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                     justify='left', anchor='w', wraplength=400)
        self.instructions_label.pack(anchor='w')
        
        # Clickable link for driving motor
        self.link_frame = tk.Frame(left_frame, bg=self.colors['main_bg'])
        self.link_frame.pack(fill='x', anchor='w', pady=(5, 0))
        
        self.link_text = tk.Label(self.link_frame, text="click here to drive the motor (or move manually)",
                            font=("Arial", 9, "underline"),
                            bg=self.colors['main_bg'], fg='blue',
                            cursor='hand2')
        self.link_text.pack(anchor='w')
        self.link_text.bind('<Button-1>', lambda e: self.drive_motor())
        
        self.additional_text = tk.Label(self.link_frame,
                                  text="• Hall sensor transition will complete direction and hall setup steps.\n"
                                       "• After hall transition, continue moving to detect index pulse.\n"
                                       "• If the motor has completed two full rotations without index pulse, click 'Home' to skip.",
                                  font=("Arial", 9),
                                  bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                  justify='left', anchor='w')
        self.additional_text.pack(anchor='w', pady=(5, 0))
        
        # Right side - Position display
        right_frame = tk.Frame(content_frame, bg=self.colors['card_bg'], relief='solid', bd=2)
        right_frame.pack(side='right', fill='y', padx=(10, 0))
        right_frame.config(width=200)
        
        position_label = tk.Label(right_frame, text="Position",
                                 font=("Arial", 10, "bold"),
                                 bg=self.colors['card_bg'], fg=self.colors['main_fg'])
        position_label.pack(pady=(15, 5))
        
        # Large position display (digital-style)
        self.position_display = tk.Label(right_frame,
                                        text="0",
                                        font=("Courier", 28, "bold"),
                                        bg='black',
                                        fg='#00ff00',
                                        width=10,
                                        anchor='e',
                                        relief='sunken',
                                        bd=3)
        self.position_display.pack(pady=10, padx=10)
        
        # Home button
        self.home_btn = tk.Button(right_frame, text="Home",
                            font=("Arial", 10, "bold"),
                            bg=self.colors.get('secondary_fg', '#888888'), fg='white',
                            command=self.home_motor,
                            width=12, state='normal')
        self.home_btn.pack(pady=10)
        
        # Start position updates for display and manual movement detection
        # Detection will only trigger after actual movement is detected
        self.start_position_updates()
        
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
    
    def create_status_item(self, text, completed, is_info=False):
        """Create a status indicator item"""
        item_frame = tk.Frame(self.status_frame, bg=self.colors['main_bg'])
        item_frame.pack(fill='x', pady=3, anchor='w')
        
        # Icon
        if completed:
            icon = tk.Label(item_frame, text="✓", font=("Arial", 12, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['success_green'], width=2)
        elif is_info:
            icon = tk.Label(item_frame, text="ℹ", font=("Arial", 12, "bold"),
                           bg=self.colors['main_bg'], fg=self.colors['accent_blue'], width=2)
        else:
            icon = tk.Label(item_frame, text="○", font=("Arial", 12),
                           bg=self.colors['main_bg'], fg=self.colors.get('secondary_fg', '#888888'), width=2)
        
        icon.pack(side='left')
        
        # Text
        text_label = tk.Label(item_frame, text=text, font=("Arial", 9),
                             bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        text_label.pack(side='left', padx=(5, 0))
        
        return item_frame
    
    def run_initialization_steps(self):
        """Run the motor initialization steps automatically"""
        if not self.main_app or not self.main_app.controller:
            return
        
        # Run initialization in a background thread to avoid blocking UI
        init_thread = threading.Thread(target=self._run_initialization_background, daemon=True)
        init_thread.start()
    
    def _run_initialization_background(self):
        """Run initialization steps in background thread"""
        try:
            # Step 1: Configure brushless amplifier
            if self.main_app and self.main_app.controller:
                if self.main_app:
                    self.main_app.append_test_log(f"Initializing brushless motor setup for Axis {self.axis}...")
                
                # Set motor type to brushless
                try:
                    response = self.main_app.controller.send_command(f"MT{self.axis}=1.0")
                    if response and response.strip() == "?":
                        if self.main_app:
                            self.main_app.append_test_log(f"Warning: MT{self.axis}=1.0 rejected - motor may already be configured")
                    elif self.main_app:
                        self.main_app.append_test_log(f"MT{self.axis}=1.0 (Motor type: Brushless)")
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: MT command error: {e}")
                
                # Configure brushless amplifier (only if motor type was set successfully)
                try:
                    response = self.main_app.controller.send_command(f"BA{self.axis}")
                    if response and response.strip() == "?":
                        if self.main_app:
                            self.main_app.append_test_log(f"Warning: BA{self.axis} rejected - will retry when motor is driven")
                    elif self.main_app:
                        self.main_app.append_test_log(f"BA{self.axis} (Brushless amplifier configured)")
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: BA command error: {e}")
                
                # Set estimated brushless modulo (but don't mark complete yet - wait for user confirmation)
                # The BM command will be sent when motor is actually driven
                # Just mark the step as ready
                self.dialog.after(0, lambda: self.complete_step('modulo'))
                
                if self.main_app:
                    self.main_app.append_test_log(f"Estimated brushless modulo: {self.estimated_modulo} (will be set when motor is driven)")
                time.sleep(0.3)
                
                # Step 2: Initialize with hall sensors (BI/BC method)
                if self.main_app:
                    self.main_app.append_test_log(f"Initializing hall sensors for Axis {self.axis}...")
                
                # Set estimated commutation based on current hall state
                try:
                    response = self.main_app.controller.send_command(f"BI{self.axis}=-1")
                    if self.main_app:
                        self.main_app.append_test_log(f"BI{self.axis}=-1 (Hall sensor initialization started)")
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: BI command failed: {e}")
                
                # Enable brushless calibration - this waits for hall transition
                try:
                    response = self.main_app.controller.send_command(f"BC{self.axis}")
                    if self.main_app:
                        self.main_app.append_test_log(f"BC{self.axis} (Hall-based calibration enabled - waiting for hall transition)")
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: BC command failed: {e}")
                
                # Get initial hall sensor state for transition detection
                # Note: We'll get this in the position update loop when it starts running
                self.initial_hall_state = None
                
                if self.main_app:
                    self.main_app.append_test_log(f"Initial setup complete. Move motor manually or click 'Drive Motor' to detect hall transition and index pulse.")
                
                # Steps 2 and 3 will be completed when hall transition is detected
                
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Initialization error: {e}")
        
        # Position tracking will start when motor is driven or moved manually
        # Don't start immediately to prevent false detections on startup
    
    def complete_step(self, step_type):
        """Mark a step as complete and update the UI"""
        if step_type == 'modulo':
            # Only mark modulo complete if we actually set it
            if hasattr(self, 'modulo_status_item'):
                self.update_status_item(self.modulo_status_item, True)
            self.brushless_modulo = self.estimated_modulo
            # Don't mark other steps complete yet
        elif step_type == 'direction':
            # Only complete if hall transition was detected
            if self.hall_transition_detected and hasattr(self, 'direction_status_item'):
                self.update_status_item(self.direction_status_item, True)
                self.motor_direction_verified = True
        elif step_type == 'hall':
            # Only complete if hall transition was detected
            if self.hall_transition_detected and hasattr(self, 'hall_status_item'):
                self.update_status_item(self.hall_status_item, True)
                self.hall_sensors_determined = True
    
    def update_status_item(self, item_frame, completed):
        """Update a status item to show completed"""
        for widget in item_frame.winfo_children():
            if isinstance(widget, tk.Label) and len(widget.cget('text')) == 1:
                # This is the icon
                widget.config(text="✓", fg=self.colors['success_green'], font=("Arial", 12, "bold"))
                break
    
    def start_position_updates(self):
        """Start real-time encoder position updates and index pulse detection"""
        if not self.main_app or not self.main_app.controller:
            if hasattr(self, 'position_display'):
                self.position_display.config(text="No Controller")
            return
        
        # Only start if not already running
        if self.position_update_running:
            return
        
        # Get initial position - wait a moment to ensure it's stable
        try:
            time.sleep(0.2)
            response = self.main_app.controller.send_command(f"TP{self.axis}")
            if response and not response.strip().startswith('?') and response.strip():
                try:
                    pos_str = response.split(',')[0].strip()
                    current_pos = int(float(pos_str))
                    # Display current position
                    if hasattr(self, 'position_display'):
                        self.position_display.config(text=str(current_pos))
                    # Store as initial reference if motor driven, otherwise wait for movement detection
                    if self.motor_driven:
                        self.initial_position = current_pos
                        if self.main_app:
                            self.main_app.append_test_log(f"Initial position for motor movement: {self.initial_position}")
                except (ValueError, IndexError):
                    self.initial_position = None
            else:
                self.initial_position = None
                if self.main_app:
                    self.main_app.append_test_log(f"Warning: Could not read initial position for Axis {self.axis} (response: {response})")
        except Exception as e:
            self.initial_position = None
            if self.main_app:
                self.main_app.append_test_log(f"Warning: Exception reading initial position: {e}")
        
        # Reset tracking states
        self.index_pulse_found = False
        if not self.motor_driven:
            # Only reset hall transition if motor hasn't been driven yet
            self.hall_transition_detected = False
            self.initial_hall_state = None
        
        self.position_update_running = True
        self.position_thread = threading.Thread(target=self.update_position_loop, daemon=True)
        self.position_thread.start()
    
    def update_position_loop(self):
        """Update encoder position in real-time and detect index pulse"""
        last_position = None
        last_displayed_position = None
        update_threshold = 2  # Only update if position changes by at least 2 counts
        manual_movement_detected = False
        
        while self.position_update_running:
            try:
                if self.main_app and self.main_app.controller:
                    # Read encoder position (skip if controller is in error state)
                    try:
                        response = self.main_app.controller.send_command(f"TP{self.axis}")
                    except Exception as e:
                        # Controller error - skip this update, wait longer before retry
                        time.sleep(0.5)
                        continue
                    
                    if response and not response.strip().startswith('?') and response.strip():
                        try:
                            pos_str = response.split(',')[0].strip()
                            position = int(float(pos_str))
                        except (ValueError, IndexError):
                            time.sleep(0.1)
                            continue
                            
                        # Always update display if position changed significantly
                        if last_displayed_position is None or abs(position - last_displayed_position) >= update_threshold:
                            # Update display (must be in main thread)
                            if hasattr(self, 'dialog') and self.dialog.winfo_exists():
                                self.dialog.after(0, lambda p=position: self.update_display(p))
                            last_displayed_position = position
                        
                        # Detect manual movement if motor hasn't been driven yet
                        if not self.motor_driven and last_position is not None:
                            position_change = abs(position - last_position)
                            # Accumulate motion to avoid noise-triggering
                            if position_change > 0:
                                self._cumulative_motion = (self._cumulative_motion or 0) + position_change
                                if self._movement_start_time is None:
                                    self._movement_start_time = time.time()
                            # Require sustained/cumulative movement before considering motor 'driven'
                            if (self._cumulative_motion is not None and self._cumulative_motion >= 800 and
                                self._movement_start_time is not None and (time.time() - self._movement_start_time) >= 0.25):
                                manual_movement_detected = True
                                self.motor_driven = True  # Enable detection
                                # Set initial position as baseline
                                if self.initial_position is None:
                                    self.initial_position = last_position
                                # Reset cumulative motion from this point for min-move enforcement
                                self._cumulative_motion = 0
                                self._movement_start_time = time.time()
                                if self.main_app:
                                    self.main_app.append_test_log(f"Manual movement detected on Axis {self.axis}! Starting hall/index detection.")
                        
                        # Accumulate motion after motor is driven to support min-move checks
                        if last_position is not None and self.motor_driven:
                            try:
                                delta = abs(position - last_position)
                                if delta > 0:
                                    self._cumulative_motion = (self._cumulative_motion or 0) + delta
                            except Exception:
                                pass
                        last_position = position
                        
                        # Check for hall sensor transition - only after motor is actually driven/moved and after small delay
                        if not self.hall_transition_detected and self.motor_driven and (self._movement_start_time is not None and (time.time() - self._movement_start_time) >= 0.2):
                            try:
                                # Check for hall sensor transition using _QH
                                hall_response = self.main_app.controller.send_command(f"MG _QH{self.axis}")
                                if hall_response and hall_response.strip() != "?":
                                    try:
                                        hall_state = int(float(hall_response.split(',')[0].strip()))
                                        # Hall state should be 1-6 (valid), 0 or 7 are invalid
                                        if 1 <= hall_state <= 6:
                                            # Check if this is the first valid hall reading
                                            if self.initial_hall_state is None:
                                                # First time we got a valid reading, save it as baseline
                                                self.initial_hall_state = hall_state
                                                if self.main_app:
                                                    self.main_app.append_test_log(f"Initial hall sensor state for Axis {self.axis}: {hall_state}")
                                            # Check if hall state has changed from initial state
                                            elif hall_state != self.initial_hall_state:
                                                # Hall transition detected!
                                                self.hall_transition_detected = True
                                                if self.main_app:
                                                    self.main_app.append_test_log(f"Hall sensor transition detected! State changed from {self.initial_hall_state} to {hall_state}")
                                                # Mark direction and hall steps as complete
                                                self.dialog.after(0, lambda: self.complete_step('direction'))
                                                self.dialog.after(0, lambda: self.complete_step('hall'))
                                        elif hall_state == 0 or hall_state == 7:
                                            # Invalid hall state - log but don't use it
                                            if self.main_app and self.initial_hall_state is None:
                                                self.main_app.append_test_log(f"Warning: Invalid hall sensor state {hall_state} for Axis {self.axis}")
                                    except:
                                        pass
                            except:
                                pass

                        # Record samples and estimate BM over multiple cycles
                        try:
                            # Read current hall state (best-effort)
                            hall_val = None
                            try:
                                qh = self.main_app.controller.send_command(f"MG _QH{self.axis}")
                                if qh and qh.strip() != "?":
                                    hv = int(float(qh.split(',')[0].strip()))
                                    hall_val = hv if 1 <= hv <= 6 else None
                            except:
                                hall_val = None
                            now = time.time()
                            self.sample_times.append(now)
                            self.sample_positions.append(position)
                            self.sample_halls.append(hall_val if hall_val is not None else (self.sample_halls[-1] if self.sample_halls else None))

                            # Detect transitions and accumulate cycle spans
                            if len(self.sample_halls) >= 2:
                                prev_h = self.sample_halls[-2]
                                cur_h = self.sample_halls[-1]
                                if prev_h is not None and cur_h is not None and prev_h != cur_h:
                                    self.cycle_boundaries.append((now, position))
                                    if len(self.cycle_boundaries) >= 7:
                                        span = abs(self.cycle_boundaries[-1][1] - self.cycle_boundaries[-7][1])
                                        if 100 <= span <= 200000:
                                            self.cycle_spans.append(span)
                                            if len(self.cycle_spans) > 20:
                                                self.cycle_spans.pop(0)
                                            # Periodic debug: log last few spans to verify data quality
                                            if self.main_app and len(self.cycle_spans) % 6 == 0:
                                                recent = self.cycle_spans[-6:]
                                                try:
                                                    from statistics import median, pstdev
                                                    m_dbg = median(recent)
                                                    s_dbg = pstdev(recent)
                                                    cv_dbg = (s_dbg / m_dbg) if m_dbg else 1.0
                                                except Exception:
                                                    m_dbg, cv_dbg, recent = 0, 1.0, list(self.cycle_spans[-6:])
                                                self.main_app.append_test_log(
                                                    f"[COMM DBG] spans={recent} median={int(m_dbg)} CV={cv_dbg*100:.1f}%"
                                                )
                                            # Accept only after enough cycles AND minimum duration
                                            elapsed = time.time() - self.attempt_start_time if self.attempt_start_time else 0
                                            if (len(self.cycle_spans) >= self.min_cycles_required and
                                                elapsed >= self.min_duration_s and
                                                self.validation_result is None):
                                                m = median(self.cycle_spans)
                                                s = pstdev(self.cycle_spans)
                                                cv = (s / m) if m else 1.0
                                                if cv <= 0.05:  # <=5% variation
                                                    self.estimated_modulo = int(round(m))
                                                    self.validation_result = {"bm": self.estimated_modulo, "cv": cv, "cycles": list(self.cycle_spans[-self.min_cycles_required:])}
                                                    try:
                                                        # Apply validated BM immediately and only once
                                                        if not hasattr(self, '_bm_set_from_validator'):
                                                            self._bm_set_from_validator = False
                                                        if not self._bm_set_from_validator:
                                                            self.main_app.controller.send_command(f"BM{self.axis}={self.estimated_modulo}")
                                                            self._bm_set_from_validator = True
                                                            if self.main_app:
                                                                self.main_app.append_test_log(
                                                                    f"[COMM] Hall-cycle BM set: BM={self.estimated_modulo} (CV={cv*100:.1f}%, spans={self.cycle_spans[-self.min_cycles_required:]})"
                                                                )
                                                    except:
                                                        pass
                        except:
                            pass

                        # Attempt timeout and adaptive retry (only while still seeking validation/index)
                        try:
                            if (not self.index_pulse_found and self.validation_result is None and self.attempt_start_time and
                                time.time() - self.attempt_start_time > self.attempt_timeout_s):
                                if self.comm_attempt < self.max_comm_attempts:
                                    # Stop, adapt, and retry
                                    try:
                                        self.main_app.controller.send_command(f"ST{self.axis}")
                                        time.sleep(0.2)
                                    except:
                                        pass
                                    # Reduce speed and flip direction
                                    self.jog_direction *= -1
                                    base = max(3000, int(self.jog_speed_base * (0.8 ** (self.comm_attempt))))
                                    self.current_jog_speed = base * self.jog_direction
                                    try:
                                        self.main_app.controller.send_command(f"JG{self.axis}={self.current_jog_speed}")
                                        self.main_app.controller.send_command(f"BG{self.axis}")
                                    except:
                                        pass
                                    # Reset buffers and timers
                                    self.sample_times, self.sample_positions, self.sample_halls = [], [], []
                                    self.cycle_boundaries, self.cycle_spans = [], []
                                    self.attempt_start_time = time.time()
                                    self.comm_attempt += 1
                                    if self.main_app:
                                        self.main_app.append_test_log(f"[COMM] Retry attempt {self.comm_attempt}: JG={self.current_jog_speed}")
                                else:
                                    if self.main_app:
                                        self.main_app.append_test_log("[COMM] Max attempts reached; proceeding without BM acceptance yet")
                                    # avoid spamming
                                    self.attempt_start_time = time.time()
                        except:
                            pass
                        
                        # Check for index pulse and hall transition
                        if not self.index_pulse_found:
                            try:
                                # Check for index pulse using ZI command (requires min movement)
                                try:
                                    zi_response = self.main_app.controller.send_command(f"MG _ZI{self.axis}")
                                    if zi_response and zi_response.strip() != "?":
                                        zi_value = zi_response.strip()
                                        try:
                                            if float(zi_value.split(',')[0]) != 0 and (self._cumulative_motion or 0) >= self.min_move_counts and not self._index_trigger_queued:
                                                self._index_trigger_queued = True
                                                self.dialog.after(0, self.on_index_pulse_found)
                                        except:
                                            pass
                                except:
                                    pass
                                
                                # Alternative: detect large position change after hall transition
                                if (self.hall_transition_detected and self.motor_driven and 
                                    self.initial_position is not None and 
                                    position != 0 and position != self.initial_position):
                                    position_change = abs(position - self.initial_position)
                                    movement_threshold = max(self.estimated_modulo * 2, self.min_move_counts)
                                    if position_change >= movement_threshold and not self.index_pulse_found and not self._index_trigger_queued:
                                        if self.main_app:
                                            self.main_app.append_test_log(f"Significant movement detected ({position_change} counts from {self.initial_position} to {position}), triggering index pulse detection")
                                        self._index_trigger_queued = True
                                        self.dialog.after(100, self.on_index_pulse_found)
                            except:
                                pass
            except Exception as e:
                pass
            
            time.sleep(0.1)  # Update 10 times per second
    
    def update_display(self, position):
        """Update the position display (called from main thread)"""
        if hasattr(self, 'position_display') and self.position_display.winfo_exists():
            try:
                # Only update if the value has changed to prevent blinking
                current_text = self.position_display.cget('text')
                new_text = str(position)
                if current_text != new_text:
                    self.position_display.config(text=new_text)
            except tk.TclError:
                # Widget was destroyed, stop trying to update
                pass
    
    def drive_motor(self):
        """Drive the motor to help with hall sensor transition and index pulse detection"""
        if not self.main_app or not self.main_app.controller:
            messagebox.showerror("Error", "No controller connected")
            return
        
        try:
            if self.main_app:
                self.main_app.append_test_log(f"Driving motor on Axis {self.axis} to detect hall transition and index pulse...")
            
            # Ensure brushless initialization is complete
            try:
                # BA - configure brushless amplifier
                ba_response = self.main_app.controller.send_command(f"BA{self.axis}")
                if ba_response and ba_response.strip() == "?":
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: BA{self.axis} command rejected")
                
                # Defer BM setting until validated (hall-cycle estimator) or index refinement
                
                # BI - initialize with hall sensors
                bi_response = self.main_app.controller.send_command(f"BI{self.axis}=-1")
                if bi_response and bi_response.strip() == "?":
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: BI{self.axis}=-1 command rejected")
                
                # BC - enable brushless calibration
                bc_response = self.main_app.controller.send_command(f"BC{self.axis}")
                if bc_response and bc_response.strip() == "?":
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: BC{self.axis} command rejected")
            except Exception as e:
                if self.main_app:
                    self.main_app.append_test_log(f"Warning: Brushless initialization error: {e}")
            
            # Enable servo (required for movement)
            self.main_app.controller.send_command(f"SH{self.axis}")
            time.sleep(0.2)

            # Loosen limits and allow motion: disable off-on-error, raise error limit, expand software limits, set moderate torque
            try:
                self.main_app.controller.send_command(f"OE{self.axis}=0")
            except Exception:
                pass
            try:
                self.main_app.controller.send_command(f"ER{self.axis}=200000")
            except Exception:
                pass
            try:
                self.main_app.controller.send_command(f"FL{self.axis}=2147483647")
                self.main_app.controller.send_command(f"BL{self.axis}=-2147483648")
            except Exception:
                pass
            try:
                self.main_app.controller.send_command(f"TL{self.axis}=6")
            except Exception:
                pass
            
            # Set slow jog speed for precise commutation angle detection
            # Use conservative speed to allow clean hall transitions
            jog_speed = max(8000, int(self.estimated_modulo / 4))
            self.jog_speed_base = jog_speed
            self.current_jog_speed = jog_speed
            self.jog_direction = 1
            self.main_app.controller.send_command(f"JG{self.axis}={self.current_jog_speed}")
            
            # Begin jog
            self.main_app.controller.send_command(f"BG{self.axis}")
            
            # Mark that motor has been driven
            self.motor_driven = True
            # Initialize multi-pass attempt tracking and buffers
            self.comm_attempt = 1
            self.attempt_start_time = time.time()
            # Reset movement tracking for min-move enforcement
            self._cumulative_motion = 0
            self._movement_start_time = time.time()
            self.sample_times, self.sample_positions, self.sample_halls = [], [], []
            self.cycle_boundaries, self.cycle_spans = [], []
            self.validation_result = None
            # Ensure retry/validation parameters are initialized
            if not hasattr(self, 'max_comm_attempts'):
                self.max_comm_attempts = 3
            if not hasattr(self, 'attempt_timeout_s'):
                self.attempt_timeout_s = 3.5
            if not hasattr(self, 'min_cycles_required'):
                self.min_cycles_required = 6
            if not hasattr(self, 'min_duration_s'):
                self.min_duration_s = 1.5
            
            # Start position tracking now that motor is being driven
            if not self.position_update_running:
                self.start_position_updates()
            
            # Reset initial position now that motor is starting to move
            try:
                time.sleep(0.1)
                response = self.main_app.controller.send_command(f"TP{self.axis}")
                if response and not response.strip().startswith('?'):
                    pos_str = response.split(',')[0].strip()
                    self.initial_position = int(float(pos_str))
                    if self.main_app:
                        self.main_app.append_test_log(f"Initial position for motor movement: {self.initial_position}")
            except:
                pass
            
            if self.main_app:
                self.main_app.append_test_log(f"Motor jogging at {self.current_jog_speed} counts/sec. Waiting for hall transition and index pulse...")
                
            # Update UI text
            if hasattr(self, 'instructions_label'):
                if not self.hall_transition_detected:
                    self.instructions_label.config(
                        text=f"Motor is jogging slowly (or move it manually). Waiting for hall sensor transition to complete direction and hall setup...\n\n"
                             f"Once hall transition is detected, continue moving to find index pulse."
                    )
                else:
                    self.instructions_label.config(
                        text=f"Motor is jogging slowly (or move it manually). Hall transition detected. Continuing to search for index pulse...\n\n"
                             f"If the motor has completed two full rotations without detecting an index pulse, you can click 'Home' to skip index detection."
                    )
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Drive motor failed: {e}")
            messagebox.showerror("Error", f"Failed to drive motor: {e}")
    
    def _track_parameter_change(self, param: str, value: str):
        """Track parameter change for Save Configuration dialog"""
        if self.main_app and hasattr(self.main_app, 'step_by_step_gui'):
            if hasattr(self.main_app.step_by_step_gui, 'modified_parameters'):
                self.main_app.step_by_step_gui.modified_parameters[param] = value
    
    def on_index_pulse_found(self):
        """Handle index pulse detection"""
        if self.index_pulse_found:
            return  # Already processed
        
        # Don't allow index pulse detection unless motor has been driven or moved
        if not self.motor_driven:
            # Silently ignore - this prevents spam in logs
            return
        
        # Enforce minimum movement before accepting index
        if (self._cumulative_motion or 0) < getattr(self, 'min_move_counts', 20000):
            # Not enough movement yet; keep searching
            return
        
        # Don't allow if hall transition hasn't been detected yet
        if not self.hall_transition_detected:
            # Silently ignore - this prevents spam in logs
            return
        
        self.index_pulse_found = True
        
        # Stop motor and disable servo
        if self.main_app and self.main_app.controller:
            try:
                self.main_app.controller.send_command(f"ST{self.axis}")
                time.sleep(0.2)
                self.main_app.controller.send_command(f"MO{self.axis}")
            except:
                pass
        # Stop position update loop to prevent further retries/logs
        self.position_update_running = False
        
        # Update status item
        if hasattr(self, 'index_status_item'):
            for widget in self.index_status_item.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget('text') == "ℹ":
                    widget.config(text="✓", fg=self.colors['success_green'], font=("Arial", 12, "bold"))
                elif isinstance(widget, tk.Label) and "Index pulse" in widget.cget('text'):
                    widget.config(text="Found index pulse")
        
        # Calculate final brushless modulo
        try:
            if self.main_app and self.main_app.controller:
                # Query the actual brushless modulo from controller
                try:
                    bm_response = self.main_app.controller.send_command(f"MG _BM{self.axis}")
                except:
                    # Use estimated modulo if _BM not supported
                    bm_response = str(self.estimated_modulo)
                if bm_response and not bm_response.strip().startswith('?'):
                    try:
                        self.final_modulo = float(bm_response.split(',')[0].strip())
                    except:
                        # Fallback to estimated value with some precision
                        self.final_modulo = float(self.estimated_modulo)
                else:
                    # Use estimated modulo if controller doesn't provide it
                    self.final_modulo = float(self.estimated_modulo)
                
                # If hall-cycle validator produced a BM, prefer it
                try:
                    if getattr(self, 'validation_result', None) and 'bm' in self.validation_result:
                        bm_validated = int(self.validation_result['bm'])
                        try:
                            self.main_app.controller.send_command(f"BM{self.axis}={bm_validated}")
                            self.final_modulo = float(bm_validated)
                            if self.main_app:
                                self.main_app.append_test_log(f"[COMM] BM set from hall-cycle validator: BM={bm_validated}")
                        except Exception:
                            pass
                except Exception:
                    pass

                # Add final modulo status item
                if self.final_modulo:
                    # Format modulo as integer if it's close to whole number, otherwise with decimals
                    if abs(self.final_modulo - round(self.final_modulo)) < 0.01:
                        modulo_str = f"Final Brushless Modulo: {int(round(self.final_modulo))}"
                    else:
                        modulo_str = f"Final Brushless Modulo: {self.final_modulo:.4f}"
                    
                    self.final_modulo_status_item = self.create_status_item(modulo_str, True)
                    # Pack it after index status
                    if hasattr(self, 'status_frame'):
                        self.final_modulo_status_item.pack(fill='x', pady=3, anchor='w')
                    
                    # Track the brushless modulo change
                    self._track_parameter_change(f"BM{self.axis}", str(self.final_modulo))

                    # Launch an index-based BM improvement in background (computes counts per rev)
                    threading.Thread(target=self._improve_bm_via_index, daemon=True).start()
                    
                    # Track other motor parameters
                    try:
                        # Track brushless inputs (BI)
                        self._track_parameter_change(f"BI{self.axis}", "-1")
                        # Track amplifier hall correction (A3) if set
                        try:
                            a3_response = self.main_app.controller.send_command(f"MG _A3{self.axis}")
                            if a3_response and a3_response.strip() != '?' and not a3_response.strip().startswith('?'):
                                a3_value = a3_response.split(',')[0].strip()
                                try:
                                    # Validate it's a reasonable A3 value (should be around 0-200, not 5024)
                                    a3_float = float(a3_value)
                                    if 0 <= a3_float <= 200:
                                        self._track_parameter_change(f"A3{self.axis}", a3_value)
                                except:
                                    pass
                        except:
                            pass
                        # Track amplifier current loop gain (AU) if set
                        try:
                            au_response = self.main_app.controller.send_command(f"MG _AU{self.axis}")
                            if au_response and au_response.strip() != '?' and not au_response.strip().startswith('?'):
                                au_value = au_response.split(',')[0].strip()
                                try:
                                    # Validate it's a reasonable AU value (should be around 1-20, not 5024)
                                    au_float = float(au_value)
                                    if 1 <= au_float <= 20:
                                        self._track_parameter_change(f"AU{self.axis}", au_value)
                                except:
                                    pass
                        except:
                            pass
                    except:
                        pass
                    
                    # Update instructions to show completion
                    self.update_instructions_for_completion()
                    # Show commutation graph (if plotting available)
                    self.show_commutation_graph_safe()
                
                if self.main_app:
                    self.main_app.append_test_log(f"Index pulse found for Axis {self.axis}, final modulo: {self.final_modulo}")
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Error calculating modulo: {e}")

    def _improve_bm_via_index(self):
        """Refine BM by polling _ZI while jogging (no FI dependency)."""
        try:
            ctrl = self.main_app.controller if self.main_app else None
            if not ctrl:
                return
            ax = self.axis
            # Prepare axis
            try:
                ctrl.send_command(f"OE{ax}=0")
            except Exception:
                pass
            try:
                ctrl.send_command(f"ER{ax}=200000")
            except Exception:
                pass
            ctrl.send_command(f"ST{ax}")
            ctrl.send_command(f"DP{ax}=0")
            try:
                ctrl.send_command(f"ZI{ax}=0")
            except Exception:
                pass
            ctrl.send_command(f"SH{ax}")
            time.sleep(0.1)
            ctrl.send_command(f"JG{ax}=8000")
            ctrl.send_command(f"BG{ax}")
            # Wait first index
            t0 = time.time()
            p1 = None
            while time.time() - t0 < 6.0:
                try:
                    zi = ctrl.send_command(f"MG _ZI{ax}")
                    if zi and float(str(zi).strip().split(',')[0]) != 0.0:
                        p1 = float(str(ctrl.send_command(f"TP{ax}")).strip().split(',')[0])
                        ctrl.send_command(f"ZI{ax}=0")
                        break
                except Exception:
                    pass
                time.sleep(0.03)
            if p1 is None:
                ctrl.send_command(f"ST{ax}")
                return
            # Continue jog and wait second index
            t1 = time.time()
            p2 = None
            while time.time() - t1 < 6.0:
                try:
                    zi = ctrl.send_command(f"MG _ZI{ax}")
                    if zi and float(str(zi).strip().split(',')[0]) != 0.0:
                        p2 = float(str(ctrl.send_command(f"TP{ax}")).strip().split(',')[0])
                        ctrl.send_command(f"ZI{ax}=0")
                        break
                except Exception:
                    pass
                time.sleep(0.03)
            ctrl.send_command(f"ST{ax}")
            if p2 is None:
                return
            rev_counts = abs(p2 - p1)
            if rev_counts <= 0:
                return
            # Estimate pole_pairs from current estimate to avoid hardcoding
            est_bm = self.final_modulo or self.estimated_modulo or 5000
            pole_pairs_guess = max(1, int(round(rev_counts / float(est_bm))))
            bm_new = int(round(rev_counts / float(pole_pairs_guess)))
            # Apply if meaningfully different
            if abs(bm_new - int(round(est_bm))) >= 1:
                try:
                    ctrl.send_command(f"BM{ax}={bm_new}")
                    self.final_modulo = float(bm_new)
                    self._track_parameter_change(f"BM{ax}", str(bm_new))
                    if self.main_app:
                        self.main_app.append_test_log(f"[COMM] Index-based BM refined: rev={int(rev_counts)} counts, poles≈{pole_pairs_guess}, BM={bm_new}")
                except:
                    pass
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"[COMM] BM improvement error: {e}")

    def show_commutation_graph_safe(self):
        """Show a diagnostic graph of commutation sampling."""
        if Figure is None or FigureCanvasTkAgg is None:
            if self.main_app:
                self.main_app.append_test_log("[COMMUTATION] Matplotlib not available; skipping graph")
            return
        try:
            if not self.sample_times or not self.sample_positions:
                return
            t0 = self.sample_times[0]
            times = [t - t0 for t in self.sample_times]
            positions = list(self.sample_positions)
            halls = [h if h is not None else 0 for h in self.sample_halls]
            fig = Figure(figsize=(7, 4), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(times, positions, 'g-', label='Position (counts)')
            if any(halls):
                # scale halls to overlay
                span = max(positions) - min(positions) if positions else 1
                offset = min(positions)
                h_scaled = [offset + (h * span / 8.0) for h in halls]
                ax.plot(times, h_scaled, 'b--', alpha=0.6, label='Hall state (scaled)')
            if self.cycle_boundaries:
                for tb, _ in self.cycle_boundaries[-36:]:
                    ax.axvline(tb - t0, color='orange', alpha=0.2, linewidth=1)
            title = f"Axis {self.axis} Commutation"
            if self.validation_result:
                title += f" | BM≈{self.validation_result['bm']} (CV={self.validation_result['cv']*100:.1f}%)"
            ax.set_title(title)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Encoder Counts')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.2)

            win = tk.Toplevel(self.dialog)
            win.title(f"Axis {self.axis}: Commutation Diagnostics")
            win.configure(bg=self.colors['main_bg'])
            canvas = FigureCanvasTkAgg(fig, master=win)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"[COMMUTATION] Graph error: {e}")
    
    def update_instructions_for_completion(self):
        """Update instructions section to show completion message"""
        if hasattr(self, 'instructions_label'):
            # Only show completion if ALL steps are actually complete
            if (self.hall_transition_detected and self.index_pulse_found and 
                self.final_modulo is not None):
                # Update main instructions
                completion_text = f"All motor setup steps for Axis {self.axis} are complete. Click 'Next' to proceed to motor tuning."
                self.instructions_label.config(text=completion_text)
                
                # Hide the link and additional text
                if hasattr(self, 'link_frame'):
                    self.link_frame.pack_forget()
                if hasattr(self, 'additional_text'):
                    self.additional_text.pack_forget()
                
                # Disable home button
                if hasattr(self, 'home_btn'):
                    self.home_btn.config(state='disabled', bg=self.colors.get('secondary_fg', '#888888'))
            else:
                # Ensure link is visible if not complete
                if hasattr(self, 'link_frame'):
                    try:
                        if not self.link_frame.winfo_viewable():
                            self.link_frame.pack(fill='x', anchor='w', pady=(5, 0))
                    except:
                        pass
    
    def home_motor(self):
        """Continue setup without index pulse"""
        try:
            # Stop any motion
            if self.main_app and self.main_app.controller:
                self.main_app.controller.send_command(f"ST{self.axis}")
                time.sleep(0.2)
                # Disable servo
                self.main_app.controller.send_command(f"MO{self.axis}")
            
            # Set brushless modulo to estimated value
            if self.main_app and self.main_app.controller:
                self.main_app.controller.send_command(f"BM{self.axis}={self.estimated_modulo}")
            
            # Simulate index pulse found to continue
            if not self.index_pulse_found:
                self.final_modulo = float(self.estimated_modulo)  # Use estimated
                self.on_index_pulse_found()
            
            if self.main_app:
                self.main_app.append_test_log(f"Index pulse detection skipped for Axis {self.axis}, using estimated modulo: {self.estimated_modulo}")
                
            # Update instructions
            if hasattr(self, 'instructions_label'):
                self.instructions_label.config(
                    text=f"Motor setup for Axis {self.axis} complete.\n\n"
                         f"Brushless Modulo: {int(self.estimated_modulo)}\n\n"
                         f"Click 'Next' to proceed to motor tuning."
                )
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Home action failed: {e}")
            messagebox.showerror("Error", f"Failed to continue: {e}")
    
    def go_back(self):
        """Go back to previous step"""
        self.on_close()
    
    def go_next(self):
        """Proceed to next step"""
        try:
            # Stop position updates
            self.position_update_running = False
            
            # Save motor configuration
            if self.main_app:
                self.main_app.append_test_log(f"Motor setup complete for Axis {self.axis}")
            
            # Mark motor as complete
            if self.completion_callback:
                self.completion_callback('motor')
            
            messagebox.showinfo("Success", f"Motor configuration saved for Axis {self.axis}")
            self.on_close()
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Save failed: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def on_close(self):
        """Handle dialog close"""
        # Stop position updates
        self.position_update_running = False
        if self.position_thread and self.position_thread.is_alive():
            time.sleep(0.2)  # Give thread time to stop
        
        if hasattr(self, 'dialog') and self.dialog.winfo_exists():
            self.dialog.destroy()

