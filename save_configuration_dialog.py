"""
Save Configuration Dialog
Shows parameter comparison and allows saving configuration to controller
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, List, Tuple

try:
    from tkinter import scrolledtext
except ImportError:
    # Fallback for older Python versions
    pass

class SaveConfigurationDialog:
    """Dialog for reviewing and saving configuration parameters"""
    
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.dialog = None
        
        # Color scheme
        self.colors = {
            'main_bg': '#f0f0f0',
            'card_bg': '#ffffff',
            'main_fg': '#333333',
            'accent_blue': '#4A90E2',
            'success_green': '#4CAF50',
        }
        
        # Parameter defaults (factory defaults for DMC-4103)
        self.parameter_defaults = self._load_parameter_defaults()
        
        # Track which parameters have been modified
        self.modified_parameters = {}
        
        self.show_dialog()
    
    def _load_parameter_defaults(self) -> Dict[str, str]:
        """Load factory default parameter values"""
        return {
            # Global parameters
            'SDD': '256000', 'TLD': '9.9982', 'FVD': '0.00', 'EP': '256',
            'DH': '1', 'IK': '1', '_CN4': '0', '_CN3': '0', '_CN1': '-1',
            '_CN2': '-1', '_CN0': '-1', 'IA': '0.0.0.0', 'MU': '239.255.19.56',
            'LZ': '1', 'OP0': '0', 'PF': '10.0000', 'CW': '1',
            'VAS': '256000', 'VDS': '256000', 'VSS': '25000',
            'SM': '0.0.0.0', 'VAT': '256000', 'VDT': '256000', 'VST': '25000',
            'US': '0', 'TM': '1000.00', 'VF': '10.4000',
            
            # Per-axis defaults
            'AC': '256000', 'DC': '256000', 'SP': '25000',
            'KP': '6.00', 'KI': '0.0000', 'KD': '64.00',
            'TL': '9.9982', 'ER': '16384', 'MO': '1',
            'MT': '1.0', 'CE': '0', 'BI': '0', 'BM': '2000.0000',
            'AU': '1.0', 'AG': '1', 'A3': '0.0000',
            'OE': '0', 'OA': '0', 'OT': '30', 'OV': '0.9438',
            'FL': '2147483647', 'BL': '-2147483648',
            'HV': '256', 'IT': '1.0000', 'IL': '9.9982',
            'LD': '0', 'LC': '0', 'GA': '0', 'NB': '0.5',
            'NF': '0', 'NZ': '0.0', 'TK': '0.0000', 'PL': '0.0000',
            'FA': '0.00', 'FV': '0.00',
        }
    
    def get_default_for_param(self, param: str, axis: str = '') -> str:
        """Get default value for a parameter"""
        # Remove axis suffix for lookup
        base_param = param.rstrip('ABCD')
        if base_param in self.parameter_defaults:
            return self.parameter_defaults[base_param]
        return '0'  # Fallback
    
    def get_parameter_description(self, param: str) -> str:
        """Get human-readable description for a parameter"""
        descriptions = {
            'AC': 'Acceleration', 'DC': 'Deceleration', 'SP': 'Speed',
            'KP': 'Proportional Constant', 'KI': 'Integrator Constant', 'KD': 'Derivative Constant',
            'TL': 'Torque Limit', 'ER': 'Error Limit', 'MO': 'Motor Off',
            'MT': 'Motor Type', 'CE': 'Encoder Configuration', 'BI': 'Brushless Inputs',
            'BM': 'Brushless Modulo', 'AU': 'Amplifier Current Loop Gain', 'AG': 'Amplifier Gain',
            'A3': 'Amplifier Hall Correction', 'OE': 'Off On Error',
            'FL': 'Forward Software Limit', 'BL': 'Reverse Software Limit',
            'HV': 'Homing Velocity', 'IT': 'Independent Smoothing Function',
            'IL': 'Integrator Limit', 'LD': 'Overtravel Limit Disable',
            'SD': 'Switch Deceleration', 'FV': 'Velocity Feedforward',
            'EP': 'Cam table master interval and phase shift',
            'DH': 'DHCP Client Enable', 'IK': 'Ethernet Port Blocking',
            '_CN0': 'Global Limit Switch Active Level', '_CN1': 'Global Home Direction',
            '_CN2': 'Global Latch Input Active Level', '_CN3': 'Global Axis-specific Abort',
            '_CN4': 'Global Abort Input', 'IA': 'IP Address', 'MU': 'Multicast Address',
            'LZ': 'Omit Leading Zeros', 'OP': 'Output Port Bank', 'PF': 'Position Format',
            'CW': 'Program Execution when communications FIFO Full',
            'VA': 'S Vector Acceleration', 'VD': 'S Vector Deceleration', 'VS': 'S Vector Speed',
            'SM': 'Subnet Mask', 'US': 'USB port configuration',
            'TM': 'Update Time', 'VF': 'Variable Format',
            'FA': 'Acceleration Feedforward', 'TK': 'Peak Torque Limit',
            'PL': 'Pole Filter', 'LC': 'Low Current Stepper Mode',
        }
        
        base_param = param.rstrip('ABCD_0123456789')
        if base_param in descriptions:
            return descriptions[base_param]
        
        # Generate description from parameter name
        return param.replace('_', ' ').title()
    
    def show_dialog(self):
        """Display the save configuration dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Step by Step")
        self.dialog.geometry("1100x750")
        self.dialog.configure(bg=self.colors['main_bg'])
        self.dialog.resizable(True, True)
        
        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.focus_set()
        self.dialog.lift()
        
        # Main content
        self.create_content()
        
        # Update dialog size after widgets are created, then center
        self.dialog.update_idletasks()
        self.dialog.minsize(1100, 750)
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Bottom buttons
        self.create_bottom_buttons()
    
    def create_content(self):
        """Create the main content area with tabs"""
        # Notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Parameters tab
        self.create_parameters_tab(notebook)
        
        # Program tab
        self.create_program_tab(notebook)
        
        # Variables and Arrays tabs (placeholders)
        vars_frame = tk.Frame(notebook, bg=self.colors['main_bg'])
        notebook.add(vars_frame, text="Variables")
        
        arrays_frame = tk.Frame(notebook, bg=self.colors['main_bg'])
        notebook.add(arrays_frame, text="Arrays")
    
    def create_parameters_tab(self, notebook):
        """Create the Parameters tab with comparison table"""
        params_frame = tk.Frame(notebook, bg=self.colors['main_bg'])
        notebook.add(params_frame, text="Parameters")
        
        # Create treeview for parameter table
        tree_frame = tk.Frame(params_frame, bg=self.colors['main_bg'])
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview with scrollbar
        scrollbar_y = ttk.Scrollbar(tree_frame, orient='vertical')
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal')
        
        self.params_tree = ttk.Treeview(tree_frame,
                                        columns=("Description", "Param", "Default", "Saved", "New"),
                                        show="tree headings",
                                        yscrollcommand=scrollbar_y.set,
                                        xscrollcommand=scrollbar_x.set,
                                        height=20)
        
        scrollbar_y.config(command=self.params_tree.yview)
        scrollbar_x.config(command=self.params_tree.xview)
        
        # Configure columns
        self.params_tree.heading("#0", text="", anchor='w')
        self.params_tree.heading("Description", text="Description", anchor='w')
        self.params_tree.heading("Param", text="Param", anchor='w')
        self.params_tree.heading("Default", text="Default", anchor='w')
        self.params_tree.heading("Saved", text="Saved", anchor='w')
        self.params_tree.heading("New", text="New", anchor='w')
        
        self.params_tree.column("#0", width=20, minwidth=20)
        self.params_tree.column("Description", width=300, minwidth=200)
        self.params_tree.column("Param", width=80, minwidth=60)
        self.params_tree.column("Default", width=120, minwidth=80)
        self.params_tree.column("Saved", width=120, minwidth=80)
        self.params_tree.column("New", width=120, minwidth=80)
        
        # Grid layout
        self.params_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Control frame for buttons
        control_frame = tk.Frame(params_frame, bg=self.colors['main_bg'])
        control_frame.pack(fill='x', padx=10, pady=(5, 0))
        
        # Checkbox for showing unchanged
        self.show_unchanged_var = tk.BooleanVar(value=True)
        show_check = tk.Checkbutton(control_frame, text="Show unchanged",
                                   variable=self.show_unchanged_var,
                                   bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                   selectcolor=self.colors['card_bg'],
                                   command=self.toggle_unchanged)
        show_check.pack(side='left', padx=10, pady=5)
        
        # Copy parameters button
        copy_params_btn = tk.Button(control_frame, text="📋 Copy Parameters",
                                   font=("Arial", 9, "bold"),
                                   bg=self.colors['accent_blue'], fg='white',
                                   command=self.copy_parameters,
                                   width=15)
        copy_params_btn.pack(side='right', padx=(5, 0))
        
        # Populate parameters
        self.populate_parameters()
    
    def populate_parameters(self):
        """Populate the parameters tree with actual controller data"""
        if not self.main_app or not self.main_app.controller:
            return
        
        try:
            # First, get global/system parameters
            self._populate_global_parameters()
            
            # Then, get axis-specific parameters for each configured axis
            for axis in ['A', 'B', 'C', 'D']:
                if self.main_app.step_by_step_gui and axis in self.main_app.step_by_step_gui.completion_status:
                    self._populate_axis_parameters(axis)
            
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Error populating parameters: {e}")
            messagebox.showerror("Error", f"Failed to query controller parameters: {e}")
    
    def _query_controller_parameter(self, param: str) -> Tuple[str, str]:
        """
        Query both saved (EEPROM) and current (RAM) values for a parameter
        Returns: (saved_value, current_value)
        """
        try:
            # For most parameters, we can query using MG _PARAM
            # Note: Some controllers support reading EEPROM separately, but for now
            # we'll use the current RAM value for both Saved and New, then track changes
            if param.startswith('_'):
                # Internal variable, use MG directly
                response = self.main_app.controller.send_command(f"MG {param}")
            else:
                # Regular parameter
                response = self.main_app.controller.send_command(f"MG _{param}")
            
            if response and not response.strip().startswith('?'):
                # Parse response (handle comma-separated values)
                value = response.split(',')[0].strip()
                # For now, use same value for both Saved and New
                # In a real implementation, you'd query EEPROM separately
                return (value, value)
            else:
                return ('?', '?')
        except:
            # Parameter not supported or error
            return ('?', '?')
    
    def _populate_global_parameters(self):
        """Populate global/system parameters"""
        global_params = [
            ('SDD', 'D'), ('TLD', 'D'), ('FVD', ''), ('EP', ''),
            ('DH', ''), ('IK', ''), ('_CN4', ''), ('_CN3', ''), 
            ('_CN1', ''), ('_CN2', ''), ('_CN0', ''), ('IA', ''),
            ('MU', ''), ('LZ', ''), ('OP0', ''), ('PF', ''),
            ('CW', ''), ('VAS', ''), ('VDS', ''), ('VSS', ''),
            ('SM', ''), ('VAT', ''), ('VDT', ''), ('VST', ''),
            ('US', ''), ('TM', ''), ('VF', ''),
        ]
        
        for param, suffix in global_params:
            full_param = param + suffix
            default = self.get_default_for_param(full_param)
            saved, current = self._query_controller_parameter(full_param)
            
            # Use current value as "New" value
            new = current
            
            # Format values consistently
            def format_value(val):
                if val == '?' or val == '':
                    return val
                try:
                    float_val = float(val)
                    # Check if it's a whole number
                    if float_val == int(float_val):
                        return str(int(float_val))
                    # Format with up to 4 decimal places, remove trailing zeros
                    formatted = f"{float_val:.4f}".rstrip('0').rstrip('.')
                    return formatted
                except (ValueError, TypeError):
                    return str(val)
            
            saved = format_value(saved)
            new = format_value(new)
            default = format_value(default)
            
            desc = self.get_parameter_description(param)
            changed = (saved != new) and (saved != '?' and new != '?')
            tags = ("changed",) if changed else ("unchanged",)
            
            self.params_tree.insert("", "end",
                                   values=(desc, full_param, default, saved, new),
                                   tags=tags)
    
    def _populate_axis_parameters(self, axis: str):
        """Populate parameters for a specific axis"""
        # Create axis node
        axis_node = self.params_tree.insert("", "end", text=f"Axis {axis}", open=True)
        
        # List of axis-specific parameters
        axis_params = [
            'AC', 'FA', 'AU', 'AG', 'A3', 'AF', 'BW', 'BR', 'BI', 'BM', 'BB',
            'DC', 'KD', 'DV', 'EM', 'CE', 'ER', 'OF', 'FL', 'GM', 'GD', 'GR',
            'HV', 'IT', 'KI', 'IL', 'LC', 'GA', 'MO', 'MT', 'NB', 'NF', 'NZ',
            'OE', 'OA', 'OT', 'OV', 'LD', 'TK', 'PL', 'KP', 'BL', 'SP', 'YA',
            'YC', 'YB', 'KS', 'YS', 'SD', 'TL', 'FV',
        ]
        
        for param in axis_params:
            full_param = param + axis
            default = self.get_default_for_param(param, axis)
            saved, current = self._query_controller_parameter(full_param)
            
            # Track if this parameter was modified by setup dialogs
            if self.main_app and hasattr(self.main_app, 'step_by_step_gui'):
                if hasattr(self.main_app.step_by_step_gui, 'modified_parameters'):
                    if full_param in self.main_app.step_by_step_gui.modified_parameters:
                        # Use the modified value instead of current
                        current = self.main_app.step_by_step_gui.modified_parameters[full_param]
            
            # Use current value as "New" value
            new = current
            
            # Format values consistently (remove unnecessary decimals)
            def format_value(val):
                if val == '?' or val == '':
                    return val
                try:
                    float_val = float(val)
                    # Check if it's a whole number
                    if float_val == int(float_val):
                        return str(int(float_val))
                    # Format with up to 4 decimal places, remove trailing zeros
                    formatted = f"{float_val:.4f}".rstrip('0').rstrip('.')
                    return formatted
                except (ValueError, TypeError):
                    return str(val)
            
            saved = format_value(saved)
            new = format_value(new)
            default = format_value(default)
            
            # Check if this parameter was modified (even if saved == new, it might have been set)
            param_was_modified = False
            if self.main_app and hasattr(self.main_app, 'step_by_step_gui'):
                if hasattr(self.main_app.step_by_step_gui, 'modified_parameters'):
                    if full_param in self.main_app.step_by_step_gui.modified_parameters:
                        param_was_modified = True
            
            desc = self.get_parameter_description(param)
            # Parameter is changed if saved != new OR if it was explicitly modified during setup
            changed = ((saved != new) and (saved != '?' and new != '?')) or param_was_modified
            tags = ("changed",) if changed else ("unchanged",)
            
            self.params_tree.insert(axis_node, "end",
                                   values=(desc, full_param, default, saved, new),
                                   tags=tags)
        
        # Configure tag colors
        self.params_tree.tag_configure("changed", background='#fff4cd')
        self.params_tree.tag_configure("unchanged", background='white')
    
    def toggle_unchanged(self):
        """Toggle visibility of unchanged parameters"""
        # Treeview doesn't natively support hiding, so we'll rebuild
        # For now, just highlight changed items
        pass
    
    def create_program_tab(self, notebook):
        """Create the Program tab with generated code"""
        program_frame = tk.Frame(notebook, bg=self.colors['main_bg'])
        notebook.add(program_frame, text="Program")
        
        # Buttons frame for copy function
        program_buttons = tk.Frame(program_frame, bg=self.colors['main_bg'])
        program_buttons.pack(fill='x', padx=10, pady=(10, 0))
        
        copy_program_btn = tk.Button(program_buttons, text="📋 Copy Program",
                                     font=("Arial", 9, "bold"),
                                     bg=self.colors['accent_blue'], fg='white',
                                     command=self.copy_program,
                                     width=15)
        copy_program_btn.pack(side='right', padx=(5, 0))
        
        # Text widget for program code
        self.program_text = tk.Text(program_frame, wrap='none',
                                   font=("Courier", 10),
                                   bg='white', fg='black',
                                   width=80, height=25)
        self.program_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Generate and display program code
        self.generate_program_code()
    
    def generate_program_code(self):
        """Generate Galil program code for the configuration"""
        # Generate code for each configured axis
        configured_axes = []
        if self.main_app and hasattr(self.main_app, 'step_by_step_gui'):
            for axis in ['A', 'B', 'C', 'D']:
                if axis in self.main_app.step_by_step_gui.completion_status:
                    status = self.main_app.step_by_step_gui.completion_status[axis]
                    if any(status.values()):
                        configured_axes.append(axis)
        
        if not configured_axes:
            configured_axes = ['A', 'B', 'C']
        
        # Build program code for each axis
        axis_sections = []
        for axis in configured_axes:
            # Get BM value from modified parameters or query
            bm_value = 5000.0000
            bm_param = f'BM{axis}'
            if bm_param in self.modified_parameters:
                bm_value = float(self.modified_parameters[bm_param])
            else:
                try:
                    if self.main_app and self.main_app.controller:
                        response = self.main_app.controller.send_command(f"MG _{bm_param}")
                        if response and not response.strip().startswith('?'):
                            bm_value = float(response.split(',')[0].strip())
                except:
                    pass
            
            axis_code = f"""' Axis {axis} Sinusoidal Amplifier Startup Code
' This code configures the motor and encoder polarities.
MT{axis}=1.0; CE{axis}=0
' This code initializes the axis for sinusoidal commutation.
' When hall sensors are present, the BI/BC initialization mode is recommended.
' BI-1 estimates commutation using hall sensors.
' BC will set a precise commutation angle on the first hall sensor transition.
BM{axis}={bm_value}; BI{axis}=-1; BC{axis}
' The motor is now estimating commutation using BI-1.
' To complete commutation setup, the motor must move to detect a hall transition. 
' Example code has been provided below to jog the motor until a hall transition is detected. 
' Remove the comments to use this code.

' hall=_QH{axis};' store hall state
' SH{axis};' enable amplifier
' JG{axis}={bm_value}/4;' slow jog so that the commutation angle is set precisely at
' the next hall transition.
' BG{axis};' begin jog
' #hall
' WT2
' JP#hall,_QH{axis}=hall;' wait for a hall transition
' At this point, a precise commutation angle is set
' and the axis is fully configured for sinusoidal commutation
' ST{axis}
' AM{axis}
' MO{axis}
' Remove the below comment to servo the motor on startup.
' SH{axis}

"""
            axis_sections.append(axis_code)
        
        # Combine all sections
        program_code = f"""' The #AUTO subroutine is automatically executed on controller startup.
#AUTO

{''.join(axis_sections)}' End the #AUTO subroutine
EN
"""
        
        self.program_text.insert('1.0', program_code)
        self.program_text.config(state='normal')
    
    def create_bottom_buttons(self):
        """Create bottom button bar"""
        bottom_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        bottom_frame.pack(fill='x', pady=10)
        
        # Save button (left side) - green circular button with checkmark
        save_btn_frame = tk.Frame(bottom_frame, bg=self.colors['main_bg'])
        save_btn_frame.pack(side='left', padx=(20, 0))
        
        save_btn = tk.Button(save_btn_frame, text="✓",
                            font=("Arial", 20, "bold"),
                            bg='#4CAF50', fg='white',
                            command=self.save_configuration,
                            width=3, height=2,
                            relief='flat', bd=0, highlightthickness=0)
        save_btn.pack()
        
        save_label = tk.Label(save_btn_frame, text="Save",
                             font=("Arial", 9),
                             bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        save_label.pack()
        
        # Navigation buttons (right side)
        nav_frame = tk.Frame(bottom_frame, bg=self.colors['main_bg'])
        nav_frame.pack(side='right')
        
        back_btn = tk.Button(nav_frame, text="< Back",
                            font=("Arial", 10, "bold"),
                            bg=self.colors['card_bg'], fg=self.colors['main_fg'],
                            command=self.go_back, width=10)
        back_btn.pack(side='left', padx=(0, 5))
        
        finish_btn = tk.Button(nav_frame, text="Finish",
                              font=("Arial", 10, "bold"),
                              bg=self.colors['accent_blue'], fg='white',
                              command=self.finish_setup, width=10)
        finish_btn.pack(side='left')
    
    def save_configuration(self):
        """Save configuration to controller"""
        if not self.main_app or not self.main_app.controller:
            messagebox.showerror("Error", "No controller connected")
            return
        
        try:
            # Collect all parameters that have changed
            changes = []
            for item in self.params_tree.get_children():
                tags = self.params_tree.item(item, "tags")
                if tags and len(tags) > 0 and tags[0] == "changed":
                    values = self.params_tree.item(item, "values")
                    if values and len(values) > 4:
                        param = values[1]
                        new_value = values[4]
                        if new_value != '?' and new_value != '':
                            changes.append((param, new_value))
                
                # Check children (axis parameters)
                for child in self.params_tree.get_children(item):
                    child_tags = self.params_tree.item(child, "tags")
                    if child_tags and len(child_tags) > 0 and child_tags[0] == "changed":
                        child_values = self.params_tree.item(child, "values")
                        if child_values and len(child_values) > 4:
                            param = child_values[1]
                            new_value = child_values[4]
                            if new_value != '?' and new_value != '':
                                changes.append((param, new_value))
            
            # Also check modified_parameters directly (in case they match saved values but still need saving)
            if self.main_app and hasattr(self.main_app, 'step_by_step_gui'):
                if hasattr(self.main_app.step_by_step_gui, 'modified_parameters'):
                    for param, value in self.main_app.step_by_step_gui.modified_parameters.items():
                        # Check if this parameter is already in changes
                        if not any(p == param for p, v in changes):
                            if value != '?' and value != '':
                                changes.append((param, value))
                                if self.main_app:
                                    self.main_app.append_test_log(f"Adding modified parameter: {param}={value}")
            
            # Apply all changes
            for param, value in changes:
                try:
                    # Format command based on parameter type
                    if param.startswith('_'):
                        # Internal variable, can't set directly
                        continue
                    
                    # Determine if parameter needs axis suffix
                    axis_suffix = ''
                    for axis in ['A', 'B', 'C', 'D']:
                        if param.endswith(axis):
                            axis_suffix = axis
                            base_param = param[:-1]
                            break
                    
                    if axis_suffix:
                        command = f"{base_param}{axis_suffix}={value}"
                    else:
                        command = f"{param}={value}"
                    
                    self.main_app.controller.send_command(command)
                    if self.main_app:
                        self.main_app.append_test_log(f"Set {param}={value}")
                except Exception as e:
                    if self.main_app:
                        self.main_app.append_test_log(f"Failed to set {param}: {e}")
            
            # Send BN command to save to EEPROM
            response = self.main_app.controller.send_command("BN")
            
            if self.main_app:
                self.main_app.append_test_log(f"Configuration saved to controller EEPROM (BN response: {response})")
            
            messagebox.showinfo("Success", 
                f"Configuration saved successfully!\n\n{len(changes)} parameter(s) written.\n\n"
                "Power cycle the controller for changes to take effect.")
            
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Save failed: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def go_back(self):
        """Go back to previous step"""
        self.on_close()
    
    def finish_setup(self):
        """Finish the setup process"""
        try:
            # Save configuration before finishing
            self.save_configuration()
            self.on_close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to finish setup: {e}")
    
    def copy_program(self):
        """Copy program code to clipboard"""
        try:
            if hasattr(self, 'program_text'):
                program_code = self.program_text.get('1.0', 'end-1c')
                if program_code:
                    self.dialog.clipboard_clear()
                    self.dialog.clipboard_append(program_code)
                    messagebox.showinfo("Copied", "Program code copied to clipboard!")
                else:
                    messagebox.showwarning("Warning", "No program code to copy")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy program: {e}")
    
    def copy_parameters(self):
        """Copy parameters table to clipboard"""
        try:
            params_text = []
            params_text.append("Description\tParam\tDefault\tSaved\tNew")
            params_text.append("-" * 80)
            
            for item in self.params_tree.get_children():
                values = self.params_tree.item(item, "values")
                if values and len(values) >= 5:
                    params_text.append("\t".join(values[:5]))
                
                # Add children
                for child in self.params_tree.get_children(item):
                    child_values = self.params_tree.item(child, "values")
                    if child_values and len(child_values) >= 5:
                        params_text.append("\t".join(child_values[:5]))
            
            if params_text:
                clipboard_text = "\n".join(params_text)
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(clipboard_text)
                messagebox.showinfo("Copied", "Parameters copied to clipboard!")
            else:
                messagebox.showwarning("Warning", "No parameters to copy")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy parameters: {e}")
    
    def on_close(self):
        """Handle dialog close"""
        if hasattr(self, 'dialog') and self.dialog.winfo_exists():
            self.dialog.destroy()
