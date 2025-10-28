"""
Step-by-Step Motor Configuration GUI
Creates a modern, intuitive interface for motor configuration similar to commercial tools
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict
import threading
import time
from encoder_setup_dialog import EncoderSetupDialog
from motor_setup_dialog import MotorSetupDialog
from tuning_setup_dialog import TuningSetupDialog
from io_setup_dialog import IOSetupDialog
from controller_info_dialog import ControllerInfoDialog
from save_configuration_dialog import SaveConfigurationDialog

class StepByStepMotorGUI:
    """Step-by-Step Motor Configuration Interface"""
    
    def __init__(self, parent_frame, colors, main_app):
        self.parent_frame = parent_frame
        self.colors = colors
        self.main_app = main_app
        self.current_axis = "A"
        
        # Variables for dropdowns
        self.encoder_vars = {}
        self.motor_vars = {}
        
        # Track completion status for each axis {axis: {encoder: bool, motor: bool, tuning: bool}}
        self.completion_status = {}
        for axis in ['A', 'B', 'C', 'D']:
            self.completion_status[axis] = {
                'encoder': False,
                'motor': False,
                'tuning': False
            }
        
        # Store button references for updating
        self.setup_buttons = {}
        
        # Store axis label references for selection highlighting
        self.axis_labels = {}
        
        # Track modified parameters for Save Configuration dialog
        self.modified_parameters = {}
        
        # Warning preferences
        self.show_motion_warning = True  # Can be saved to config file
        self.show_tuning_warning = True  # Can be saved to config file
        
        self.create_interface()
        
        # Highlight the initial selected axis (Axis A by default)
        if 'A' in self.axis_labels and hasattr(self, 'colors'):
            self.axis_labels['A'].config(
                bg=self.colors['accent_blue'],
                relief='solid',
                borderwidth=2
            )
    
    def create_interface(self):
        """Create the main step-by-step interface"""
        # Title
        title_frame = tk.Frame(self.parent_frame, bg=self.colors['main_bg'])
        title_frame.pack(fill='x', pady=(0, 20))
        
        title = tk.Label(title_frame, text="Step by Step Home", 
                        font=("Arial", 20, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack(anchor='w')
        
        # Main content container
        main_container = tk.Frame(self.parent_frame, bg=self.colors['main_bg'])
        main_container.pack(fill='both', expand=True)
        
        # Left side - Axis Configuration
        left_frame = tk.Frame(main_container, bg=self.colors['card_bg'], relief='solid', bd=2)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10), pady=10)
        
        # Right side - Configure buttons
        right_frame = tk.Frame(main_container, bg=self.colors['card_bg'], relief='solid', bd=2, width=200)
        right_frame.pack(side='right', fill='y', padx=(10, 0), pady=10)
        right_frame.pack_propagate(False)
        
        # Create left side content
        self.create_axis_configuration(left_frame)
        
        # Create right side content
        self.create_configure_panel(right_frame)
    
    def create_axis_configuration(self, parent):
        """Create the axis configuration table"""
        # Title
        title_label = tk.Label(parent, text="Axis Configuration", 
                              font=("Arial", 14, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'])
        title_label.pack(pady=(15, 10))
        
        # Table frame
        table_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        table_frame.pack(fill='x', padx=20, pady=10)
        
        # Headers
        headers_frame = tk.Frame(table_frame, bg=self.colors['card_bg'])
        headers_frame.pack(fill='x')
        
        tk.Label(headers_frame, text="Axis", font=("Arial", 10, "bold"),
                bg=self.colors['card_bg'], fg=self.colors['main_fg'], width=8).grid(row=0, column=0)
        tk.Label(headers_frame, text="Encoder", font=("Arial", 10, "bold"),
                bg=self.colors['card_bg'], fg=self.colors['main_fg'], width=15).grid(row=0, column=1, padx=5)
        tk.Label(headers_frame, text="Motor", font=("Arial", 10, "bold"),
                bg=self.colors['card_bg'], fg=self.colors['main_fg'], width=15).grid(row=0, column=2, padx=5)
        
        # Create rows for each axis
        encoder_options = ["Quadrature", "Index", "Hall", "Absolute"]
        motor_options = ["Brushless", "Brush", "Stepper", "None"]
        
        for i, axis in enumerate(['A', 'B', 'C', 'D'], 1):
            row_frame = tk.Frame(table_frame, bg=self.colors['card_bg'])
            row_frame.pack(fill='x', pady=3)
            
            # Axis label (stored for selection highlighting)
            axis_label = tk.Label(row_frame, text=axis, font=("Arial", 12, "bold"),
                                 bg=self.colors['card_bg'], fg=self.colors['main_fg'], width=8,
                                 relief='flat', borderwidth=2)
            axis_label.grid(row=0, column=0, sticky='w', padx=2, pady=2)
            self.axis_labels[axis] = axis_label
            
            # Encoder dropdown
            self.encoder_vars[axis] = tk.StringVar(value="Quadrature")
            encoder_combo = ttk.Combobox(row_frame, textvariable=self.encoder_vars[axis],
                                        values=encoder_options, state="readonly", width=12)
            encoder_combo.grid(row=0, column=1, padx=5)
            
            # Bind with proper closure
            def make_encoder_handler(ax):
                return lambda e: self.on_encoder_changed(ax)
            encoder_combo.bind('<<ComboboxSelected>>', make_encoder_handler(axis))
            
            # Also make axis label clickable to select axis
            def make_axis_click_handler(ax):
                return lambda e: self.select_axis(ax)
            axis_label.bind('<Button-1>', make_axis_click_handler(axis))
            axis_label.config(cursor='hand2')
            
            # Motor dropdown
            self.motor_vars[axis] = tk.StringVar(value="Brushless")
            motor_combo = ttk.Combobox(row_frame, textvariable=self.motor_vars[axis],
                                      values=motor_options, state="readonly", width=12)
            motor_combo.grid(row=0, column=2, padx=5)
            
            # Bind with proper closure
            def make_motor_handler(ax):
                return lambda e: self.on_motor_changed(ax)
            motor_combo.bind('<<ComboboxSelected>>', make_motor_handler(axis))
        
        # Axis Setup section - large buttons
        setup_frame = tk.Frame(parent, bg=self.colors['main_bg'])
        setup_frame.pack(fill='both', expand=True, padx=20, pady=(20, 10))
        
        setup_title = tk.Label(setup_frame, text=f"Axis {self.current_axis} Setup",
                               font=("Arial", 14, "bold"),
                               bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        setup_title.pack(pady=(0, 15))
        
        # Store title for updates
        self.setup_title = setup_title
        
        # Three large buttons in a row
        buttons_frame = tk.Frame(setup_frame, bg=self.colors['main_bg'])
        buttons_frame.pack(fill='both', expand=True)
        
        # Store buttons by type for updating
        if self.current_axis not in self.setup_buttons:
            self.setup_buttons[self.current_axis] = {}
        
        # Encoder button
        encoder_btn_frame = self.create_large_button(buttons_frame, "Encoder", "⚡",
                                                     self.colors['accent_blue'],
                                                     lambda: self.show_encoder_setup())
        encoder_btn_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.setup_buttons[self.current_axis]['encoder'] = encoder_btn_frame
        
        # Motor button
        motor_btn_frame = self.create_large_button(buttons_frame, "Motor", "⚙",
                                                  self.colors['accent_blue'],
                                                  lambda: self.show_motor_setup())
        motor_btn_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.setup_buttons[self.current_axis]['motor'] = motor_btn_frame
        
        # Tuning button
        tuning_btn_frame = self.create_large_button(buttons_frame, "Tuning", "🎯",
                                                   self.colors['accent_blue'],
                                                   lambda: self.show_tuning_setup())
        tuning_btn_frame.pack(side='left', fill='both', expand=True, padx=5)
        self.setup_buttons[self.current_axis]['tuning'] = tuning_btn_frame
        
        # Update button states based on completion
        self.update_button_states()
        
        # Cancel button at bottom
        cancel_btn = tk.Button(parent, text="Cancel", 
                              font=("Arial", 10, "bold"),
                              bg=self.colors['error_red'], fg='white',
                              command=self.cancel_setup,
                              width=15, height=2)
        cancel_btn.pack(side='bottom', pady=15)
    
    def create_large_button(self, parent, text, icon, bg_color, command):
        """Create a large square button with icon and text"""
        btn_frame = tk.Frame(parent, bg=bg_color, relief='raised', bd=3)
        
        # Store original color
        btn_frame.original_bg = bg_color
        btn_frame.text = text
        
        def on_enter(e):
            if not hasattr(btn_frame, 'is_complete') or not btn_frame.is_complete:
                # Highlight effect - raised border instead of color change
                btn_frame.config(relief='raised', bd=3)
        
        def on_leave(e):
            if not hasattr(btn_frame, 'is_complete') or not btn_frame.is_complete:
                btn_frame.config(bg=btn_frame.original_bg, relief='flat', bd=2)
        
        btn_frame.bind('<Enter>', on_enter)
        btn_frame.bind('<Leave>', on_leave)
        btn_frame.bind('<Button-1>', lambda e: command())
        
        # Icon (text-based emoji) - stored for updating
        icon_label = tk.Label(btn_frame, text=icon, font=("Arial", 32),
                             bg=bg_color, fg='white')
        icon_label.pack(pady=(20, 10))
        icon_label.bind('<Button-1>', lambda e: command())
        btn_frame.icon_label = icon_label  # Store reference
        
        # Text
        text_label = tk.Label(btn_frame, text=text, font=("Arial", 14, "bold"),
                             bg=bg_color, fg='white')
        text_label.pack(pady=(0, 20))
        text_label.bind('<Button-1>', lambda e: command())
        btn_frame.text_label = text_label  # Store reference
        
        return btn_frame
    
    def update_button_states(self):
        """Update button icons and colors based on completion status"""
        axis = self.current_axis
        if axis not in self.setup_buttons:
            return
        
        status = self.completion_status[axis]
        
        for button_type in ['encoder', 'motor', 'tuning']:
            if button_type in self.setup_buttons[axis]:
                btn_frame = self.setup_buttons[axis][button_type]
                is_complete = status[button_type]
                
                if is_complete:
                    # Show checkmark and change to green
                    btn_frame.config(bg=self.colors['success_green'])
                    btn_frame.icon_label.config(bg=self.colors['success_green'], text="✓")
                    btn_frame.is_complete = True
                else:
                    # Show original icon and color
                    icons = {'encoder': '⚡', 'motor': '⚙', 'tuning': '🎯'}
                    btn_frame.config(bg=btn_frame.original_bg)
                    btn_frame.icon_label.config(bg=btn_frame.original_bg, text=icons[button_type])
                    btn_frame.is_complete = False
    
    def mark_complete(self, button_type):
        """Mark a setup step as complete"""
        self.completion_status[self.current_axis][button_type] = True
        self.update_button_states()
        if self.main_app:
            self.main_app.append_test_log(f"Axis {self.current_axis} {button_type} setup completed")
    
    def mark_complete_callback(self, button_type):
        """Callback function to mark steps as complete (passed to dialogs)"""
        self.mark_complete(button_type)
    
    def select_axis(self, axis):
        """Select an axis to configure"""
        old_axis = self.current_axis
        self.current_axis = axis
        
        # Update visual selection indication
        if hasattr(self, 'axis_labels'):
            # Deselect old axis
            if old_axis in self.axis_labels:
                self.axis_labels[old_axis].config(
                    bg=self.colors['card_bg'],
                    relief='flat',
                    borderwidth=2
                )
            # Select new axis
            if axis in self.axis_labels:
                self.axis_labels[axis].config(
                    bg=self.colors['accent_blue'],
                    relief='solid',
                    borderwidth=2
                )
        
        if hasattr(self, 'setup_title'):
            self.setup_title.config(text=f"Axis {self.current_axis} Setup")
        if self.main_app:
            self.main_app.append_test_log(f"Selected Axis {axis} for configuration")
        
        # Create buttons for new axis if they don't exist
        if axis not in self.setup_buttons:
            self.setup_buttons[axis] = {}
            # Reuse existing button frames but update their commands
            # The buttons should work for any axis since they use self.current_axis
            if old_axis in self.setup_buttons:
                for btn_type in ['encoder', 'motor', 'tuning']:
                    if btn_type in self.setup_buttons[old_axis]:
                        self.setup_buttons[axis][btn_type] = self.setup_buttons[old_axis][btn_type]
        
        # Update button states for new axis
        self.update_button_states()
    
    def create_configure_panel(self, parent):
        """Create the configure panel on the right"""
        title_label = tk.Label(parent, text="Configure", 
                              font=("Arial", 14, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'])
        title_label.pack(pady=(15, 20))
        
        # IO Setup button
        io_btn = self.create_vertical_button(parent, "IO Setup", "📊",
                                            lambda: self.show_io_setup())
        io_btn.pack(fill='x', padx=15, pady=10)
        
        # Info button
        info_btn = self.create_vertical_button(parent, "Info", "🔍",
                                              lambda: self.show_info())
        info_btn.pack(fill='x', padx=15, pady=10)
        
        # Save button
        save_btn = self.create_vertical_button(parent, "Save", "💾",
                                              lambda: self.save_configuration())
        save_btn.pack(fill='x', padx=15, pady=10)
    
    def create_vertical_button(self, parent, text, icon, command):
        """Create a vertical button"""
        btn = tk.Button(parent, text=f"{icon}\n{text}", 
                       font=("Arial", 12, "bold"),
                       bg=self.colors['accent_blue'], fg='white',
                       command=command,
                       width=15, height=4)
        
        def on_enter(e):
            # Highlight effect - slightly brighter blue
            btn.config(bg='#6BA3E8', relief='raised')
        
        def on_leave(e):
            btn.config(bg=self.colors['accent_blue'], relief='flat')
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def on_encoder_changed(self, axis):
        """Handle encoder type change"""
        encoder_type = self.encoder_vars[axis].get()
        if self.main_app:
            self.main_app.append_test_log(f"Axis {axis} encoder set to: {encoder_type}")
    
    def on_motor_changed(self, axis):
        """Handle motor type change"""
        motor_type = self.motor_vars[axis].get()
        if self.main_app:
            self.main_app.append_test_log(f"Axis {axis} motor set to: {motor_type}")
    
    def show_encoder_setup(self):
        """Show encoder configuration dialog"""
        if self.main_app:
            self.main_app.append_test_log(f"Opening encoder setup for Axis {self.current_axis}")
        
        # Open encoder setup dialog
        encoder_dialog = EncoderSetupDialog(self.parent_frame.master, self.colors, self.main_app, 
                                           self.current_axis, self.mark_complete_callback)
    
    def show_motor_setup(self):
        """Show motor configuration dialog"""
        if self.main_app:
            self.main_app.append_test_log(f"Opening motor setup for Axis {self.current_axis}")
        
        # Open motor setup dialog (will show warning unless disabled)
        motor_dialog = MotorSetupDialog(self.parent_frame.master, self.colors, self.main_app,
                                       self.current_axis, self.mark_complete_callback,
                                       show_warning=self.show_motion_warning)
    
    def show_tuning_setup(self):
        """Show tuning configuration dialog"""
        if self.main_app:
            self.main_app.append_test_log(f"Opening tuning setup for Axis {self.current_axis}")
        
        # Open tuning setup dialog (will show warning unless disabled)
        tuning_dialog = TuningSetupDialog(self.parent_frame.master, self.colors, self.main_app,
                                         self.current_axis, self.mark_complete_callback,
                                         show_warning=self.show_tuning_warning)
    
    def show_io_setup(self):
        """Show IO setup dialog"""
        if self.main_app:
            self.main_app.append_test_log("Opening IO Setup")
        
        # Open IO setup dialog
        io_dialog = IOSetupDialog(self.parent_frame.master, self.colors, self.main_app)
    
    def show_info(self):
        """Show system information"""
        if self.main_app:
            self.main_app.append_test_log("Opening system information")
        
        # Open controller info dialog
        info_dialog = ControllerInfoDialog(self.parent_frame.master, self.colors, self.main_app)
    
    def save_configuration(self):
        """Save current configuration"""
        if self.main_app:
            self.main_app.append_test_log("Opening save configuration dialog...")
        
        try:
            # Open save configuration dialog (show_dialog is called in __init__)
            save_dialog = SaveConfigurationDialog(self.parent_frame.master, self.main_app)
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Error opening save dialog: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to open save configuration dialog:\n{e}")
    
    def cancel_setup(self):
        """Cancel the setup"""
        if self.main_app:
            self.main_app.append_test_log("Setup cancelled")

