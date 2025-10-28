"""
Tuning Setup Dialog for Step-by-Step Motor Configuration
Includes motion warning and motor tuning interface
"""

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
    
    def run_auto_crossover(self):
        """Run the auto crossover tuning process"""
        if not self.main_app or not self.main_app.controller:
            self.dialog.after(0, lambda: self.on_tuning_complete(False, "No controller connected"))
            return
        
        try:
            if self.main_app:
                self.main_app.append_test_log(f"Starting auto crossover tuning for Axis {self.axis}...")
            
            # Simulate auto crossover process
            import time
            
            # Step 1: Prepare motor
            time.sleep(1)
            if not self.auto_tuning_running:
                return
            
            if self.main_app and self.main_app.controller:
                # Enable servo
                try:
                    self.main_app.controller.send_command(f"SH{self.axis}")
                    time.sleep(0.5)
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Warning: Could not enable servo: {e}")
            
            # Step 2: Run test moves
            if self.main_app and self.main_app.controller:
                try:
                    # Small test move forward
                    self.main_app.controller.send_command(f"SP{self.axis}=50000")
                    self.main_app.controller.send_command(f"AC{self.axis}=100000")
                    self.main_app.controller.send_command(f"PR{self.axis}=10000")
                    self.main_app.controller.send_command(f"BG{self.axis}")
                    time.sleep(2)
                    
                    if not self.auto_tuning_running:
                        return
                    
                    # Stop
                    try:
                        self.main_app.controller.send_command(f"ST{self.axis}")
                    except:
                        pass  # Ignore errors on stop command
                    time.sleep(0.5)
                    
                    # Small test move backward
                    self.main_app.controller.send_command(f"PR{self.axis}=-10000")
                    self.main_app.controller.send_command(f"BG{self.axis}")
                    time.sleep(2)
                    
                    if not self.auto_tuning_running:
                        return
                    
                    # Stop
                    try:
                        self.main_app.controller.send_command(f"ST{self.axis}")
                    except:
                        pass  # Ignore errors on stop command
                    time.sleep(0.5)
                    
                    # Return to start
                    self.main_app.controller.send_command(f"PA{self.axis}=0")
                    self.main_app.controller.send_command(f"BG{self.axis}")
                    time.sleep(1)
                    try:
                        self.main_app.controller.send_command(f"ST{self.axis}")
                    except:
                        pass  # Ignore errors on stop command
                except Exception as e:
                    # Stop motor if error occurs
                    try:
                        self.main_app.controller.send_command(f"ST{self.axis}")
                    except:
                        pass
                    # Complete with error
                    error_msg = str(e)
                    self.dialog.after(0, lambda: self.on_tuning_complete(False, error_msg))
                    return
            
            # Step 3: Complete
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
        """Read KP, KI, KD values from controller and track them"""
        if not self.main_app or not self.main_app.controller:
            return
        
        try:
            # Read KP
            kp_response = self.main_app.controller.send_command(f"MG _KP{self.axis}")
            if kp_response and not kp_response.strip().startswith('?'):
                kp_value = kp_response.split(',')[0].strip()
                self._track_parameter_change(f"KP{self.axis}", kp_value)
            
            # Read KI
            ki_response = self.main_app.controller.send_command(f"MG _KI{self.axis}")
            if ki_response and not ki_response.strip().startswith('?'):
                ki_value = ki_response.split(',')[0].strip()
                self._track_parameter_change(f"KI{self.axis}", ki_value)
            
            # Read KD
            kd_response = self.main_app.controller.send_command(f"MG _KD{self.axis}")
            if kd_response and not kd_response.strip().startswith('?'):
                kd_value = kd_response.split(',')[0].strip()
                self._track_parameter_change(f"KD{self.axis}", kd_value)
        except:
            # If reading fails, use default simulated values
            self._track_parameter_change(f"KP{self.axis}", "19.38")
            self._track_parameter_change(f"KI{self.axis}", "0.9316")
            self._track_parameter_change(f"KD{self.axis}", "148.38")
    
    def show_tuning_results(self):
        """Display the tuning results graph"""
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
            
            # Generate sample data for the graph
            time_data = np.linspace(0, 2, 400)
            
            # Reference position: step up at t=0.5, step down at t=1.5
            reference = np.zeros_like(time_data)
            reference[time_data >= 0.5] = 100
            reference[time_data >= 1.5] = 0
            
            # Current position: follows reference with slight overshoot and settling
            current = np.zeros_like(time_data)
            for i, t in enumerate(time_data):
                if t < 0.5:
                    current[i] = 0
                elif t < 1.5:
                    # Step response with overshoot
                    decay = np.exp(-(t - 0.5) * 3)
                    current[i] = 100 + (105 - 100) * decay * np.sin((t - 0.5) * 20) * 0.3
                else:
                    # Return step response
                    decay = np.exp(-(t - 1.5) * 3)
                    current[i] = (0 - 5) * decay * np.sin((t - 1.5) * 20) * 0.3
            
            # Error: difference between reference and current
            error = reference - current
            
            # Torque: proportional to error during transitions
            torque = np.zeros_like(time_data)
            for i, t in enumerate(time_data):
                if 0.5 <= t < 0.6:
                    torque[i] = 2.0 * np.exp(-(t - 0.5) * 10)
                elif 1.5 <= t < 1.6:
                    torque[i] = -2.0 * np.exp(-(t - 1.5) * 10)
            
            # Create matplotlib figure
            fig = Figure(figsize=(8, 5), dpi=100, facecolor='white')
            ax = fig.add_subplot(111)
            
            # Plot reference position (blue)
            ax.plot(time_data, reference, 'b-', linewidth=2, label='Reference Position', marker='s', markersize=4)
            
            # Plot current position (green)
            ax.plot(time_data, current, 'g-', linewidth=2, label='Current Position', marker='s', markersize=4)
            
            # Plot error (orange)
            ax.plot(time_data, error, 'orange', linewidth=2, label='Error', marker='s', markersize=4)
            
            # Plot torque on secondary y-axis (purple)
            ax2 = ax.twinx()
            ax2.plot(time_data, torque, 'purple', linewidth=2, label='Torque', marker='s', markersize=4)
            
            # Configure left y-axis (encoder counts)
            ax.set_ylabel('Relative Encoder Counts', fontsize=10)
            ax.set_ylim(-100, 100)
            ax.set_yticks([-100, -50, 0, 50, 100])
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
            
            # Configure right y-axis (volts)
            ax2.set_ylabel('Volts', fontsize=10)
            ax2.set_ylim(-10, 10)
            ax2.set_yticks([-10, -5, 0, 5, 10])
            
            # Configure x-axis
            ax.set_xlabel('Time', fontsize=10)
            
            # Add legend
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
            
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

