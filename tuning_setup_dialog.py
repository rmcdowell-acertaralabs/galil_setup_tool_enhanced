"""
Tuning Setup Dialog for Step-by-Step Motor Configuration
Includes motion warning and motor tuning interface

VERSION: 2.0 - REAL AUTO-TUNING WITH MEASUREMENT AND CALCULATION
Updated: Added actual motor response measurement and PID calculation
"""

# VERSION TRACKER - Change this to force reload detection
TUNING_DIALOG_VERSION = "2.0-REAL-TUNING"

import tkinter as tk
from tkinter import messagebox
import threading
import time
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class TuningSetupDialog:
    """Dialog for configuring motor tuning with safety warnings"""
    
    def __init__(self, parent, colors, main_app, axis, completion_callback=None, show_warning=True):
        self.parent = parent
        self.colors = colors
        self.main_app = main_app
        self.axis = axis.upper()
        self.completion_callback = completion_callback
        self.warning_accepted = False
        self.dont_show_again = False
        
        # Show motion warning if requested (or if preference not saved)
        if show_warning:
            self.show_motion_warning()
        else:
            # Skip warning and go directly to tuning setup
            self.warning_accepted = True
            self.show_tuning_setup()
    
    def show_motion_warning(self):
        """Show motion warning dialog"""
        warning_dialog = tk.Toplevel(self.parent)
        warning_dialog.title("Motion Warning")
        warning_dialog.geometry("450x230")
        warning_dialog.configure(bg=self.colors['main_bg'])
        warning_dialog.transient(self.parent)
        warning_dialog.grab_set()
        
        # Center the dialog
        warning_dialog.update_idletasks()
        x = (warning_dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (warning_dialog.winfo_screenheight() // 2) - (230 // 2)
        warning_dialog.geometry(f"450x230+{x}+{y}")
        
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
        message_text = ("The motor will move as part of tuning. Confirm that the motor is "
                       "spinning freely, uncoupled from any mechanics, then click OK to begin.")
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
                    if not hasattr(self.main_app.step_by_step_gui, 'show_tuning_warning'):
                        self.main_app.step_by_step_gui.show_tuning_warning = True
                    self.main_app.step_by_step_gui.show_tuning_warning = False
            
            warning_dialog.destroy()
            # Proceed to tuning setup after warning accepted
            self.show_tuning_setup()
        
        def on_cancel():
            warning_dialog.destroy()
        
        cancel_btn = tk.Button(button_frame, text="Cancel",
                              font=("Arial", 10, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'],
                              command=on_cancel,
                              width=10,
                              relief='solid', bd=2, highlightthickness=2, 
                              highlightbackground='blue', highlightcolor='blue')
        cancel_btn.pack(side='right', padx=(5, 0))
        
        ok_btn = tk.Button(button_frame, text="OK",
                          font=("Arial", 10, "bold"),
                          bg=self.colors.get('card_bg', '#f0f0f0'), fg=self.colors['main_fg'],
                          command=on_ok,
                          width=10)
        ok_btn.pack(side='right')
        
        # Focus on Cancel initially
        cancel_btn.focus_set()
    
    def show_tuning_setup(self):
        """Show motor tuning configuration dialog after warning"""
        # Create main tuning setup dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Step by Step")
        self.dialog.geometry("900x650")
        self.dialog.configure(bg=self.colors['main_bg'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        self.create_tuning_widgets()
        
        # Update dialog size after widgets are created, then center
        self.dialog.update_idletasks()
        self.dialog.minsize(900, 650)
        
        # Force geometry update to ensure content is visible
        self.dialog.update()
        
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"{self.dialog.winfo_width()}x{self.dialog.winfo_height()}+{x}+{y}")
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_tuning_widgets(self):
        """Create tuning setup widgets"""
        # State tracking
        self.auto_tuning_running = False
        self.auto_tuning_thread = None
        self.tuning_complete = False
        self.spinner_index = 0
        
        # Title
        title_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        title_frame.pack(fill='x', pady=(20, 10), padx=20)
        
        title = tk.Label(title_frame, text=f"Set up Axis {self.axis}: Motor Tuning",
                        font=("Arial", 14, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack()
        
        # Content area
        self.content_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        self.content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left side - STOP button
        self.left_frame = tk.Frame(self.content_frame, bg=self.colors['main_bg'])
        self.left_frame.pack(side='left', padx=(0, 20))
        
        # Red octagonal STOP button
        self.stop_btn = tk.Button(self.left_frame, text="STOP",
                                 font=("Arial", 16, "bold"),
                                 bg='#d32f2f', fg='white',
                                 command=self.stop_auto_tuning,
                                 width=10, height=4,
                                 relief='raised', bd=3)
        self.stop_btn.pack(pady=20)
        
        # Right side - Status and animation (will be replaced with graph on completion)
        self.right_frame = tk.Frame(self.content_frame, bg=self.colors['main_bg'])
        self.right_frame.pack(side='left', fill='both', expand=True)
        
        # Spinner animation frame
        self.spinner_frame = tk.Frame(self.right_frame, bg=self.colors['main_bg'])
        self.spinner_frame.pack(fill='both', expand=True, pady=50)
        
        # Spinner dots
        self.spinner_label = tk.Label(self.spinner_frame, text="⦿",
                                     font=("Arial", 24),
                                     bg=self.colors['main_bg'], fg=self.colors['accent_blue'])
        self.spinner_label.pack()
        
        # Status text
        self.status_label = tk.Label(self.spinner_frame, text="Running Auto Crossover",
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        self.status_label.pack(pady=(10, 0))
        
        # Start auto-tuning process
        self.start_auto_tuning()
        
        # Navigation buttons
        nav_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        nav_frame.pack(side='bottom', fill='x', pady=(10, 20), padx=20)
        
        # Back button
        self.back_btn = tk.Button(nav_frame, text="< Back",
                            font=("Arial", 10, "bold"),
                            bg=self.colors['card_bg'], fg=self.colors['main_fg'],
                            command=self.go_back,
                            width=10)
        self.back_btn.pack(side='left')
        
        # Next button (disabled until tuning complete)
        self.next_btn = tk.Button(nav_frame, text="Next >",
                            font=("Arial", 10, "bold"),
                            bg=self.colors['success_green'], fg='white',
                            command=self.go_next,
                            width=10, state='disabled')
        self.next_btn.pack(side='right')
    
    def start_auto_tuning(self):
        """Start the auto-tuning process"""
        self.auto_tuning_running = True
        
        # Start spinner animation
        self.animate_spinner()
        
        # Start auto-tuning in background thread
        self.auto_tuning_thread = threading.Thread(target=self.run_auto_crossover, daemon=True)
        self.auto_tuning_thread.start()
    
    def animate_spinner(self):
        """Animate the spinner"""
        if not self.auto_tuning_running:
            return
        
        # Rotate spinner dots
        spinner_chars = ['⦿', '◐', '◓', '◑', '◒']
        self.spinner_index = (self.spinner_index + 1) % len(spinner_chars)
        
        if hasattr(self, 'spinner_label') and self.spinner_label.winfo_exists():
            self.spinner_label.config(text=spinner_chars[self.spinner_index])
            self.dialog.after(200, self.animate_spinner)
    
    def _measure_motor_response(self, test_move_distance=50000, speed=50000):
        """Measure motor step response during a test move"""
        if not self.main_app or not self.main_app.controller:
            if self.main_app:
                self.main_app.append_test_log("ERROR: Cannot measure response - no controller")
            return None
        
        if self.main_app:
            self.main_app.append_test_log(f"[MEASURE] Starting position measurement...")
        # Get starting position
        try:
            start_pos_response = self.main_app.controller.send_command(f"TP{self.axis}")
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] TP{self.axis} response: {start_pos_response}")
            if start_pos_response:
                first = start_pos_response.strip().split('\n')[0].replace('\r', '').strip()
                first = first.split(',')[0].split(':')[0].strip()
                start_pos = float(first)
            else:
                start_pos = 0.0
        except Exception as e:
            start_pos = 0.0
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] Warning: Could not read start pos (default 0): {e}")

        # Initialize target position (may be adjusted by limit checks)
        target_pos = start_pos + test_move_distance

        # Set motion parameters
        if self.main_app:
            self.main_app.append_test_log(f"[MEASURE] Setting motion parameters: SP={speed}, AC={speed*2}")
        self.main_app.controller.send_command(f"SP{self.axis}={speed}")
        self.main_app.controller.send_command(f"AC{self.axis}={speed*2}")  # Moderate acceleration
        self.main_app.controller.send_command(f"DC{self.axis}={speed*2}")

        # Check software limits before moving
        forward_limit = None
        backward_limit = None
        try:
            fl_response = self.main_app.controller.send_command(f"MG _FL{self.axis}")
            bl_response = self.main_app.controller.send_command(f"MG _BL{self.axis}")
            
            # Parse limits
            def parse_limit(response):
                if not response:
                    return None
                lines = response.strip().split('\n')
                first_line = lines[0].strip().replace('\r', '').strip()
                val_str = first_line.split(',')[0].strip()
                if ':' in val_str:
                    val_str = val_str.split(':')[0].strip()
                try:
                    return float(val_str)
                except ValueError:
                    return None
            
            forward_limit = parse_limit(fl_response)
            backward_limit = parse_limit(bl_response)
            # Sanity clamp: ignore absurd limits (e.g., INT_MAX artifacts)
            try:
                if forward_limit is not None and abs(forward_limit) > 1e8:
                    forward_limit = None
                if backward_limit is not None and abs(backward_limit) > 1e8:
                    backward_limit = None
            except:
                pass
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] Warning: Limit check failed, using default target: {e}")

        # Check if target would exceed limits
        if forward_limit is not None and target_pos > forward_limit:
            # Adjust target to stay within limit with margin
            target_pos = forward_limit - abs(test_move_distance * 0.1)
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] Warning: Target would exceed forward limit, adjusting to {target_pos:.0f}")
        elif backward_limit is not None and target_pos < backward_limit:
            # Adjust target to stay within limit with margin
            target_pos = backward_limit + abs(test_move_distance * 0.1)
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] Warning: Target would exceed backward limit, adjusting to {target_pos:.0f}")

        # Additional safety check - if target is still invalid, use smaller move
        if (forward_limit is not None and target_pos > forward_limit) or (backward_limit is not None and target_pos < backward_limit):
            # Use a much smaller move to stay within limits
            safe_move_distance = min(10000, abs(test_move_distance) * 0.2)  # Max 10k counts or 20% of original
            if start_pos + safe_move_distance <= (forward_limit or 999999999):
                target_pos = start_pos + safe_move_distance
                if self.main_app:
                    self.main_app.append_test_log(f"[MEASURE] Using smaller safe move: {safe_move_distance:.0f} counts")
            else:
                # Move in opposite direction
                target_pos = start_pos - safe_move_distance
                if self.main_app:
                    self.main_app.append_test_log(f"[MEASURE] Moving in reverse direction: {safe_move_distance:.0f} counts")
        
        if self.main_app:
            self.main_app.append_test_log(f"[MEASURE] Starting move from {start_pos:.0f} to {target_pos:.0f}")
        
        # Use PR (position relative) instead of PA to avoid limit issues
        try:
            actual_move_distance = target_pos - start_pos
            self.main_app.controller.send_command(f"PR{self.axis}={actual_move_distance}")
            self.main_app.controller.send_command(f"BG{self.axis}")
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] Warning: PR command failed: {e}, trying PA")
            # Fallback to PA
            try:
                self.main_app.controller.send_command(f"PA{self.axis}={target_pos}")
                self.main_app.controller.send_command(f"BG{self.axis}")
            except Exception as e2:
                if self.main_app:
                    self.main_app.append_test_log(f"[MEASURE] ERROR: Both PR and PA failed: {e2}")
                raise
            
        # Measure response over time
        positions = []
        errors = []
        velocities = []
        times = []
        
        start_time = time.time()
        max_measure_time = 3.0  # Maximum 3 seconds
        settle_threshold = 100  # Consider settled when error < 100 counts
        settled = False
        
        while time.time() - start_time < max_measure_time:
            if not self.auto_tuning_running:
                self.main_app.controller.send_command(f"ST{self.axis}")
                return None
            
            current_time = time.time() - start_time
            
            # Read position and error
            try:
                pos_response = self.main_app.controller.send_command(f"TP{self.axis}")
                # Parse position - handle various response formats
                # Response might be: "1234", "1234\r\n: 11", "1234,5678", etc.
                if pos_response:
                    # Split by newline first to handle "value\r\n: error" format
                    lines = pos_response.strip().split('\n')
                    first_line = lines[0].strip() if lines else ''
                    # Remove \r if present
                    first_line = first_line.replace('\r', '').strip()
                    # Split by comma to get first value
                    pos_str = first_line.split(',')[0].strip()
                    # Remove any colon and everything after (error codes)
                    if ':' in pos_str:
                        pos_str = pos_str.split(':')[0].strip()
                    try:
                        pos = float(pos_str)
                    except ValueError:
                        if self.main_app:
                            self.main_app.append_test_log(f"[MEASURE] Warning: Could not parse position '{pos_response}' (extracted '{pos_str}'), using start_pos")
                        pos = start_pos
                else:
                    pos = start_pos
                
                error_response = self.main_app.controller.send_command(f"TE{self.axis}")
                # Parse error - handle various response formats
                if error_response:
                    # Split by newline first to handle "value\r\n: error" format
                    lines = error_response.strip().split('\n')
                    first_line = lines[0].strip() if lines else ''
                    # Remove \r if present
                    first_line = first_line.replace('\r', '').strip()
                    # Split by comma to get first value
                    error_str = first_line.split(',')[0].strip()
                    # Remove any colon and everything after (error codes)
                    if ':' in error_str:
                        error_str = error_str.split(':')[0].strip()
                    try:
                        error = abs(float(error_str))
                    except ValueError:
                        if self.main_app:
                            self.main_app.append_test_log(f"[MEASURE] Warning: Could not parse error '{error_response}' (extracted '{error_str}'), using 999999")
                        error = 999999
                else:
                    error = 999999
                
                # Try to read velocity (may not be supported on all controllers)
                try:
                    vel_response = self.main_app.controller.send_command(f"TV{self.axis}")
                    if vel_response:
                        # Parse velocity similar to position/error
                        vel_str = vel_response.strip().replace('\r\n', ' ').replace('\n', ' ').split(',')[0].strip()
                        if ':' in vel_str:
                            vel_str = vel_str.split(':')[-1].strip()
                        try:
                            vel = abs(float(vel_str))
                        except ValueError:
                            vel = 0
                    else:
                        vel = 0
                except:
                    # Calculate velocity from position change
                    if len(positions) > 0:
                        dt = current_time - times[-1] if times else 0.05
                        vel = abs((pos - positions[-1]) / dt) if dt > 0 else 0
                    else:
                        vel = 0
                
                positions.append(pos)
                errors.append(error)
                velocities.append(vel)
                times.append(current_time)
                
                # Check if settled
                if error < settle_threshold and vel < 1000:  # Low error and low velocity
                    if not settled:
                        settled = True
                        settle_time = current_time
                    # Wait a bit more to confirm settling
                    if current_time - settle_time > 0.2:
                        break
                
            except Exception as e:
                if self.main_app:
                    self.main_app.append_test_log(f"Measurement error: {e}")
                break
            
            time.sleep(0.01)  # 100 Hz sampling for smoother data
        
        # Stop motor
        try:
            self.main_app.controller.send_command(f"ST{self.axis}")
            time.sleep(0.3)
        except:
            pass
        
        if len(positions) < 10:
            if self.main_app:
                self.main_app.append_test_log(f"[MEASURE] ERROR: Only collected {len(positions)} samples (need at least 10)")
            return None
        
        if self.main_app:
            self.main_app.append_test_log(f"[MEASURE] Collected {len(positions)} samples over {times[-1]:.2f} seconds")
        
        # Calculate response characteristics
        max_error = max(errors) if errors else 0
        # Overshoot: maximum position beyond target (can't be negative - overshoot means going past target)
        overshoots = [p - target_pos for p in positions if p > target_pos]
        max_overshoot = max(overshoots) if overshoots else 0  # Only positive overshoots
        steady_state_error = abs(errors[-1]) if errors else 999999
        settle_time = times[-1] if times else max_measure_time
        max_velocity = max(velocities) if velocities else 0
        
        # Calculate overshoot percentage (0% if no overshoot)
        # Only count overshoot if position actually exceeded target
        overshoot_pct = (max_overshoot / test_move_distance * 100) if (test_move_distance > 0 and max_overshoot > 0) else 0
        
        # Clamp overshoot to reasonable range (0-100%)
        overshoot_pct = min(overshoot_pct, 100.0)
        
        return {
            'positions': positions,
            'errors': errors,
            'velocities': velocities,
            'times': times,
            'start_pos': start_pos,
            'target_pos': target_pos,
            'max_error': max_error,
            'max_overshoot': max_overshoot,
            'steady_state_error': steady_state_error,
            'settle_time': settle_time,
            'max_velocity': max_velocity,
            'overshoot_pct': overshoot_pct
        }
    
    def _calculate_optimal_pid(self, response_data, iteration=1):
        """
        Calculate optimal PID values based on measured response with iterative refinement
        
        Args:
            response_data: Dictionary with measured response characteristics
            iteration: Current iteration number (for multi-pass tuning)
        """
        if not response_data:
            return None, None, None
        
        # Get current PID values
        try:
            kp_current_response = self.main_app.controller.send_command(f"MG _KP{self.axis}")
            ki_current_response = self.main_app.controller.send_command(f"MG _KI{self.axis}")
            kd_current_response = self.main_app.controller.send_command(f"MG _KD{self.axis}")
            
            # Parse responses (handle various formats)
            def parse_value(response):
                if not response:
                    return None
                lines = response.strip().split('\n')
                first_line = lines[0].strip().replace('\r', '').strip()
                val_str = first_line.split(',')[0].strip()
                if ':' in val_str:
                    val_str = val_str.split(':')[0].strip()
                try:
                    return float(val_str)
                except ValueError:
                    return None
            
            kp_current = parse_value(kp_current_response) or 6.0
            ki_current = parse_value(ki_current_response) or 0.0
            kd_current = parse_value(kd_current_response) or 64.0
        except:
            kp_current, ki_current, kd_current = 6.0, 0.0, 64.0
        
        # Analyze response
        max_error = response_data['max_error']
        overshoot_pct = response_data['overshoot_pct']
        steady_state_error = response_data['steady_state_error']
        settle_time = response_data['settle_time']
        max_velocity = response_data['max_velocity']
        test_move_distance = abs(response_data['target_pos'] - response_data['start_pos'])
        
        if self.main_app:
            self.main_app.append_test_log(f"[ITER {iteration}] Response: Max error={max_error:.1f}, Overshoot={overshoot_pct:.1f}%, "
                                        f"Settle={settle_time:.2f}s, SS error={steady_state_error:.1f}")
        
        # Start with current values
        kp_new = kp_current
        ki_new = ki_current
        kd_new = kd_current
        
        # Calculate performance score (0-100, higher is better)
        performance_score = 100.0
        
        # Penalize for overshoot
        performance_score -= min(overshoot_pct * 2, 50)  # Up to -50 points for overshoot
        
        # Penalize for slow settling (target: <2s)
        if settle_time > 2.0:
            performance_score -= (settle_time - 2.0) * 10  # -10 points per second over target
        
        # Penalize for steady-state error (target: <50 counts)
        if steady_state_error > 50:
            performance_score -= min((steady_state_error - 50) / 10, 30)  # Up to -30 points
        
        # Penalize for high max error relative to move distance
        error_ratio = max_error / test_move_distance if test_move_distance > 0 else 1.0
        if error_ratio > 0.05:  # More than 5% error
            performance_score -= min((error_ratio - 0.05) * 200, 20)  # Up to -20 points
        
        # Clamp score to 0-100 range
        performance_score = max(0.0, min(100.0, performance_score))
        
        if self.main_app:
            self.main_app.append_test_log(f"[ITER {iteration}] Performance score: {performance_score:.1f}/100")
        
        # Determine tuning strategy based on performance
        needs_major_adjustment = performance_score < 70
        needs_refinement = performance_score < 85 and iteration < 3
        
        # STRATEGY 1: Handle steady-state error (CRITICAL for accuracy)
        if steady_state_error > 50:
            # Calculate KI based on steady-state error
            # KI should be proportional to SS error but inversely related to KP
            # Rule of thumb: KI ~ 0.01 * SS_error / max(KP, 1) but keep reasonable
            ki_suggestion = min(steady_state_error / (kp_current * 100), 1.5)
            
            if ki_current < 0.01:
                # First time adding KI - use conservative value
                ki_new = min(ki_suggestion, 0.2)
                if self.main_app:
                    self.main_app.append_test_log(f"[ITER {iteration}] Adding KI to handle SS error: {ki_new:.4f}")
            else:
                # Already has KI - increase it
                ki_new = min(ki_current * 1.3, ki_suggestion * 1.2, 1.5)
                if self.main_app:
                    self.main_app.append_test_log(f"[ITER {iteration}] Increasing KI: {ki_current:.4f} -> {ki_new:.4f}")
        
        # STRATEGY 2: Handle overshoot
        if overshoot_pct > 10:
            # High overshoot - reduce KP and increase damping
            kp_new = kp_current * 0.8
            kd_new = kd_current * 1.25
            if self.main_app:
                self.main_app.append_test_log(f"[ITER {iteration}] High overshoot - reducing KP to {kp_new:.2f}, increasing KD to {kd_new:.2f}")
        elif overshoot_pct > 5:
            # Moderate overshoot
            kp_new = kp_current * 0.9
            kd_new = kd_current * 1.1
            if self.main_app:
                self.main_app.append_test_log(f"[ITER {iteration}] Moderate overshoot - adjusting KP to {kp_new:.2f}, KD to {kd_new:.2f}")
        
        # STRATEGY 3: Handle slow settling
        if settle_time > 2.5:
            # Very slow - needs more aggressive tuning
            if overshoot_pct < 3:  # Only if not overshooting
                # Safe to increase KP significantly
                kp_new = kp_current * 1.5
                if self.main_app:
                    self.main_app.append_test_log(f"[ITER {iteration}] Very slow settling ({settle_time:.2f}s) - increasing KP to {kp_new:.2f}")
            elif overshoot_pct < 8:
                # Moderate increase
                kp_new = kp_current * 1.2
                kd_new = kd_current * 1.1  # Add damping
                if self.main_app:
                    self.main_app.append_test_log(f"[ITER {iteration}] Slow settling - increasing KP to {kp_new:.2f}, KD to {kd_new:.2f}")
        elif settle_time > 1.5 and overshoot_pct < 2:
            # Moderately slow but stable
            kp_new = kp_current * 1.25
            if self.main_app:
                self.main_app.append_test_log(f"[ITER {iteration}] Slow settling - increasing KP to {kp_new:.2f}")
        
        # STRATEGY 4: Handle high max error (poor tracking)
        error_ratio = max_error / test_move_distance if test_move_distance > 0 else 1.0
        if error_ratio > 0.1:  # More than 10% tracking error
            if overshoot_pct < 5:  # Safe to increase KP
                kp_new = kp_current * 1.4
                if self.main_app:
                    self.main_app.append_test_log(f"[ITER {iteration}] High tracking error ({error_ratio*100:.1f}%) - increasing KP to {kp_new:.2f}")
            else:
                # Overshooting but also high error - need better damping
                kd_new = kd_current * 1.3
                kp_new = kp_current * 0.95  # Slight reduction
                if self.main_app:
                    self.main_app.append_test_log(f"[ITER {iteration}] High error with overshoot - adjusting KP={kp_new:.2f}, KD={kd_new:.2f}")
        
        # STRATEGY 5: Refinement for already-good performance
        if performance_score > 85 and iteration > 1:
            # Fine-tune for optimal performance
            if steady_state_error > 10:
                ki_new = min(ki_current * 1.1, 1.0)
            if settle_time > 1.3:
                kp_new = kp_current * 1.05  # Small increase
        
        # Clamp values to reasonable ranges
        kp_new = max(1.0, min(50.0, kp_new))
        ki_new = max(0.0, min(2.0, ki_new))
        kd_new = max(10.0, min(500.0, kd_new))
        
        # Log final values
        if self.main_app:
            changes = []
            if abs(kp_new - kp_current) > 0.1:
                changes.append(f"KP: {kp_current:.2f}→{kp_new:.2f}")
            if abs(ki_new - ki_current) > 0.001:
                changes.append(f"KI: {ki_current:.4f}→{ki_new:.4f}")
            if abs(kd_new - kd_current) > 0.5:
                changes.append(f"KD: {kd_current:.2f}→{kd_new:.2f}")
            if changes:
                self.main_app.append_test_log(f"[ITER {iteration}] Adjustments: {', '.join(changes)}")
        
        return kp_new, ki_new, kd_new
    
    def run_auto_crossover(self):
        """Run the auto crossover tuning process - REAL auto-tuning with measurement and calculation"""
        # LOG IMMEDIATELY to confirm new code is running - THIS MUST APPEAR IN LOGS
        print(f"\n{'='*70}")
        print(f"NEW AUTO-TUNING CODE VERSION {TUNING_DIALOG_VERSION} - STARTING")
        print(f"{'='*70}\n")
        
        if self.main_app:
            self.main_app.append_test_log("="*70)
            self.main_app.append_test_log(f"⚡ NEW AUTO-TUNING CODE VERSION {TUNING_DIALOG_VERSION} ⚡")
            self.main_app.append_test_log("THIS SHOULD TAKE 15-30 SECONDS WITH REAL MEASUREMENTS")
            self.main_app.append_test_log("="*70)
        
        if not self.main_app or not self.main_app.controller:
            self.dialog.after(0, lambda: self.on_tuning_complete(False, "No controller connected"))
            return
        
        try:
            if self.main_app:
                self.main_app.append_test_log(f"Starting auto crossover tuning for Axis {self.axis}...")
                self.main_app.append_test_log("This will measure motor response and calculate optimal PID values")
                self.main_app.append_test_log(f"[NEW CODE] Controller available: {self.main_app.controller is not None}")
            
            # Step 1: Prepare motor - ensure it's enabled
            time.sleep(0.5)
            if not self.auto_tuning_running:
                return
            
            if self.main_app and self.main_app.controller:
                # Enable servo and set safe initial PID values
                try:
                    self.main_app.controller.send_command(f"SH{self.axis}")
                    time.sleep(0.5)
                    
                    # Read current PID or use safe defaults
                    try:
                        kp_response = self.main_app.controller.send_command(f"MG _KP{self.axis}")
                        kp_current = float(kp_response.split(',')[0].strip()) if kp_response else 6.0
                    except:
                        kp_current = 6.0
                    
                    # Start with moderate PID values for initial test
                    if kp_current < 3.0:
                        kp_test = 6.0
                        ki_test = 0.0
                        kd_test = 64.0
                        self.main_app.controller.send_command(f"KP{self.axis}={kp_test}")
                        self.main_app.controller.send_command(f"KI{self.axis}={ki_test}")
                        self.main_app.controller.send_command(f"KD{self.axis}={kd_test}")
                        time.sleep(0.2)
                    
                    # Move motor to a safe position for tuning (near center of range)
                    try:
                        current_pos_response = self.main_app.controller.send_command(f"TP{self.axis}")
                        if current_pos_response:
                            lines = current_pos_response.strip().split('\n')
                            first_line = lines[0].strip().replace('\r', '').strip()
                            val_str = first_line.split(',')[0].strip()
                            if ':' in val_str:
                                val_str = val_str.split(':')[0].strip()
                            try:
                                current_pos = float(val_str)
                                
                                # Check if motor is in a reasonable position for tuning
                                if abs(current_pos) > 50000:  # Too far from center
                                    if self.main_app:
                                        self.main_app.append_test_log(f"[TUNING] Moving motor to safe position for tuning...")
                                    
                                    # Move to a position closer to zero
                                    target_safe_pos = 0 if abs(current_pos) > 100000 else current_pos
                                    if target_safe_pos != current_pos:
                                        self.main_app.controller.send_command(f"PA{self.axis}={target_safe_pos}")
                                        self.main_app.controller.send_command(f"BG{self.axis}")
                                        time.sleep(2.0)  # Wait for move to complete
                                        self.main_app.controller.send_command(f"ST{self.axis}")
                                        time.sleep(0.3)
                                        
                                        if self.main_app:
                                            self.main_app.append_test_log(f"[TUNING] Motor repositioned for tuning")
                            except ValueError:
                                pass
                    except Exception as e:
                        if self.main_app:
                            self.main_app.append_test_log(f"[TUNING] Warning: Could not reposition motor: {e}")
                        
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: Could not prepare motor: {e}")
            
            # Step 2: Measure motor response with test move
            if self.main_app and self.main_app.controller:
                try:
                    if self.main_app:
                        self.main_app.append_test_log(f"Running test move to measure motor response...")
                    
                    # Measure response - use smaller, safer move distance
                    if self.main_app:
                        self.main_app.append_test_log(f"[TUNING] Calling _measure_motor_response...")
                    response_data = self._measure_motor_response(test_move_distance=20000, speed=30000)
                    
                    if not self.auto_tuning_running:
                        if self.main_app:
                            self.main_app.append_test_log(f"[TUNING] Tuning stopped by user")
                        return
                    
                    if not response_data:
                        error_msg = "Failed to measure motor response - no data returned"
                        if self.main_app:
                            self.main_app.append_test_log(f"[TUNING] ERROR: {error_msg}")
                        raise Exception(error_msg)
                    
                    if self.main_app:
                        self.main_app.append_test_log(f"[TUNING] Response measurement successful!")
                    
                    # Step 3: Iterative PID tuning with refinement
                    if self.main_app:
                        self.main_app.append_test_log("Analyzing response and calculating optimal PID values...")
                    
                    # Initial tuning pass
                    best_kp, best_ki, best_kd = self._calculate_optimal_pid(response_data, iteration=1)
                    best_response = response_data
                    best_score = 100.0 - response_data.get('steady_state_error', 0) * 0.1 - response_data.get('settle_time', 0) * 5
                    
                    if best_kp is None:
                        raise Exception("Failed to calculate optimal PID values")
                    
                    # Apply initial tuning
                    if self.main_app:
                        self.main_app.append_test_log(f"[PASS 1] Applying PID values: KP={best_kp:.3f}, KI={best_ki:.4f}, KD={best_kd:.3f}")
                    
                    self.main_app.controller.send_command(f"KP{self.axis}={best_kp}")
                    self.main_app.controller.send_command(f"KI{self.axis}={best_ki}")
                    self.main_app.controller.send_command(f"KD{self.axis}={best_kd}")
                    time.sleep(0.3)  # Allow PID to stabilize
                    
                    # Iterative refinement passes (up to 2 more)
                    max_iterations = 3
                    for iteration in range(2, max_iterations + 1):
                        if not self.auto_tuning_running:
                            break
                        
                        if self.main_app:
                            self.main_app.append_test_log(f"[PASS {iteration}] Running refinement measurement...")
                        
                        # Return to start position (use relative move to avoid limit issues)
                        try:
                            current_pos_response = self.main_app.controller.send_command(f"TP{self.axis}")
                            # Parse position
                            if current_pos_response:
                                lines = current_pos_response.strip().split('\n')
                                first_line = lines[0].strip().replace('\r', '').strip()
                                val_str = first_line.split(',')[0].strip()
                                if ':' in val_str:
                                    val_str = val_str.split(':')[0].strip()
                                try:
                                    current_pos = float(val_str)
                                    # Move back to zero using relative move
                                    if abs(current_pos) > 10:  # Only if not already near zero
                                        self.main_app.controller.send_command(f"PR{self.axis}={-current_pos}")
                                        self.main_app.controller.send_command(f"BG{self.axis}")
                                        time.sleep(1.5)
                                        self.main_app.controller.send_command(f"ST{self.axis}")
                                        time.sleep(0.3)
                                except ValueError:
                                    pass
                        except Exception as e:
                            if self.main_app:
                                self.main_app.append_test_log(f"[PASS {iteration}] Warning: Could not return to start: {e}")
                        
                        # Measure response with current tuning - use smaller move
                        refine_response = self._measure_motor_response(test_move_distance=15000, speed=25000)
                        
                        if not refine_response or not self.auto_tuning_running:
                            break
                        
                        # Calculate performance score
                        refine_score = 100.0
                        refine_score -= min(refine_response.get('overshoot_pct', 0) * 2, 50)
                        if refine_response.get('settle_time', 0) > 2.0:
                            refine_score -= (refine_response['settle_time'] - 2.0) * 10
                        if refine_response.get('steady_state_error', 0) > 50:
                            refine_score -= min((refine_response['steady_state_error'] - 50) / 10, 30)
                        
                        if self.main_app:
                            self.main_app.append_test_log(f"[PASS {iteration}] Score: {refine_score:.1f}/100 "
                                                         f"(SS error={refine_response['steady_state_error']:.1f}, "
                                                         f"Settle={refine_response['settle_time']:.2f}s)")
                        
                        # If performance is significantly better, use these values
                        if refine_score > best_score + 5:  # At least 5 points better
                            best_kp, best_ki, best_kd = self._calculate_optimal_pid(refine_response, iteration=iteration)
                            if best_kp is not None:
                                self.main_app.controller.send_command(f"KP{self.axis}={best_kp}")
                                self.main_app.controller.send_command(f"KI{self.axis}={best_ki}")
                                self.main_app.controller.send_command(f"KD{self.axis}={best_kd}")
                                time.sleep(0.3)
                                best_response = refine_response
                                best_score = refine_score
                                if self.main_app:
                                    self.main_app.append_test_log(f"[PASS {iteration}] Improved! New PID: KP={best_kp:.3f}, KI={best_ki:.4f}, KD={best_kd:.3f}")
                            else:
                                break  # Can't calculate better values
                        elif refine_score < best_score - 10:  # Significantly worse - revert
                            if self.main_app:
                                self.main_app.append_test_log(f"[PASS {iteration}] Performance degraded, keeping previous tuning")
                            break
                        else:
                            # Similar performance - done refining
                            if self.main_app:
                                self.main_app.append_test_log(f"[PASS {iteration}] Performance stable, tuning complete")
                            break
                    
                    # Final verification move
                    if self.main_app:
                        self.main_app.append_test_log("Running final verification move...")
                    
                    # Return to start (use relative move)
                    try:
                        current_pos_response = self.main_app.controller.send_command(f"TP{self.axis}")
                        if current_pos_response:
                            lines = current_pos_response.strip().split('\n')
                            first_line = lines[0].strip().replace('\r', '').strip()
                            val_str = first_line.split(',')[0].strip()
                            if ':' in val_str:
                                val_str = val_str.split(':')[0].strip()
                            try:
                                current_pos = float(val_str)
                                if abs(current_pos) > 10:
                                    self.main_app.controller.send_command(f"PR{self.axis}={-current_pos}")
                                    self.main_app.controller.send_command(f"BG{self.axis}")
                                    time.sleep(1.5)
                                    self.main_app.controller.send_command(f"ST{self.axis}")
                                    time.sleep(0.3)
                            except ValueError:
                                pass
                    except Exception as e:
                        if self.main_app:
                            self.main_app.append_test_log(f"Warning: Could not return to start: {e}")
                    
                    # Run final verification - use smaller move
                    verify_response = self._measure_motor_response(test_move_distance=10000, speed=20000)
                    
                    if verify_response and self.main_app:
                        final_score = 100.0
                        final_score -= min(verify_response.get('overshoot_pct', 0) * 2, 50)
                        if verify_response.get('settle_time', 0) > 2.0:
                            final_score -= (verify_response['settle_time'] - 2.0) * 10
                        if verify_response.get('steady_state_error', 0) > 50:
                            final_score -= min((verify_response['steady_state_error'] - 50) / 10, 30)
                        
                        self.main_app.append_test_log(f"✓ Final tuning score: {final_score:.1f}/100")
                        self.main_app.append_test_log(f"  Overshoot: {verify_response['overshoot_pct']:.1f}%, "
                                                     f"SS error: {verify_response['steady_state_error']:.1f} counts, "
                                                     f"Settle: {verify_response['settle_time']:.2f}s")
                    
                    # Return to start (use relative move)
                    try:
                        current_pos_response = self.main_app.controller.send_command(f"TP{self.axis}")
                        if current_pos_response:
                            lines = current_pos_response.strip().split('\n')
                            first_line = lines[0].strip().replace('\r', '').strip()
                            val_str = first_line.split(',')[0].strip()
                            if ':' in val_str:
                                val_str = val_str.split(':')[0].strip()
                            try:
                                current_pos = float(val_str)
                                if abs(current_pos) > 10:
                                    self.main_app.controller.send_command(f"PR{self.axis}={-current_pos}")
                                    self.main_app.controller.send_command(f"BG{self.axis}")
                                    time.sleep(1.5)
                                    self.main_app.controller.send_command(f"ST{self.axis}")
                            except ValueError:
                                pass
                    except Exception as e:
                        if self.main_app:
                            self.main_app.append_test_log(f"Warning: Could not return to start: {e}")
                    
                    # Store final calculated values for tracking
                    self.calculated_kp = best_kp
                    self.calculated_ki = best_ki
                    self.calculated_kd = best_kd
                    
                    # Store measured response data for graph display
                    self.measured_response_data = best_response
                    self.verification_response_data = verify_response if verify_response else None
                    
                    if self.main_app:
                        self.main_app.append_test_log(f"Auto tuning complete! New PID values calculated and applied.")
                    
                except Exception as e:
                    # Stop motor if error occurs
                    try:
                        self.main_app.controller.send_command(f"ST{self.axis}")
                    except:
                        pass
                    # Complete with error
                    error_msg = str(e)
                    if self.main_app:
                        self.main_app.append_test_log(f"Auto tuning error: {error_msg}")
                    self.dialog.after(0, lambda: self.on_tuning_complete(False, error_msg))
                    return
            
            # Step 6: Complete
            if self.auto_tuning_running:
                self.dialog.after(0, lambda: self.on_tuning_complete(True, None))
            
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Auto tuning error: {e}")
            self.dialog.after(0, lambda: self.on_tuning_complete(False, str(e)))
    
    def stop_auto_tuning(self):
        """Stop the auto-tuning process"""
        self.auto_tuning_running = False
        
        # Stop any motor motion
        try:
            if self.main_app and self.main_app.controller:
                self.main_app.controller.send_command(f"ST{self.axis}")
        except:
            pass
        
        # Update UI
        if hasattr(self, 'status_label'):
            self.status_label.config(text="Auto Crossover Stopped")
        
        if hasattr(self, 'spinner_label'):
            self.spinner_label.config(text="⏸", font=("Arial", 32), fg=self.colors.get('error_red', '#d32f2f'))
        
        # Enable Next button (allow to proceed even if stopped)
        if hasattr(self, 'next_btn'):
            self.next_btn.config(state='normal')
        
        if self.main_app:
            self.main_app.append_test_log(f"Auto tuning stopped for Axis {self.axis}")
    
    def _track_parameter_change(self, param: str, value: str):
        """Track parameter change for Save Configuration dialog"""
        if self.main_app and hasattr(self.main_app, 'step_by_step_gui'):
            if hasattr(self.main_app.step_by_step_gui, 'modified_parameters'):
                self.main_app.step_by_step_gui.modified_parameters[param] = value
    
    def on_tuning_complete(self, success, error_msg):
        """Handle completion of auto-tuning"""
        self.auto_tuning_running = False
        self.tuning_complete = success
        
        if success:
            # Query and track the new PID values after tuning
            self._read_and_track_tuning_results()
            
            # Show results graph
            self.show_tuning_results()
            
            if self.main_app:
                self.main_app.append_test_log(f"Auto crossover tuning complete for Axis {self.axis}")
        else:
            # Show error
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"Tuning Failed: {error_msg}")
            
            if self.main_app:
                self.main_app.append_test_log(f"Auto tuning failed: {error_msg}")
    
    def _read_and_track_tuning_results(self):
        """Read KP, KI, KD values from controller and track them (using calculated values if available)"""
        if not self.main_app or not self.main_app.controller:
            return
        
        try:
            # Use calculated values if available (from auto-tuning), otherwise read from controller
            if hasattr(self, 'calculated_kp') and hasattr(self, 'calculated_ki') and hasattr(self, 'calculated_kd'):
                # Use the calculated values from auto-tuning
                self._track_parameter_change(f"KP{self.axis}", f"{self.calculated_kp:.4f}")
                self._track_parameter_change(f"KI{self.axis}", f"{self.calculated_ki:.4f}")
                self._track_parameter_change(f"KD{self.axis}", f"{self.calculated_kd:.4f}")
            else:
                # Fall back to reading from controller
                kp_response = self.main_app.controller.send_command(f"MG _KP{self.axis}")
                if kp_response and not kp_response.strip().startswith('?'):
                    kp_value = kp_response.split(',')[0].strip()
                    self._track_parameter_change(f"KP{self.axis}", kp_value)
                
                ki_response = self.main_app.controller.send_command(f"MG _KI{self.axis}")
                if ki_response and not ki_response.strip().startswith('?'):
                    ki_value = ki_response.split(',')[0].strip()
                    self._track_parameter_change(f"KI{self.axis}", ki_value)
                
                kd_response = self.main_app.controller.send_command(f"MG _KD{self.axis}")
                if kd_response and not kd_response.strip().startswith('?'):
                    kd_value = kd_response.split(',')[0].strip()
                    self._track_parameter_change(f"KD{self.axis}", kd_value)
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Warning: Could not read/track PID values: {e}")
    
    def show_tuning_results(self):
        """Display the tuning results graph using REAL measured data"""
        # Remove spinner and status if they exist
        if hasattr(self, 'spinner_frame'):
            for widget in self.spinner_frame.winfo_children():
                widget.destroy()
            self.spinner_frame.pack_forget()
        
        # Create graph in the right frame
        if hasattr(self, 'right_frame'):
            # Clear any existing widgets
            for widget in self.right_frame.winfo_children():
                widget.destroy()
            
            # Use real measured data if available, otherwise show message
            if not hasattr(self, 'measured_response_data') or not self.measured_response_data:
                # No data available - show message
                no_data_label = tk.Label(self.right_frame, 
                                        text="No measurement data available\n(Run auto-tuning to see results)",
                                        font=("Arial", 12),
                                        bg=self.colors['main_bg'], 
                                        fg=self.colors['main_fg'])
                no_data_label.pack(expand=True, pady=50)
                if hasattr(self, 'stop_btn'):
                    self.stop_btn.pack_forget()
                if hasattr(self, 'next_btn'):
                    self.next_btn.config(state='normal')
                return
            
            response_data = self.measured_response_data
            
            # Extract real data
            times = np.array(response_data['times'])
            positions = np.array(response_data['positions'])
            errors = np.array(response_data['errors'])
            velocities = np.array(response_data['velocities'])

            # Resample to uniform grid and smooth for plotting only
            try:
                if len(times) >= 5 and times[-1] > times[0]:
                    t0, t1 = times[0], times[-1]
                    # 100 Hz uniform grid for smooth curves
                    t_uniform = np.linspace(t0, t1, int((t1 - t0) * 100) + 1)
                    pos_uniform = np.interp(t_uniform, times, positions)
                    err_uniform = np.interp(t_uniform, times, errors)
                    # Simple moving average smoothing (window=5)
                    def smooth(x, w=5):
                        if len(x) < w:
                            return x
                        k = np.ones(w) / w
                        y = np.convolve(x, k, mode='same')
                        # edge fallback
                        y[0:2] = x[0:2]
                        y[-2:] = x[-2:]
                        return y
                    pos_s = smooth(pos_uniform, 5)
                    err_s = smooth(err_uniform, 5)
                    # Replace originals for plotting
                    times = t_uniform
                    positions = pos_s
                    errors = err_s
                    # Recompute velocity on uniform grid for a cleaner derivative
                    dt = (times[1] - times[0]) if len(times) > 1 else 0.01
                    velocities = np.gradient(positions, dt)
            except Exception:
                pass
            start_pos = response_data['start_pos']
            target_pos = response_data['target_pos']
            
            # Convert absolute positions to relative (relative to start position)
            relative_positions = positions - start_pos
            relative_target = target_pos - start_pos
            
            # Create reference line (step function at target position)
            reference = np.full_like(times, relative_target)
            
            # For error: convert to signed error (target - actual position)
            signed_error = relative_target - relative_positions
            
            # Estimate torque/command from error and velocity (proportional to PID output)
            # This is an approximation since we can't directly read torque command
            # Use a combination of error and velocity change to estimate command
            estimated_command = np.zeros_like(times)
            for i in range(len(times)):
                if i > 0:
                    # Use filtered error and velocity; reduce derivative weight to avoid spikes
                    dt_local = (times[i] - times[i-1]) if times[i] > times[i-1] else (times[1]-times[0] if len(times)>1 else 0.01)
                    dv_dt = (velocities[i] - velocities[i-1]) / dt_local if dt_local > 0 else 0
                    estimated_command[i] = signed_error[i] * 0.01 - dv_dt * 0.00002
                else:
                    estimated_command[i] = 0
            
            # Normalize command for display (scale to reasonable range)
            if len(estimated_command) > 0:
                max_cmd = max(np.abs(estimated_command)) if max(np.abs(estimated_command)) > 0 else 1.0
                estimated_command = estimated_command / max_cmd * 5.0  # Scale to ±5V range
            
            # Create matplotlib figure
            fig = Figure(figsize=(8, 5), dpi=100, facecolor='white')
            ax = fig.add_subplot(111)
            
            # Plot reference position (blue dashed line)
            ax.plot(times, reference, 'b--', linewidth=2, label='Target Position', alpha=0.7)
            
            # Plot actual position (green solid line)
            ax.plot(times, relative_positions, 'g-', linewidth=2, label='Actual Position', alpha=0.8)
            
            # Plot error (orange line)
            ax.plot(times, signed_error, 'orange', linewidth=1.5, label='Position Error', alpha=0.7, linestyle=':')
            
            # Plot estimated command/torque on secondary y-axis (purple)
            ax2 = ax.twinx()
            ax2.plot(times, estimated_command, 'purple', linewidth=1.5, label='Est. Command', alpha=0.6, linestyle='-.')
            
            # Configure left y-axis (encoder counts)
            ax.set_ylabel('Position (Encoder Counts)', fontsize=10)
            
            # Auto-scale based on data
            pos_min = min(min(relative_positions), min(reference)) if len(relative_positions) > 0 else -100
            pos_max = max(max(relative_positions), max(reference)) if len(relative_positions) > 0 else 100
            margin = (pos_max - pos_min) * 0.1 if pos_max > pos_min else 10
            ax.set_ylim(pos_min - margin, pos_max + margin)
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
            
            # Configure right y-axis (volts)
            ax2.set_ylabel('Estimated Command (Normalized)', fontsize=10, color='purple')
            ax2.tick_params(axis='y', labelcolor='purple')
            ax2.set_ylim(-6, 6)
            ax2.set_yticks([-5, -2.5, 0, 2.5, 5])
            
            # Configure x-axis
            ax.set_xlabel('Time (seconds)', fontsize=10)
            if len(times) > 0:
                ax.set_xlim(0, max(times) * 1.05)
            
            # Add title with tuning results
            title_str = f"Axis {self.axis} Tuning Results"
            if hasattr(self, 'calculated_kp'):
                title_str += f" | KP={self.calculated_kp:.2f}, KI={self.calculated_ki:.3f}, KD={self.calculated_kd:.2f}"
            ax.set_title(title_str, fontsize=11, fontweight='bold')
            
            # Add legend
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9, framealpha=0.9)
            
            # Add text box with performance metrics
            if len(errors) > 0 and len(velocities) > 0:
                metrics_text = f"Overshoot: {response_data.get('overshoot_pct', 0):.1f}%\n"
                metrics_text += f"Settle Time: {response_data.get('settle_time', 0):.2f}s\n"
                metrics_text += f"SS Error: {response_data.get('steady_state_error', 0):.1f} counts"
                props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
                ax.text(0.02, 0.98, metrics_text, transform=ax.transAxes, fontsize=9,
                       verticalalignment='top', bbox=props)
            
            # Create canvas and add to frame with proper resizing
            canvas = FigureCanvasTkAgg(fig, self.right_frame)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Store references for cleanup
            self.tuning_canvas = canvas
            self.tuning_fig = fig
            
            # Force layout update to ensure proper resizing
            self.dialog.update_idletasks()
            
            # Configure canvas to resize with frame
            fig.set_tight_layout(True)
            
            # Hide STOP button
            if hasattr(self, 'stop_btn'):
                self.stop_btn.pack_forget()
            
            # Enable Next button
            if hasattr(self, 'next_btn'):
                self.next_btn.config(state='normal')
    
    def go_back(self):
        """Go back to previous step"""
        self.on_close()
    
    def go_next(self):
        """Proceed to next step"""
        try:
            # Stop auto-tuning if still running
            self.auto_tuning_running = False
            
            # Save tuning configuration
            if self.main_app:
                self.main_app.append_test_log(f"Tuning setup complete for Axis {self.axis}")
            
            # Mark tuning as complete
            if self.completion_callback:
                self.completion_callback('tuning')
            
            # Don't show messagebox, just close and proceed
            self.on_close()
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Save failed: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def on_close(self):
        """Handle dialog close"""
        # Stop auto-tuning
        self.auto_tuning_running = False
        
        # Stop any motor motion
        try:
            if self.main_app and self.main_app.controller:
                self.main_app.controller.send_command(f"ST{self.axis}")
        except:
            pass
        
        if hasattr(self, 'dialog') and self.dialog.winfo_exists():
            self.dialog.destroy()

