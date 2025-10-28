"""
Encoder Setup Dialog for Step-by-Step Motor Configuration
Implements a dialog similar to commercial Galil tools with real-time encoder position monitoring
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
import re

class EncoderSetupDialog:
    """Dialog for configuring encoder direction and settings"""
    
    def __init__(self, parent, colors, main_app, axis, completion_callback=None):
        self.parent = parent
        self.colors = colors
        self.main_app = main_app
        self.axis = axis.upper()
        self.completion_callback = completion_callback  # Callback to mark as complete
        
        # State
        self.update_running = False
        self.update_thread = None
        self.current_position = 0
        self.initial_position = 0
        self.reverse_direction = False
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Step by Step")
        self.dialog.geometry("550x400")
        self.dialog.configure(bg=self.colors['main_bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        self.create_widgets()
        self.start_position_updates()
        
        # Update dialog size after widgets are created, then center
        self.dialog.update_idletasks()
        self.dialog.minsize(550, 400)
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Title
        title_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        title_frame.pack(fill='x', pady=(20, 10), padx=20)
        
        title = tk.Label(title_frame, text=f"Quadrature Encoder Setup - Axis {self.axis}",
                        font=("Arial", 14, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack()
        
        # Instructions
        instructions = tk.Label(self.dialog, 
                               text="Move the encoder in the desired positive direction, then reverse the direction if necessary.",
                               font=("Arial", 9),
                               bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                               wraplength=450, justify='left')
        instructions.pack(pady=(0, 20), padx=20)
        
        # Position display frame
        position_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        position_frame.pack(pady=20, padx=20)
        
        # Position label
        label = tk.Label(position_frame, text="Position",
                        font=("Arial", 10, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        label.pack(anchor='w', pady=(0, 5))
        
        # Position display and controls frame
        display_frame = tk.Frame(position_frame, bg=self.colors['main_bg'])
        display_frame.pack(fill='x')
        
        # Large position display (digital-style)
        self.position_display = tk.Label(display_frame,
                                         text="0",
                                         font=("Courier", 24, "bold"),
                                         bg='black',
                                         fg='#00ff00',
                                         width=12,
                                         anchor='e',
                                         relief='sunken',
                                         bd=3)
        self.position_display.pack(side='left', padx=(0, 10))
        
        # Reset button
        reset_btn = tk.Button(display_frame, text="Reset",
                             font=("Arial", 9),
                             bg=self.colors['accent_blue'], fg='white',
                             command=self.reset_position,
                             width=10)
        reset_btn.pack(side='left', padx=(0, 10))
        
        # Reverse direction checkbox
        self.reverse_var = tk.BooleanVar(value=False)
        reverse_check = tk.Checkbutton(display_frame,
                                      text="Reverse direction",
                                      font=("Arial", 9),
                                      bg=self.colors['main_bg'],
                                      fg=self.colors['main_fg'],
                                      variable=self.reverse_var,
                                      command=self.on_reverse_changed,
                                      selectcolor=self.colors['card_bg'])
        reverse_check.pack(side='left', padx=10)
        
        # Navigation buttons
        nav_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        nav_frame.pack(side='bottom', fill='x', pady=(20, 10), padx=20)
        
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
    
    def start_position_updates(self):
        """Start real-time encoder position updates"""
        if not self.main_app or not self.main_app.controller:
            self.position_display.config(text="No Controller")
            return
        
        # Disable motor/servo for this axis to allow manual movement during encoder setup
        try:
            if self.main_app and self.main_app.controller:
                # Stop any motion first
                self.main_app.controller.send_command(f"ST{self.axis}")
                # Turn motor off to allow manual movement
                self.main_app.controller.send_command(f"MO{self.axis}")
                if self.main_app:
                    self.main_app.append_test_log(f"Motor disabled for Axis {self.axis} to allow manual encoder movement")
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Warning: Could not disable motor: {e}")
        
        self.update_running = True
        self._pending_update_flag = False
        self.update_thread = threading.Thread(target=self.update_position_loop, daemon=True)
        self.update_thread.start()
        self.initial_position = self.current_position
    
    def update_position_loop(self):
        """Update encoder position in real-time"""
        last_display_position = None
        update_threshold = 2  # Only update if position changes by at least 2 counts
        
        while self.update_running:
            try:
                if self.main_app and self.main_app.controller:
                    # Read encoder position
                    response = self.main_app.controller.send_command(f"TP{self.axis}")
                    if response and not response.strip().startswith('?'):
                        # Parse position (handle comma-separated values)
                        try:
                            pos_str = response.split(',')[0].strip()
                            position = int(float(pos_str))
                            
                            # Apply reverse if checked to get display position
                            display_position = -position if self.reverse_var.get() else position
                            
                            # Only update if display position changed significantly (threshold prevents blinking)
                            if last_display_position is None or abs(display_position - last_display_position) >= update_threshold:
                                # Update display (must be in main thread)
                                if self.dialog.winfo_exists() and not self._pending_update_flag:
                                    self._pending_update_flag = True
                                    self.dialog.after_idle(lambda p=display_position, s=self: self.update_display_and_reset_flag(p, s))
                                
                                self.current_position = position
                                last_display_position = display_position
                        except (ValueError, IndexError):
                            pass
            except Exception as e:
                # Silently handle errors to avoid log spam
                pass
            
            time.sleep(0.1)  # Update 10 times per second
    
    def update_display_and_reset_flag(self, position, self_ref):
        """Update display and reset pending flag"""
        if hasattr(self_ref, '_pending_update_flag'):
            self_ref._pending_update_flag = False
        self_ref.update_display(position)
    
    def update_display(self, position):
        """Update the position display (called from main thread)"""
        if not hasattr(self, 'position_display') or not self.position_display.winfo_exists():
            return
        
        try:
            # Only update if the value has changed to prevent blinking
            current_text = self.position_display.cget('text')
            new_text = str(position)
            if current_text != new_text:
                self.position_display.config(text=new_text)
        except tk.TclError:
            # Widget was destroyed, stop trying to update
            pass
    
    def reset_position(self):
        """Reset the encoder position to zero"""
        try:
            if self.main_app and self.main_app.controller:
                # Zero the position
                self.main_app.controller.send_command(f"DP{self.axis}=0")
                if self.main_app:
                    self.main_app.append_test_log(f"Axis {self.axis} position zeroed")
                messagebox.showinfo("Reset", f"Axis {self.axis} position reset to zero")
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Reset failed: {e}")
            messagebox.showerror("Error", f"Failed to reset position: {e}")
    
    def on_reverse_changed(self):
        """Handle reverse direction checkbox change"""
        self.reverse_direction = self.reverse_var.get()
        if self.main_app:
            action = "enabled" if self.reverse_direction else "disabled"
            self.main_app.append_test_log(f"Axis {self.axis} reverse direction {action}")
        
        # Apply reverse to encoder polarity if controller connected
        try:
            if self.main_app and self.main_app.controller and self.reverse_direction:
                # Set encoder reverse (CE=2 for reverse)
                try:
                    current_ce = self.main_app.controller.send_command(f"MG _CE{self.axis}")
                    try:
                        ce_value = int(float(current_ce.split(',')[0] if current_ce else "0"))
                        # Toggle reverse bit (bit 1)
                        new_ce = (ce_value | 2) if self.reverse_var.get() else (ce_value & ~2)
                        self.main_app.controller.send_command(f"CE{self.axis}={new_ce}")
                        if self.main_app:
                            self.main_app.append_test_log(f"Set CE{self.axis}={new_ce}")
                    except:
                        # Simple toggle - set to 2 for reverse, 0 for normal
                        self.main_app.controller.send_command(f"CE{self.axis}={2 if self.reverse_direction else 0}")
                        if self.main_app:
                            self.main_app.append_test_log(f"Set CE{self.axis}={2 if self.reverse_direction else 0}")
                except:
                    # _CE command not supported or failed, try direct CE command
                    try:
                        self.main_app.controller.send_command(f"CE{self.axis}={2 if self.reverse_direction else 0}")
                    except:
                        pass  # Silently fail if command not supported
        except Exception as e:
            # Silently handle errors to avoid log spam
            pass
    
    def go_back(self):
        """Go back to previous step"""
        self.on_close()
    
    def go_next(self):
        """Proceed to next step"""
        try:
            # Save encoder configuration
            if self.main_app and self.main_app.controller and self.reverse_direction:
                # Already applied in on_reverse_changed, but ensure it's set
                pass
            
            if self.main_app:
                self.main_app.append_test_log(f"Encoder setup complete for Axis {self.axis}")
            
            # Mark encoder as complete
            if self.completion_callback:
                self.completion_callback('encoder')
            
            messagebox.showinfo("Success", f"Encoder configuration saved for Axis {self.axis}")
            self.on_close()
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Save failed: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def on_close(self):
        """Handle dialog close"""
        self.update_running = False
        if self.update_thread and self.update_thread.is_alive():
            time.sleep(0.2)  # Give thread time to stop
        
        # Motor remains off after encoder setup - it will be enabled during motor setup
        # This allows safe manual movement during encoder testing
        if self.dialog.winfo_exists():
            self.dialog.destroy()

