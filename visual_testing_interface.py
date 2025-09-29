# visual_testing_interface.py
# Visual Testing Interface with Progress Bar and Real-time Updates

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from simple_motor_test import TestResult

# Import command validation utilities from command_validator.py
from command_validator import (
    DMC4103CommandValidator, 
    CommandValidation, 
    LoggingUtils,
    estimate_bm_from_movement,
    calculate_motion_parameters,
    validate_motion_parameters
)

class TestStatus(Enum):
    """Test status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class VisualTestStep:
    """Visual test step data structure"""
    step_id: str
    name: str
    description: str
    status: TestStatus = TestStatus.PENDING
    progress: float = 0.0
    details: str = ""
    error_message: str = ""

class VisualTestingInterface:
    """Visual testing interface with progress bar and real-time updates"""
    
    def __init__(self, parent_frame, colors, main_app):
        """
        Initialize the visual testing interface
        
        Args:
            parent_frame: Parent tkinter frame
            colors: Color scheme dictionary
            main_app: Reference to main application
        """
        self.parent_frame = parent_frame
        self.colors = colors
        self.main_app = main_app
        
        # Test state
        self.is_running = False
        self.current_step = None
        self.test_steps = []
        self.overall_progress = 0.0
        
        # Initialize command validator and logging utilities
        self.command_validator = DMC4103CommandValidator()
        self.logging_utils = LoggingUtils(log_callback=self.add_detail)
        
        # UI components
        self.main_frame = None
        self.progress_frame = None
        self.steps_frame = None
        self.details_frame = None
        
        # Progress components
        self.overall_progress_bar = None
        self.overall_progress_label = None
        self.current_step_label = None
        self.eta_label = None
        
        # Steps components
        self.step_widgets = {}
        
        # Details components
        self.details_text = None
        
        # Control buttons
        self.start_button = None
        self.stop_button = None
        self.reset_button = None
        
        self.create_interface()
    
    def create_interface(self):
        """Create the visual testing interface"""
        # Main frame
        self.main_frame = tk.Frame(self.parent_frame, bg=self.colors['main_bg'])
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(self.main_frame, text="🧪 Visual Motor Testing", 
                             font=("Arial", 18, "bold"),
                             bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        title_label.pack(pady=(0, 20))
        
        # Progress section
        self.create_progress_section()
        
        # Steps section
        self.create_steps_section()
        
        # Details section
        self.create_details_section()
        
        # Control buttons
        self.create_control_buttons()
    
    def create_progress_section(self):
        """Create the progress section"""
        # Progress frame
        self.progress_frame = tk.LabelFrame(self.main_frame, text="Test Progress", 
                                          font=("Arial", 12, "bold"),
                                          bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                          relief='solid', bd=1)
        self.progress_frame.pack(fill='x', pady=(0, 10))
        
        # Overall progress
        progress_content = tk.Frame(self.progress_frame, bg=self.colors['main_bg'])
        progress_content.pack(fill='x', padx=15, pady=15)
        
        # Overall progress bar
        self.overall_progress_bar = ttk.Progressbar(progress_content, 
                                                   mode='determinate',
                                                   length=400,
                                                   style="Custom.Horizontal.TProgressbar")
        self.overall_progress_bar.pack(fill='x', pady=(0, 10))
        
        # Progress labels
        labels_frame = tk.Frame(progress_content, bg=self.colors['main_bg'])
        labels_frame.pack(fill='x')
        
        self.overall_progress_label = tk.Label(labels_frame, text="Overall Progress: 0%", 
                                             font=("Arial", 10, "bold"),
                                             bg=self.colors['main_bg'], fg=self.colors['main_fg'])
        self.overall_progress_label.pack(side='left')
        
        self.eta_label = tk.Label(labels_frame, text="ETA: Calculating...", 
                                font=("Arial", 9),
                                bg=self.colors['main_bg'], fg=self.colors['secondary_fg'])
        self.eta_label.pack(side='right')
        
        # Current step label
        self.current_step_label = tk.Label(progress_content, text="Ready to start testing", 
                                         font=("Arial", 10),
                                         bg=self.colors['main_bg'], fg=self.colors['accent_blue'])
        self.current_step_label.pack(pady=(5, 0))
    
    def create_steps_section(self):
        """Create the steps section"""
        # Steps frame
        self.steps_frame = tk.LabelFrame(self.main_frame, text="Test Steps", 
                                       font=("Arial", 12, "bold"),
                                       bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                       relief='solid', bd=1)
        self.steps_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create scrollable frame for steps
        canvas = tk.Canvas(self.steps_frame, bg=self.colors['main_bg'], height=200)
        scrollbar = ttk.Scrollbar(self.steps_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['main_bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=15)
        scrollbar.pack(side="right", fill="y", pady=15)
        
        self.steps_content_frame = scrollable_frame
        
        # Initialize with default steps
        self.initialize_test_steps()
    
    def create_details_section(self):
        """Create the details section"""
        # Details frame
        self.details_frame = tk.LabelFrame(self.main_frame, text="Test Details", 
                                         font=("Arial", 12, "bold"),
                                         bg=self.colors['main_bg'], fg=self.colors['main_fg'],
                                         relief='solid', bd=1)
        self.details_frame.pack(fill='x', pady=(0, 10))
        
        # Details text area
        self.details_text = tk.Text(self.details_frame, height=6, font=("Consolas", 9),
                                   bg='white', fg='black', wrap=tk.WORD)
        self.details_text.pack(fill='x', padx=15, pady=15)
        
        # Add initial message
        self.details_text.insert(tk.END, "Ready to run comprehensive motor testing...\n")
        self.details_text.insert(tk.END, "Click 'Start Test' to begin the visual testing process.\n")
    
    def create_control_buttons(self):
        """Create control buttons"""
        # Buttons frame
        buttons_frame = tk.Frame(self.main_frame, bg=self.colors['main_bg'])
        buttons_frame.pack(fill='x', pady=(0, 10))
        
        # Start button
        self.start_button = tk.Button(buttons_frame, text="🚀 Start Test", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['success_green'], fg='white',
                                    command=self.start_test)
        self.start_button.pack(side='left', padx=(0, 10))
        
        # Stop button
        self.stop_button = tk.Button(buttons_frame, text="⏹ Stop Test", 
                                   font=("Arial", 12, "bold"),
                                   bg=self.colors['error_red'], fg='white',
                                   command=self.stop_test,
                                   state='disabled')
        self.stop_button.pack(side='left', padx=(0, 10))
        
        # Reset button
        self.reset_button = tk.Button(buttons_frame, text="🔄 Reset", 
                                    font=("Arial", 12, "bold"),
                                    bg=self.colors['warning_orange'], fg='white',
                                    command=self.reset_test)
        self.reset_button.pack(side='left')
        
        # Motion test button
        self.motion_test_button = tk.Button(buttons_frame, text="🏃 Motion Test", 
                                          font=("Arial", 12, "bold"),
                                          bg=self.colors['accent_blue'], fg='white',
                                          command=self.run_motion_test)
        self.motion_test_button.pack(side='left', padx=(10, 0))
    
    def initialize_test_steps(self):
        """Initialize the test steps"""
        self.test_steps = [
            VisualTestStep("setup", "Setup and Safety", "Initialize controller safety systems"),
            VisualTestStep("command_validation", "Command Validation", "Validate motor setup commands"),
            VisualTestStep("discovery", "Axis Discovery", "Discover which axes are present"),
            VisualTestStep("motion", "Motion Testing", "Test motion with multiple profiles"),
            VisualTestStep("status", "Error Status Check", "Verify controller status"),
            VisualTestStep("teardown", "Teardown", "Return axes to safe positions")
        ]
        
        self.create_step_widgets()
    
    def create_step_widgets(self):
        """Create widgets for each test step"""
        for i, step in enumerate(self.test_steps):
            step_frame = tk.Frame(self.steps_content_frame, bg=self.colors['main_bg'])
            step_frame.pack(fill='x', pady=2)
            
            # Status icon
            status_icon = tk.Label(step_frame, text="⏳", font=("Arial", 14),
                                 bg=self.colors['main_bg'], fg=self.colors['secondary_fg'])
            status_icon.pack(side='left', padx=(0, 10))
            
            # Step info
            info_frame = tk.Frame(step_frame, bg=self.colors['main_bg'])
            info_frame.pack(side='left', fill='x', expand=True)
            
            # Step name
            name_label = tk.Label(info_frame, text=step.name, 
                                font=("Arial", 10, "bold"),
                                bg=self.colors['main_bg'], fg=self.colors['main_fg'])
            name_label.pack(anchor='w')
            
            # Step description
            desc_label = tk.Label(info_frame, text=step.description, 
                                font=("Arial", 9),
                                bg=self.colors['main_bg'], fg=self.colors['secondary_fg'])
            desc_label.pack(anchor='w')
            
            # Progress bar for this step
            step_progress = ttk.Progressbar(info_frame, mode='determinate', length=200)
            step_progress.pack(anchor='w', pady=(2, 0))
            
            # Store widget references
            self.step_widgets[step.step_id] = {
                'frame': step_frame,
                'status_icon': status_icon,
                'name_label': name_label,
                'desc_label': desc_label,
                'progress_bar': step_progress
            }
    
    def update_step_status(self, step_id: str, status: TestStatus, progress: float = 0.0, details: str = ""):
        """Update the status of a specific test step"""
        if step_id not in self.step_widgets:
            return
        
        widgets = self.step_widgets[step_id]
        
        # Check if widgets still exist
        try:
            widgets['status_icon'].winfo_exists()
        except tk.TclError:
            # Widgets have been destroyed
            return
        
        # Update status icon and colors
        status_configs = {
            TestStatus.PENDING: ("⏳", self.colors['secondary_fg']),
            TestStatus.RUNNING: ("🔄", self.colors['accent_blue']),
            TestStatus.PASSED: ("✅", self.colors['success_green']),
            TestStatus.FAILED: ("❌", self.colors['error_red']),
            TestStatus.SKIPPED: ("⏭️", self.colors['warning_orange'])
        }
        
        icon, color = status_configs.get(status, ("❓", self.colors['secondary_fg']))
        widgets['status_icon'].config(text=icon, fg=color)
        
        # Update progress bar
        widgets['progress_bar']['value'] = progress
        
        # Update details
        if details:
            self.add_detail(f"{step_id.upper()}: {details}")
    
    def update_overall_progress(self, progress: float, current_step: str = "", eta: str = ""):
        """Update the overall progress"""
        try:
            self.overall_progress = progress
            self.overall_progress_bar['value'] = progress
            self.overall_progress_label.config(text=f"Overall Progress: {progress:.1f}%")
            
            if current_step:
                self.current_step_label.config(text=f"Current: {current_step}")
            
            if eta:
                self.eta_label.config(text=f"ETA: {eta}")
        except tk.TclError:
            # UI elements have been destroyed
            pass
    
    def add_detail(self, message: str):
        """Add a detail message to the details text area"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.details_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.details_text.see(tk.END)
        except tk.TclError:
            # UI elements have been destroyed
            pass
    
    def start_test(self):
        """Start the visual test"""
        if self.is_running:
            return
        
        # Check if UI elements still exist
        try:
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
        except tk.TclError:
            # UI elements have been destroyed, can't start test
            return
        
        self.is_running = True
        
        # Stop encoder updates to prevent conflicts during testing
        if hasattr(self.main_app, 'test_encoder_update_running'):
            self.main_app.test_encoder_update_running = False
        if hasattr(self.main_app, 'encoder_update_running'):
            self.main_app.encoder_update_running = False
        if hasattr(self.main_app, 'encoder_running'):
            self.main_app.encoder_running = False
        
        # Reset all steps
        for step in self.test_steps:
            step.status = TestStatus.PENDING
            step.progress = 0.0
            step.details = ""
            step.error_message = ""
        
        # Clear details
        self.details_text.delete(1.0, tk.END)
        self.add_detail("Starting comprehensive motor testing...")
        
        # Update UI
        self.update_overall_progress(0, "Initializing...")
        
        # Start test in background thread
        test_thread = threading.Thread(target=self._run_visual_test, daemon=True)
        test_thread.start()
    
    def stop_test(self):
        """Stop the visual test"""
        self.is_running = False
        self.add_detail("Test stop requested by user...")
        
        # Update UI
        if self.current_step:
            self.update_step_status(self.current_step, TestStatus.SKIPPED, 0, "Stopped by user")
        
        self.finish_test()
    
    def reset_test(self):
        """Reset the visual test"""
        if self.is_running:
            self.stop_test()
        
        # Reset all steps
        for step in self.test_steps:
            step.status = TestStatus.PENDING
            step.progress = 0.0
            step.details = ""
            step.error_message = ""
            self.update_step_status(step.step_id, TestStatus.PENDING, 0)
        
        # Reset progress
        self.update_overall_progress(0, "Ready to start testing")
    
    def run_motion_test(self):
        """Run a focused motion test to verify motors are working"""
        try:
            self.add_detail("🏃 Starting motion test...")
            self.add_detail("Setting up axis B for motion testing...")
            
            # Run the motion test
            success = self.main_app.run_visual_motion_test()
            
            if success:
                self.add_detail("✅ Motion test completed successfully!")
                self.add_detail("Both axes A and B should have moved visibly.")
            else:
                self.add_detail("❌ Motion test failed - check logs for details.")
                
        except Exception as e:
            self.add_detail(f"❌ Motion test error: {str(e)}")
        
        # Reset buttons
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
    
    def _run_visual_test(self):
        """Run the visual test in background thread"""
        try:
            # Initialize simple motor tester with progress callback
            if not hasattr(self.main_app, 'simple_motor_tester'):
                from simple_motor_test import SimpleMotorTester
                self.main_app.simple_motor_tester = SimpleMotorTester(
                    self.main_app.controller, 
                    self.add_detail,
                    self._progress_callback
                )
            
            # Run the test with visual updates
            results = self._run_test_with_visual_updates()
            
            # Update UI with final results
            self.main_app.root.after(0, self._handle_test_completion, results)
            
        except Exception as e:
            self.main_app.root.after(0, lambda: self.add_detail(f"Test failed: {e}"))
            self.main_app.root.after(0, self.finish_test)
    
    def _run_test_with_visual_updates(self):
        """Run test with visual progress updates using simple motor testing"""
        tester = self.main_app.simple_motor_tester
        
        # Define test phases
        phases = [
            ("communication", "Controller Communication", "Testing basic controller communication"),
            ("controller_config", "Controller Configuration", "Configuring controller for servo operation"),
            ("command_validation", "Command Validation", "Validating motor setup commands"),
            ("axis_presence", "Axis Discovery", "Discovering which axes are present"),
            ("servo_enable", "Servo Enable", "Testing servo enable functionality"),
            ("basic_motion", "Basic Motion", "Testing basic motion functionality")
        ]
        
        results = {}
        
        for i, (phase_id, phase_name, phase_desc) in enumerate(phases):
            if not self.is_running:
                return {"stopped": True}
            
            # Update visual progress for this phase
            phase_progress = (i / len(phases)) * 100
            self.main_app.root.after(0, lambda p=phase_progress, name=phase_name: 
                                   self.update_overall_progress(p, f"Starting {name}..."))
            
            # Update step status to running
            self.main_app.root.after(0, lambda pid=phase_id: 
                                   self.update_step_status(pid, TestStatus.RUNNING, 10, f"Starting {phase_name}..."))
            
            try:
                # Run the actual test phase
                if phase_id == "communication":
                    phase_result = tester.test_controller_communication()
                elif phase_id == "controller_config":
                    # Configure controller for servo operation
                    config_success = tester.configure_controller_for_servo_operation()
                    phase_result = TestResult.PASS if config_success else TestResult.FAIL
                elif phase_id == "command_validation":
                    # Validate common motor setup commands
                    common_commands = [
                        "MO A,B,C,D",  # Motor off
                        "SH A,B,C,D",  # Servo here (enable)
                        "AC A=1000,B=1000,C=1000,D=1000",  # Acceleration
                        "DC A=1000,B=1000,C=1000,D=1000",  # Deceleration
                        "SP A=5000,B=5000,C=5000,D=5000",  # Speed
                        "PA A=1000,B=1000,C=1000,D=1000",  # Position absolute
                        "BG A,B,C,D",  # Begin motion
                        "AM A,B,C,D"   # After motion
                    ]
                    validation_results = self.validate_motor_setup_commands(common_commands)
                    valid_count = sum(1 for result in validation_results if result.valid)
                    phase_result = TestResult.PASS if valid_count == len(common_commands) else TestResult.FAIL
                elif phase_id == "axis_presence":
                    axis_results = tester.test_axis_presence()
                    phase_result = TestResult.PASS if any(r == TestResult.PASS for r in axis_results.values()) else TestResult.FAIL
                elif phase_id == "servo_enable":
                    # Get active axes from previous test
                    active_axes = ["A", "B", "C", "D"]  # Default to all axes
                    servo_results = tester.test_servo_enable(active_axes)
                    phase_result = TestResult.PASS if any(r == TestResult.PASS for r in servo_results.values()) else TestResult.FAIL
                elif phase_id == "basic_motion":
                    # Get servo-capable axes from previous test
                    active_axes = ["A", "B", "C", "D"]  # Default to all axes
                    motion_results = tester.test_basic_motion(active_axes)
                    phase_result = TestResult.PASS if any(r == TestResult.PASS for r in motion_results.values()) else TestResult.FAIL
                else:
                    phase_result = TestResult.SKIP
                
                results[phase_id] = phase_result
                
                # Update visual status based on result
                if phase_result == TestResult.PASS:
                    self.main_app.root.after(0, lambda pid=phase_id: 
                                           self.update_step_status(pid, TestStatus.PASSED, 100, f"{phase_name} completed successfully"))
                elif phase_result == TestResult.FAIL:
                    self.main_app.root.after(0, lambda pid=phase_id: 
                                           self.update_step_status(pid, TestStatus.FAILED, 100, f"{phase_name} failed"))
                else:
                    self.main_app.root.after(0, lambda pid=phase_id: 
                                           self.update_step_status(pid, TestStatus.SKIPPED, 100, f"{phase_name} skipped"))
                
                # Update overall progress
                overall_progress = ((i + 1) / len(phases)) * 100
                self.main_app.root.after(0, lambda p=overall_progress: 
                                       self.update_overall_progress(p, f"{phase_name} completed"))
                
            except Exception as e:
                self.main_app.root.after(0, lambda pid=phase_id, error=str(e): 
                                       self.update_step_status(pid, TestStatus.FAILED, 100, f"Error: {error}"))
                results[phase_id] = {"error": str(e)}
        
        return results
    
    def _run_real_phase(self, phase, tester):
        """Run a real comprehensive testing phase with visual updates"""
        try:
            # Update progress during phase execution
            for i, step in enumerate(phase.steps):
                if not self.is_running:
                    return "SKIP"
                
                # Update step progress
                step_progress = (i / len(phase.steps)) * 80 + 10  # 10-90% range for step progress
                self.main_app.root.after(0, lambda p=step_progress, step_name=step.name: 
                                       self.update_step_status(phase.phase_id, TestStatus.RUNNING, p, f"Running: {step_name}"))
                
                # Add detail about current step
                self.main_app.root.after(0, lambda step_name=step.name: 
                                       self.add_detail(f"{phase.name.upper()}: {step_name}"))
                
                # Execute the actual step
                try:
                    result = tester._execute_step(step)
                    
                    # Add step result to details
                    if result.value == "PASS":
                        self.main_app.root.after(0, lambda step_name=step.name: 
                                               self.add_detail(f"{phase.name.upper()}: {step_name} - PASSED"))
                    elif result.value == "FAIL":
                        self.main_app.root.after(0, lambda step_name=step.name: 
                                               self.add_detail(f"{phase.name.upper()}: {step_name} - FAILED"))
                    else:
                        self.main_app.root.after(0, lambda step_name=step.name: 
                                               self.add_detail(f"{phase.name.upper()}: {step_name} - {result.value}"))
                    
                except Exception as e:
                    self.main_app.root.after(0, lambda step_name=step.name, error=str(e): 
                                           self.add_detail(f"{phase.name.upper()}: {step_name} - ERROR: {error}"))
            
            # Determine overall phase result
            if any(step.result.value == "FAIL" for step in phase.steps):
                return "FAIL"
            elif any(step.result.value == "PASS" for step in phase.steps):
                return "PASS"
            else:
                return "SKIP"
                
        except Exception as e:
            self.main_app.root.after(0, lambda error=str(e): 
                                   self.add_detail(f"{phase.name.upper()}: Phase error - {error}"))
            return "FAIL"
    
    def _update_phase_progress(self, phase_id: str, message: str):
        """Update phase progress"""
        self.current_step = phase_id
        self.update_step_status(phase_id, TestStatus.RUNNING, 50, message)
        
        # Calculate overall progress
        phase_index = next(i for i, step in enumerate(self.test_steps) if step.step_id == phase_id)
        overall_progress = (phase_index * 20) + 10  # 20% per phase, 10% for current phase start
        self.update_overall_progress(overall_progress, message)
    
    
    def _handle_test_completion(self, results):
        """Handle test completion"""
        if "stopped" in results:
            self.add_detail("Test stopped by user")
        else:
            # Calculate overall result
            passed_steps = sum(1 for result in results.values() if isinstance(result, dict) and result.get("result") == "PASS")
            total_steps = len(results)
            
            if passed_steps == total_steps:
                self.add_detail("🎉 All tests PASSED! Motor system is ready.")
                self.update_overall_progress(100, "Test completed successfully", "Complete")
            else:
                self.add_detail(f"⚠️ {passed_steps}/{total_steps} tests passed. Review results.")
                self.update_overall_progress(100, "Test completed with issues", "Complete")
        
        self.finish_test()
    
    def finish_test(self):
        """Finish the test and update UI"""
        self.is_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        # Restart encoder updates after testing is complete
        if hasattr(self.main_app, 'start_encoder_update'):
            self.main_app.start_encoder_update()
        
        self.add_detail("Test completed.")
    
    def validate_test_command(self, command: str) -> CommandValidation:
        """Validate a command using the DMC4103 command validator"""
        try:
            validation_result = self.command_validator.validate_command(command)
            if not validation_result.valid:
                self.logging_utils.log_error(f"Invalid command '{command}': {validation_result.error_message}")
            elif validation_result.warning_message:
                self.logging_utils.log_info(f"Command warning for '{command}': {validation_result.warning_message}")
            return validation_result
        except Exception as e:
            self.logging_utils.log_error(f"Command validation error for '{command}': {str(e)}")
            return CommandValidation(valid=False, command=command, description="", error_message=str(e))
    
    def validate_motor_setup_commands(self, commands: List[str]) -> List[CommandValidation]:
        """Validate a sequence of motor setup commands"""
        self.logging_utils.log_info(f"Validating {len(commands)} motor setup commands...")
        try:
            validation_results = self.command_validator.validate_motor_setup_sequence(commands)
            
            # Log validation results
            valid_count = sum(1 for result in validation_results if result.valid)
            self.logging_utils.log_info(f"Command validation complete: {valid_count}/{len(commands)} commands valid")
            
            for result in validation_results:
                if not result.valid:
                    self.logging_utils.log_error(f"Invalid command: {result.command} - {result.error_message}")
                elif result.warning_message:
                    self.logging_utils.log_info(f"Command warning: {result.command} - {result.warning_message}")
            
            return validation_results
        except Exception as e:
            self.logging_utils.log_error(f"Command sequence validation error: {str(e)}")
            return []
    
    def calculate_motion_params(self, speed: float, acceleration: float, deceleration: float) -> Dict[str, float]:
        """Calculate motion parameters using utility functions"""
        try:
            params = calculate_motion_parameters(speed, acceleration, deceleration)
            if validate_motion_parameters(params):
                self.logging_utils.log_success(f"Motion parameters calculated: Speed={params['speed']}, Accel={params['acceleration']}, Decel={params['deceleration']}")
            else:
                self.logging_utils.log_error("Invalid motion parameters calculated")
            return params
        except Exception as e:
            self.logging_utils.log_error(f"Motion parameter calculation error: {str(e)}")
            return {'speed': 1.0, 'acceleration': 1.0, 'deceleration': 1.0}
    
    def estimate_backlash_compensation(self, positions: List[float], total_movement: float) -> float:
        """Estimate backlash compensation using utility functions"""
        try:
            bm_estimate = estimate_bm_from_movement(positions, total_movement)
            self.logging_utils.log_info(f"Estimated backlash compensation (BM): {bm_estimate:.2f}%")
            return bm_estimate
        except Exception as e:
            self.logging_utils.log_error(f"Backlash compensation estimation error: {str(e)}")
            return 0.0

    def _progress_callback(self, event_type, step_id=None, step_name=None, progress=0, result=None, error=None, notes=None):
        """Handle progress callbacks from comprehensive testing"""
        if event_type == "step_start":
            # Update step to running
            self.main_app.root.after(0, lambda: self.update_step_status(step_id, TestStatus.RUNNING, progress, f"Starting {step_name}..."))
            self.main_app.root.after(0, lambda: self.add_detail(f"{step_name.upper()}: Starting {step_name}..."))
            
        elif event_type == "step_complete":
            # Update step completion
            if result == "PASS":
                status = TestStatus.PASSED
                self.main_app.root.after(0, lambda: self.add_detail(f"{step_name.upper()}: {step_name} - PASSED"))
            elif result == "FAIL":
                status = TestStatus.FAILED
                self.main_app.root.after(0, lambda: self.add_detail(f"{step_name.upper()}: {step_name} - FAILED"))
            else:
                status = TestStatus.SKIPPED
                self.main_app.root.after(0, lambda: self.add_detail(f"{step_name.upper()}: {step_name} - {result}"))
            
            self.main_app.root.after(0, lambda: self.update_step_status(step_id, status, progress, f"{step_name} completed"))
            
            if error:
                self.main_app.root.after(0, lambda: self.add_detail(f"{step_name.upper()}: Error - {error}"))
            if notes:
                self.main_app.root.after(0, lambda: self.add_detail(f"{step_name.upper()}: Notes - {notes}"))
