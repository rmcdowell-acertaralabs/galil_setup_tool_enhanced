# demo_visual_testing.py
# Demo script to show the visual testing interface

import tkinter as tk
from tkinter import ttk
import time
import threading

# Mock controller class for demo
class MockController:
    def send_command(self, cmd):
        # Simulate some command responses
        if cmd == "TP A":
            return "1000"
        elif cmd == "TP B":
            return "2000"
        elif cmd == "TP C":
            return "3000"
        elif cmd == "TP D":
            return "4000"
        elif cmd.startswith("SH"):
            return ""
        elif cmd.startswith("TP"):
            return "1000"
        else:
            return "OK"

# Mock main app class for demo
class MockMainApp:
    def __init__(self):
        self.controller = MockController()
        self.comprehensive_tester = None
        self.root = tk.Tk()
    
    def show_visual_testing(self):
        pass

def run_demo():
    """Run the visual testing demo"""
    root = tk.Tk()
    root.title("Visual Motor Testing Demo")
    root.geometry("1000x700")
    root.configure(bg='#f5f5f5')
    
    # Mock colors
    colors = {
        'main_bg': '#f5f5f5',
        'main_fg': '#2c3e50',
        'secondary_fg': '#7f8c8d',
        'accent_blue': '#3498db',
        'success_green': '#27ae60',
        'warning_orange': '#f39c12',
        'error_red': '#e74c3c',
    }
    
    # Mock main app
    main_app = MockMainApp()
    main_app.root = root
    
    # Create visual testing interface
    from visual_testing_interface import VisualTestingInterface
    
    # Create main frame
    main_frame = tk.Frame(root, bg=colors['main_bg'])
    main_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Create visual testing interface
    visual_interface = VisualTestingInterface(main_frame, colors, main_app)
    
    # Add demo info
    demo_label = tk.Label(main_frame, 
                         text="🎬 This is a DEMO of the Visual Motor Testing Interface\n"
                              "The actual testing would connect to a real Galil controller\n"
                              "and perform comprehensive motor testing with real-time progress.",
                         font=("Arial", 12),
                         bg=colors['main_bg'], fg=colors['secondary_fg'],
                         justify='center')
    demo_label.pack(pady=(20, 0))
    
    root.mainloop()

if __name__ == "__main__":
    run_demo()
