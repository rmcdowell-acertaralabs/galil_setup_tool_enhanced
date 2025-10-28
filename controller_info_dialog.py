"""
Controller Information Dialog
Displays detailed controller hardware and firmware information
"""

import tkinter as tk
from tkinter import messagebox
import re

class ControllerInfoDialog:
    """Dialog for displaying controller information"""
    
    def __init__(self, parent, colors, main_app):
        self.parent = parent
        self.colors = colors
        self.main_app = main_app
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Step by Step")
        self.dialog.geometry("700x700")
        self.dialog.configure(bg=self.colors['main_bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        self.create_widgets()
        
        # Update dialog size after widgets are created, then center
        self.dialog.update_idletasks()
        self.dialog.minsize(700, 700)
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Title
        title_frame = tk.Frame(self.dialog, bg=self.colors['main_bg'])
        title_frame.pack(fill='x', pady=(20, 15), padx=20)
        
        title = tk.Label(title_frame, text="Controller Information",
                        font=("Arial", 18, "bold"),
                        bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title.pack()
        
        # Content area (scrollable)
        canvas = tk.Canvas(self.dialog, bg=self.colors['main_bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['main_bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=10)
        
        # Get controller information
        info = self.get_controller_info()
        
        # Firmware Info section
        self.create_info_section(scrollable_frame, "Firmware Info", [
            ("Model:", info.get('model', 'Unknown')),
            ("Revision:", info.get('revision', 'Unknown')),
            ("Serial:", info.get('serial', 'Unknown'))
        ])
        
        # DMC-4103 Info section
        self.create_info_section(scrollable_frame, "DMC-4103 Info", [
            ("Axes:", str(info.get('axes', 4)))
        ])
        
        # Encoder Support section
        encoder_support = [
            ("Quadrature", info.get('quadrature_supported', True))
        ]
        self.create_checkmark_section(scrollable_frame, "Encoder Support", encoder_support)
        
        # Axis Bank 1 section
        axis_features = [
            ("AMP-43540", True),
            ("Brushless Motor", info.get('brushless_supported', True)),
            ("Brushed Motor", info.get('brushed_supported', True))
        ]
        self.create_checkmark_section(scrollable_frame, "Axis Bank 1 (A - D)", axis_features)
        
        # Resources section
        self.create_resources_section(scrollable_frame)
        
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
                            bg=self.colors['accent_blue'], fg='white',
                            command=self.go_next,
                            width=10)
        next_btn.pack(side='right')
    
    def create_info_section(self, parent, title, items):
        """Create an information section"""
        section_frame = tk.Frame(parent, bg=self.colors['card_bg'], relief='solid', bd=2)
        section_frame.pack(fill='x', padx=10, pady=8)
        
        # Section title
        title_label = tk.Label(section_frame, text=title,
                              font=("Arial", 11, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'])
        title_label.pack(anchor='w', padx=15, pady=(10, 5))
        
        # Items
        for label, value in items:
            item_frame = tk.Frame(section_frame, bg=self.colors['card_bg'])
            item_frame.pack(fill='x', padx=15, pady=3)
            
            tk.Label(item_frame, text=label, font=("Arial", 9),
                    bg=self.colors['card_bg'], fg=self.colors['main_fg'], width=12, anchor='w').pack(side='left')
            tk.Label(item_frame, text=str(value), font=("Arial", 9, "bold"),
                    bg=self.colors['card_bg'], fg=self.colors['main_fg']).pack(side='left', padx=(5, 0))
    
    def create_checkmark_section(self, parent, title, items):
        """Create a section with checkmarks"""
        section_frame = tk.Frame(parent, bg=self.colors['card_bg'], relief='solid', bd=2)
        section_frame.pack(fill='x', padx=10, pady=8)
        
        # Section title
        title_label = tk.Label(section_frame, text=title,
                              font=("Arial", 11, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'])
        title_label.pack(anchor='w', padx=15, pady=(10, 5))
        
        # Items with checkmarks
        for item_text, checked in items:
            item_frame = tk.Frame(section_frame, bg=self.colors['card_bg'])
            item_frame.pack(fill='x', padx=15, pady=3)
            
            # Checkmark or empty
            if checked:
                checkmark = tk.Label(item_frame, text="✓", font=("Arial", 12, "bold"),
                                    bg=self.colors['card_bg'], fg=self.colors['success_green'], width=3)
            else:
                checkmark = tk.Label(item_frame, text="", font=("Arial", 12),
                                    bg=self.colors['card_bg'], width=3)
            checkmark.pack(side='left')
            
            # Item text
            tk.Label(item_frame, text=item_text, font=("Arial", 9),
                    bg=self.colors['card_bg'], fg=self.colors['main_fg']).pack(side='left', padx=(5, 0))
    
    def create_resources_section(self, parent):
        """Create resources section with clickable links"""
        section_frame = tk.Frame(parent, bg=self.colors['card_bg'], relief='solid', bd=2)
        section_frame.pack(fill='x', padx=10, pady=8)
        
        # Section title
        title_label = tk.Label(section_frame, text="Resources",
                              font=("Arial", 11, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['main_fg'])
        title_label.pack(anchor='w', padx=15, pady=(10, 5))
        
        # Resource links
        resources = [
            "Controller Manual",
            "Command Reference",
            "DMC Code Samples",
            "GDK Manual"
        ]
        
        for resource in resources:
            link_frame = tk.Frame(section_frame, bg=self.colors['card_bg'])
            link_frame.pack(fill='x', padx=15, pady=3)
            
            link_label = tk.Label(link_frame, text=resource,
                                 font=("Arial", 9, "underline"),
                                 bg=self.colors['card_bg'], fg='blue',
                                 cursor='hand2')
            link_label.pack(anchor='w')
            link_label.bind('<Button-1>', lambda e, r=resource: self.open_resource(r))
    
    def get_controller_info(self):
        """Get controller information from connected controller"""
        info = {
            'model': 'DMC4143',
            'revision': 'Unknown',
            'serial': 'Unknown',
            'axes': 4,
            'quadrature_supported': True,
            'brushless_supported': True,
            'brushed_supported': True
        }
        
        if not self.main_app or not self.main_app.controller:
            return info
        
        try:
            # Get firmware version (VE command - may not be supported on all controllers)
            try:
                ve_response = self.main_app.controller.send_command("VE")
                if ve_response and ve_response.strip() != '?' and '?' not in ve_response:
                    # Parse version string (e.g., "DMC4143 Ver 1.3k")
                    ve_text = ve_response.strip()
                    parts = ve_text.split()
                    if len(parts) >= 1:
                        # First part is usually the model
                        if parts[0].upper().startswith('DMC'):
                            info['model'] = parts[0]
                        # Look for revision pattern (e.g., "1.3k", "Ver 1.3k")
                        for i, part in enumerate(parts):
                            if part.lower() == 'ver' and i + 1 < len(parts):
                                info['revision'] = parts[i + 1]
                            elif any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
                                # Pattern like "1.3k"
                                info['revision'] = part
            except Exception as e:
                # VE command not supported or failed, use discovery info if available
                # Try to get model from connection info
                if hasattr(self.main_app, 'controller') and hasattr(self.main_app.controller, 'controller_info'):
                    conn_info = self.main_app.controller.controller_info
                    if conn_info and 'model' in conn_info:
                        info['model'] = conn_info['model']
                        info['revision'] = conn_info.get('revision', 'Unknown')
            
            # Get serial number (ID command - returns serial number)
            id_response = self.main_app.controller.send_command("ID")
            if id_response and not id_response.strip().startswith('?'):
                id_text = id_response.strip()
                # ID command can return multiple lines, extract serial number
                lines = [line.strip() for line in id_text.split('\n') if line.strip()]
                if lines:
                    # Serial number is typically on the first line or can be parsed
                    # Try to extract just the number
                    for line in lines:
                        # Look for a numeric serial
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            info['serial'] = numbers[-1]  # Take the last number found
                            break
                    # Fallback: use first line
                    if info['serial'] == 'Unknown' and lines:
                        info['serial'] = lines[0]
            
            # Query axis configuration to determine features
            # Check for brushless support (BA command)
            try:
                ba_response = self.main_app.controller.send_command("MG _BA")
                if ba_response and not ba_response.strip().startswith('?'):
                    # If BA returns a value, brushless is supported
                    pass
            except:
                pass
            
        except Exception as e:
            if self.main_app:
                self.main_app.append_test_log(f"Error getting controller info: {e}")
        
        return info
    
    def open_resource(self, resource):
        """Handle resource link click"""
        if self.main_app:
            self.main_app.append_test_log(f"Opening resource: {resource}")
        
        # Map resources to actions
        resource_map = {
            "Controller Manual": "https://www.galil.com/dmc-4143",
            "Command Reference": "https://www.galil.com/command-reference",
            "DMC Code Samples": "https://www.galil.com/dmc-code-samples",
            "GDK Manual": "https://www.galil.com/gdk"
        }
        
        url = resource_map.get(resource, "")
        if url:
            import webbrowser
            try:
                webbrowser.open(url)
            except:
                messagebox.showinfo("Resource", f"Resource: {resource}\n\nURL: {url}")
        else:
            messagebox.showinfo("Resource", f"Resource information for: {resource}")
    
    def go_back(self):
        """Go back to previous step"""
        self.on_close()
    
    def go_next(self):
        """Proceed to next step"""
        self.on_close()
    
    def on_close(self):
        """Handle dialog close"""
        if hasattr(self, 'dialog') and self.dialog.winfo_exists():
            self.dialog.destroy()

