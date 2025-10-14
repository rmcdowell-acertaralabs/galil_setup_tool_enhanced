"""
GUI Motor Tuning Integration Example
How to integrate verified motor settings into your Motor Tuning page

This module shows how to:
1. Load verified settings from config.json
2. Apply settings to GUI fields
3. Send settings to controller safely
4. Verify motor operation
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import gclib
from controller_servo_maintenance import (
    setup_motor_complete,
    apply_motor_configuration,
    initialize_brushless_commutation,
    test_motor_motion,
    get_motor_status,
    save_configuration_to_eeprom
)


class MotorTuningPanel:
    """Example motor tuning panel integration"""
    
    def __init__(self, parent, controller_connection):
        """
        Initialize motor tuning panel
        
        Args:
            parent: Parent tkinter widget
            controller_connection: Active gclib connection to controller
        """
        self.parent = parent
        self.g = controller_connection
        self.current_axis = 'A'
        
        # Create frame
        self.frame = ttk.LabelFrame(parent, text="Motor Tuning", padding=10)
        self.frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create GUI elements
        self._create_widgets()
        
        # Load verified settings
        self.load_verified_settings()
    
    def _create_widgets(self):
        """Create GUI widgets for motor tuning"""
        
        # Axis selection
        axis_frame = ttk.Frame(self.frame)
        axis_frame.pack(fill='x', pady=5)
        
        ttk.Label(axis_frame, text="Axis:").pack(side='left', padx=5)
        self.axis_var = tk.StringVar(value='A')
        axis_combo = ttk.Combobox(axis_frame, textvariable=self.axis_var, 
                                   values=['A', 'B', 'C', 'D'], width=5, state='readonly')
        axis_combo.pack(side='left', padx=5)
        axis_combo.bind('<<ComboboxSelected>>', self.on_axis_changed)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(self.frame, text="Motor Settings", padding=10)
        settings_frame.pack(fill='both', expand=True, pady=5)
        
        # PID Settings
        pid_frame = ttk.LabelFrame(settings_frame, text="PID Gains", padding=5)
        pid_frame.pack(fill='x', pady=5)
        
        self.kp_var = tk.DoubleVar(value=6.0)
        self.ki_var = tk.DoubleVar(value=0.0)
        self.kd_var = tk.DoubleVar(value=64.0)
        
        self._create_setting_row(pid_frame, "KP:", self.kp_var, 0)
        self._create_setting_row(pid_frame, "KI:", self.ki_var, 1)
        self._create_setting_row(pid_frame, "KD:", self.kd_var, 2)
        
        # Torque Settings
        torque_frame = ttk.LabelFrame(settings_frame, text="Torque Limits", padding=5)
        torque_frame.pack(fill='x', pady=5)
        
        self.tl_var = tk.DoubleVar(value=5.0)
        self.tk_var = tk.DoubleVar(value=9.99)
        
        self._create_setting_row(torque_frame, "TL:", self.tl_var, 0)
        self._create_setting_row(torque_frame, "TK:", self.tk_var, 1)
        
        # Amplifier Settings
        amp_frame = ttk.LabelFrame(settings_frame, text="Amplifier", padding=5)
        amp_frame.pack(fill='x', pady=5)
        
        self.ag_var = tk.DoubleVar(value=2.0)
        self.au_var = tk.DoubleVar(value=9.0)
        
        self._create_setting_row(amp_frame, "AG:", self.ag_var, 0)
        self._create_setting_row(amp_frame, "AU:", self.au_var, 1)
        
        # Brushless Settings
        brushless_frame = ttk.LabelFrame(settings_frame, text="Brushless Configuration", padding=5)
        brushless_frame.pack(fill='x', pady=5)
        
        self.mt_var = tk.IntVar(value=-1)
        self.ce_var = tk.IntVar(value=2)
        self.bm_var = tk.IntVar(value=5000)
        
        self._create_setting_row(brushless_frame, "MT:", self.mt_var, 0)
        self._create_setting_row(brushless_frame, "CE:", self.ce_var, 1)
        self._create_setting_row(brushless_frame, "BM:", self.bm_var, 2)
        
        # Encoder Resolution
        encoder_frame = ttk.LabelFrame(settings_frame, text="Encoder", padding=5)
        encoder_frame.pack(fill='x', pady=5)
        
        self.clicks_per_turn_var = tk.IntVar(value=20000)
        self._create_setting_row(encoder_frame, "Counts/Rev:", self.clicks_per_turn_var, 0)
        
        # Status display
        status_frame = ttk.LabelFrame(self.frame, text="Current Status", padding=5)
        status_frame.pack(fill='x', pady=5)
        
        self.status_text = tk.Text(status_frame, height=6, width=50, state='disabled')
        self.status_text.pack(fill='both', expand=True)
        
        # Buttons frame
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text="Load Verified Settings", 
                   command=self.load_verified_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Apply to Controller", 
                   command=self.apply_to_controller).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Test Motor", 
                   command=self.test_motor).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save to EEPROM", 
                   command=self.save_to_eeprom, style='Warning.TButton').pack(side='left', padx=5)
        ttk.Button(button_frame, text="Refresh Status", 
                   command=self.refresh_status).pack(side='left', padx=5)
    
    def _create_setting_row(self, parent, label, variable, row):
        """Create a setting row with label, entry, and current value display"""
        ttk.Label(parent, text=label, width=15).grid(row=row, column=0, sticky='w', padx=5, pady=2)
        
        entry = ttk.Entry(parent, textvariable=variable, width=10)
        entry.grid(row=row, column=1, padx=5, pady=2)
        
        # Current value from controller
        current_label = ttk.Label(parent, text="--", width=10, foreground='blue')
        current_label.grid(row=row, column=2, padx=5, pady=2)
        
        # Store reference for updates
        setattr(self, f"{label.strip(':').lower()}_current_label", current_label)
    
    def on_axis_changed(self, event=None):
        """Handle axis selection change"""
        self.current_axis = self.axis_var.get()
        self.load_verified_settings()
        self.refresh_status()
    
    def load_verified_settings(self):
        """Load verified settings from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            axis_config = config['axis_presets'].get(self.current_axis)
            if not axis_config:
                messagebox.showwarning("Warning", 
                    f"No verified settings found for Axis {self.current_axis}")
                return
            
            # Load settings into GUI
            self.kp_var.set(axis_config.get('kp', 6.0))
            self.ki_var.set(axis_config.get('ki', 0.0))
            self.kd_var.set(axis_config.get('kd', 64.0))
            self.tl_var.set(axis_config.get('tl', 5.0))
            self.tk_var.set(axis_config.get('tk', 9.99))
            self.ag_var.set(axis_config.get('ag', 2.0))
            self.au_var.set(axis_config.get('au', 9.0))
            self.mt_var.set(axis_config.get('mt', -1))
            self.ce_var.set(axis_config.get('ce', 2))
            self.bm_var.set(axis_config.get('bm', 5000))
            self.clicks_per_turn_var.set(axis_config.get('clicks_per_turn', 20000))
            
            self.log_status(f"✓ Loaded verified settings for Axis {self.current_axis}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")
            self.log_status(f"✗ Error loading settings: {e}")
    
    def apply_to_controller(self):
        """Apply current settings to controller"""
        if not self.g:
            messagebox.showerror("Error", "Controller not connected")
            return
        
        # Confirm with user
        if not messagebox.askyesno("Confirm", 
            f"Apply settings to Axis {self.current_axis}?\n\n"
            "This will:\n"
            "1. Turn motor off\n"
            "2. Apply configuration\n"
            "3. Initialize brushless commutation (BI/BC method)\n"
            "4. Enable motor\n\n"
            "Continue?"):
            return
        
        try:
            self.log_status(f"Applying settings to Axis {self.current_axis}...")
            
            # Build config from GUI values
            config = {
                'kp': self.kp_var.get(),
                'ki': self.ki_var.get(),
                'kd': self.kd_var.get(),
                'tl': self.tl_var.get(),
                'tk': self.tk_var.get(),
                'ag': self.ag_var.get(),
                'au': self.au_var.get(),
                'mt': self.mt_var.get(),
                'ce': self.ce_var.get(),
                'ba': 1,  # Always enable brushless
                'bm': self.bm_var.get()
            }
            
            # Apply configuration
            if not apply_motor_configuration(self.g, self.current_axis, config):
                raise Exception("Configuration application failed")
            
            self.log_status("✓ Configuration applied")
            
            # Initialize brushless commutation
            self.log_status("Initializing brushless commutation (BI/BC method)...")
            if not initialize_brushless_commutation(self.g, self.current_axis, voltage=3.0):
                raise Exception("Brushless initialization failed")
            
            self.log_status("✓ Brushless initialized")
            
            # Enable motor
            self.g.GCommand(f"SH{self.current_axis}")
            self.log_status("✓ Motor enabled")
            
            # Zero position
            self.g.GCommand(f"DP{self.current_axis}=0")
            self.log_status("✓ Position zeroed")
            
            messagebox.showinfo("Success", 
                f"Settings applied successfully to Axis {self.current_axis}")
            
            # Refresh status
            self.refresh_status()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply settings: {e}")
            self.log_status(f"✗ Error: {e}")
    
    def test_motor(self):
        """Run motor verification test"""
        if not self.g:
            messagebox.showerror("Error", "Controller not connected")
            return
        
        if not messagebox.askyesno("Test Motor", 
            "Run verification test?\n\n"
            "This will move the motor 1000 counts and back.\n"
            "Ensure the motor can move freely!"):
            return
        
        try:
            self.log_status(f"Testing Axis {self.current_axis}...")
            
            success = test_motor_motion(self.g, self.current_axis, test_distance=1000)
            
            if success:
                messagebox.showinfo("Test Passed", 
                    f"Axis {self.current_axis} test PASSED!\n"
                    "Motor is operating correctly.")
                self.log_status("✓ Test PASSED")
            else:
                messagebox.showwarning("Test Failed", 
                    f"Axis {self.current_axis} test FAILED!\n"
                    "Check accuracy and following error.")
                self.log_status("✗ Test FAILED")
            
            self.refresh_status()
            
        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")
            self.log_status(f"✗ Test error: {e}")
    
    def save_to_eeprom(self):
        """Save current configuration to controller EEPROM"""
        if not self.g:
            messagebox.showerror("Error", "Controller not connected")
            return
        
        # Strong warning
        if not messagebox.askyesno("WARNING", 
            "Save configuration to EEPROM?\n\n"
            "⚠️ This will make settings PERMANENT!\n\n"
            "Only proceed if:\n"
            "✓ Motor has been tested\n"
            "✓ Motor stays cool\n"
            "✓ Position accuracy is good\n"
            "✓ No oscillation or vibration\n\n"
            "Continue?",
            icon='warning'):
            return
        
        try:
            save_configuration_to_eeprom(self.g)
            messagebox.showinfo("Saved", 
                "Configuration saved to EEPROM.\n"
                "Settings will persist on power cycle.")
            self.log_status("✓ Saved to EEPROM")
            
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")
            self.log_status(f"✗ Save error: {e}")
    
    def refresh_status(self):
        """Refresh motor status display"""
        if not self.g:
            self.log_status("Controller not connected")
            return
        
        try:
            status = get_motor_status(self.g, self.current_axis)
            
            status_text = f"Axis {self.current_axis} Status:\n"
            status_text += f"Motor: {'ON' if status.get('motor_on') else 'OFF'}\n"
            status_text += f"Position: {status.get('position', 0):.0f}\n"
            status_text += f"Following Error: {status.get('following_error', 0):.0f}\n"
            status_text += f"Torque: {status.get('torque', 0):.2f}V\n"
            status_text += f"Commutation Angle: {status.get('commutation_angle', 0):.1f}°\n"
            status_text += f"KP={status.get('kp', 0):.1f} KD={status.get('kd', 0):.1f} KI={status.get('ki', 0):.1f}"
            
            self.status_text.config(state='normal')
            self.status_text.delete('1.0', 'end')
            self.status_text.insert('1.0', status_text)
            self.status_text.config(state='disabled')
            
        except Exception as e:
            self.log_status(f"Status refresh error: {e}")
    
    def log_status(self, message):
        """Log message to status display"""
        self.status_text.config(state='normal')
        self.status_text.insert('1.0', f"{message}\n")
        self.status_text.config(state='disabled')
        
        # Also print to console
        print(f"[MotorTuning] {message}")


# Example usage in your main application
if __name__ == "__main__":
    import gclib
    
    # Create main window
    root = tk.Tk()
    root.title("Motor Tuning Example")
    root.geometry("600x800")
    
    # Connect to controller (example)
    try:
        g = gclib.py()
        g.GOpen("10.1.0.24 -s ALL")
        print("Connected to controller")
    except Exception as e:
        print(f"Connection failed: {e}")
        g = None
    
    # Create motor tuning panel
    panel = MotorTuningPanel(root, g)
    
    # Run GUI
    root.mainloop()
    
    # Cleanup
    if g:
        g.GClose()

