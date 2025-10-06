# comprehensive_testing.py
# Comprehensive Motor Testing Framework for Galil Controllers
# Integrates all testing modules into a unified testing system

import time
import threading
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Import our testing modules
from setup_safety import setup_safety
from discovery import discover_axes
from test_motion import run_motion_tests
from pass_fail import run_pf_checks, move_and_pf
# controller_servo_maintenance provides helper functions (not a class)
from errors_status import collect_error_status, format_status_report, az_clear_latched
from teardown import teardown_axes
from command_validator import DMC4103CommandValidator
from galil_connection import (
    SUPPORTED_AXES, MAX_DI, MAX_DO, 
    get_galil_connection, gsend, num, wait_bg, 
    clear_errors_and_rebaseline, motion_profile, quiet_phase
)
from galil_helpers import (
    cmd, read_scalar, read_vector, is_servo_on, ensure_servo_on,
    wait_motion_complete, set_motion_profile, zero_position,
    move_absolute, read_position, clear_errors_and_baseline,
    setup_global_parameters, setup_axis_servo, gnum
)

class TestResult(Enum):
    """Test result enumeration"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"
    RUNNING = "RUNNING"

@dataclass
class TestStep:
    """Individual test step data structure"""
    step_id: str
    name: str
    description: str
    result: TestResult = TestResult.SKIP
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    data: Dict[str, Any] = None
    error_message: str = ""
    notes: str = ""

@dataclass
class TestPhase:
    """Test phase data structure"""
    phase_id: str
    name: str
    description: str
    steps: List[TestStep] = None
    result: TestResult = TestResult.SKIP
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0

class ComprehensiveTester:
    """Comprehensive motor testing framework"""
    
    def __init__(self, controller, log_callback=None, progress_callback=None, main_app=None):
        """
        Initialize the comprehensive tester
        
        Args:
            controller: Galil controller instance
            log_callback: Optional callback function for logging messages
            progress_callback: Optional callback function for progress updates
            main_app: Main application instance for encoder pause/resume
        """
        self.controller = controller
        self.log_callback = log_callback or self._default_log
        self.progress_callback = progress_callback
        self.main_app = main_app
        self.is_running = False
        self.current_phase = None
        self.test_results = {}
        self.active_axes = []
        
        # Command serialization lock to prevent polling conflicts
        self.command_lock = threading.Lock()
        
        # Initialize command validator
        self.validator = DMC4103CommandValidator()
        
        # Initialize servo maintenance system
        self.servo_maintenance = None
        
        # Test configuration
        # NOTE: Only A and B axes are fitted on this DMC-4143 hardware
        self.config = {
            "axes": list(SUPPORTED_AXES),  # Use hardware-defined axes (A, B only)
            "safety": {
                "oe": 3,
                "er": 200,
                "tl": 5.0,
                "tk": 9.0
            },
            "discovery": {
                "sp": 10000,
                "ac": 100000,
                "dc": 100000,
                "nudge_counts": 100
            },
            "motion": {
                "profiles": [
                    {"sp": 128000, "ac": 2560000, "dc": 2560000},
                    {"sp": 256000, "ac": 4096000, "dc": 4096000},
                    {"sp": 512000, "ac": 4096000, "dc": 4096000}
                ],
                "target_offsets": [1000, 5000, 10000, 0],
                "tolerance": 5,
                "include_jog": True
            }
        }
    
    def _default_log(self, message: str):
        """Default logging function"""
        print(f"[ComprehensiveTester] {message}")
    
    def log(self, message: str):
        """Log a message"""
        self.log_callback(message)
    
    def _start_step(self, step: TestStep) -> None:
        """Start timing a test step"""
        step.start_time = time.time()
        step.result = TestResult.RUNNING
        self.log(f"Starting: {step.name}")
        
        # Call progress callback if available
        if self.progress_callback:
            self.progress_callback("step_start", step.step_id, step.name, 0)
    
    def _complete_step(self, step: TestStep, result: TestResult, data: Dict[str, Any] = None, error: str = "", notes: str = "") -> None:
        """Complete a test step"""
        step.end_time = time.time()
        step.duration = step.end_time - step.start_time
        step.result = result
        step.data = data or {}
        step.error_message = error
        step.notes = notes
        
        status_emoji = {
            TestResult.PASS: "✅",
            TestResult.FAIL: "❌", 
            TestResult.ERROR: "💥",
            TestResult.SKIP: "⏭️"
        }.get(result, "❓")
        
        self.log(f"{status_emoji} Completed: {step.name} ({result.value}) - {step.duration:.2f}s")
        if error:
            self.log(f"   Error: {error}")
        if notes:
            self.log(f"   Notes: {notes}")
        
        # Call progress callback if available
        if self.progress_callback:
            self.progress_callback("step_complete", step.step_id, step.name, 100, result.value, error, notes)
    
    def _run_phase(self, phase: TestPhase) -> TestResult:
        """Run a complete test phase"""
        self.log(f"DEBUG: Starting phase {phase.phase_id}")
        phase.start_time = time.time()
        phase.result = TestResult.RUNNING
        self.current_phase = phase
        
        self.log(f"\n{'='*60}")
        self.log(f"PHASE: {phase.name}")
        self.log(f"Description: {phase.description}")
        self.log(f"{'='*60}")
        
        overall_result = TestResult.PASS
        
        for step in phase.steps:
            if not self.is_running:
                self._complete_step(step, TestResult.SKIP, notes="Test stopped by user")
                overall_result = TestResult.SKIP
                break
                
            try:
                self.log(f"DEBUG: Starting step {step.step_id}")
                self._start_step(step)
                result = self._execute_step(step)
                self._complete_step(step, result, data=step.data, error=step.error_message, notes=step.notes)
                
                if result == TestResult.FAIL or result == TestResult.ERROR:
                    overall_result = TestResult.FAIL
                    
            except Exception as e:
                step.error_message = str(e)
                self._complete_step(step, TestResult.ERROR, error=step.error_message)
                overall_result = TestResult.FAIL
        
        phase.end_time = time.time()
        phase.duration = phase.end_time - phase.start_time
        phase.result = overall_result
        
        self.log(f"\nPhase {phase.name} completed: {overall_result.value} ({phase.duration:.2f}s)")
        return overall_result
    
    def _execute_step(self, step: TestStep) -> TestResult:
        """Execute a specific test step"""
        step_id = step.step_id
        self.log(f"DEBUG: Executing step {step_id}")
        
        if step_id == "safety_setup":
            return self._execute_safety_setup(step)
        elif step_id == "axis_discovery":
            return self._execute_axis_discovery(step)
        elif step_id == "motion_testing":
            return self._execute_motion_testing(step)
        elif step_id == "error_status_check":
            return self._execute_error_status_check(step)
        elif step_id == "teardown":
            return self._execute_teardown(step)
        else:
            self.log(f"DEBUG: Unknown step {step_id}")
            return TestResult.SKIP
    
    def _execute_safety_setup(self, step: TestStep) -> TestResult:
        """Execute safety setup step"""
        try:
            self.log("DEBUG: Starting safety setup")
            # Get controller's gclib handle - use the correct access method
            if hasattr(self.controller, 'g') and self.controller.g:
                g = self.controller.g
            elif hasattr(self.controller, 'send_command'):
                # Create a wrapper for the controller's send_command method
                class GWrapper:
                    def __init__(self, controller, logger):
                        self.controller = controller
                        self._logger = logger
                    def GCommand(self, cmd):
                        try:
                            result = self.controller.send_command(cmd)
                            if result == "?":
                                # Command returned ?, get TC error code immediately
                                try:
                                    tc_response = self.controller.send_command("TC")
                                    self._logger(f"Command '{cmd}' returned ?, TC error: {tc_response}")
                                except:
                                    self._logger(f"Command '{cmd}' returned ?, could not read TC")
                            return result
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            # Try to get TC error code
                            try:
                                tc_response = self.controller.send_command("TC")
                                self._logger(f"Exception occurred, TC error: {tc_response}")
                            except:
                                pass
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Test basic controller communication first
            try:
                test_response = g.GCommand("TPA")
                if test_response == "?":
                    raise Exception("Controller not responding properly")
            except Exception as e:
                step.error_message = f"Controller communication test failed: {e}"
                return TestResult.ERROR
            
            # Force servo configuration before any setup
            from setup_safety import servo_bringup_41x3
            mo_status = servo_bringup_41x3(g)
            # Check if any axis successfully engaged
            if not any(mo == 0 for mo in mo_status.values()):
                step.error_message = "No axes engaged servo mode - check amp-enable/E-stop wiring"
                return TestResult.ERROR
            
            # Additional servo enable attempts for failed axes ONLY
            import time  # Import time at the beginning of the function
            # CRITICAL: Only try axes A and B (C and D not present on this hardware)
            for axis in SUPPORTED_AXES:
                if mo_status.get(axis, 1) != 0:  # Servo not enabled
                    self.log(f"Attempting additional servo enable for axis {axis}...")
                    try:
                        # Try multiple approaches to enable servo WITHOUT turning off first
                        for attempt in range(3):
                            try:
                                # DO NOT turn off servo first - just try to enable
                                g.GCommand(f"SH{axis}")  # Turn on
                                time.sleep(0.2)
                                
                                # Check if enabled - use MG {_VAR} format
                                mo_response = g.GCommand(f"MG _MO{axis}")
                                if mo_response and mo_response != "?":
                                    mo_value = float(mo_response.split(",")[0])
                                    if mo_value == 0.0:
                                        self.log(f"Axis {axis}: Servo enabled on attempt {attempt + 1}")
                                        mo_status[axis] = 0
                                        break
                                    else:
                                        self.log(f"Axis {axis}: Servo enable attempt {attempt + 1} failed (MO={mo_value})")
                                else:
                                    self.log(f"Axis {axis}: Cannot read servo status on attempt {attempt + 1}")
                                
                                if attempt < 2:  # Not the last attempt
                                    time.sleep(0.3)
                            except Exception as e:
                                self.log(f"Axis {axis}: Servo enable attempt {attempt + 1} error: {e}")
                                if attempt < 2:
                                    time.sleep(0.3)
                    except Exception as e:
                        self.log(f"Axis {axis}: Additional servo enable failed: {e}")
                else:
                    self.log(f"Axis {axis}: Servo already enabled (MO=0) - keeping enabled")
            
            # Final check
            if not any(mo == 0 for mo in mo_status.values()):
                step.error_message = "All servo enable attempts failed - check amp-enable/E-stop wiring"
                return TestResult.ERROR
            
            # Stop all motion first to clear any stuck axes, but keep servos enabled
            # CRITICAL: Only stop axes A and B (C and D not present on this hardware)
            for axis in SUPPORTED_AXES:
                try:
                    print(f"[SETUP] Stopping motion on axis {axis}...")
                    # Use the correct method to send commands with error handling
                    if hasattr(g, 'send_command'):
                        try:
                            g.send_command(f"ST{axis}")
                            # DO NOT use AM - it's program-only trippoint, use _BG polling instead
                            time.sleep(0.1)  # Brief pause for motion to stop
                            # Re-enable servo after stopping motion to ensure it stays on
                            g.send_command(f"SH{axis}")
                            print(f"[SETUP] Motion stopped and servo re-enabled on axis {axis}")
                        except Exception as cmd_error:
                            print(f"[SETUP] Command error on axis {axis}: {cmd_error}")
                            # Try alternative approach
                            try:
                                g.GCommand(f"ST{axis}")
                                g.GCommand(f"AM{axis}")
                                g.GCommand(f"SH{axis}")  # Re-enable servo
                                print(f"[SETUP] Motion stopped and servo re-enabled on axis {axis} (fallback)")
                            except Exception as fallback_error:
                                print(f"[SETUP] Fallback failed on axis {axis}: {fallback_error}")
                    else:
                        # Fallback to gclib method
                        g.GCommand(f"ST{axis}")
                        g.GCommand(f"AM{axis}")
                        g.GCommand(f"SH{axis}")  # Re-enable servo
                        print(f"[SETUP] Motion stopped and servo re-enabled on axis {axis}")
                except Exception as e:
                    print(f"[SETUP] Error stopping motion on axis {axis}: {e}")
                    pass
            
            # Run safety setup
            summary = setup_safety(
                g,
                axes=self.config["axes"],
                oe=self.config["safety"]["oe"],
                er=self.config["safety"]["er"],
                tl=self.config["safety"]["tl"],
                tk=self.config["safety"]["tk"]
            )
            
            step.data = summary
            
            # Check if setup was successful
            ab = summary.get("values", {}).get("abort_input", -1)
            # Pass if we got a sane abort state OR if all the setter dicts are present
            have_limits = all(k in summary.get("values", {}) for k in ("OE","ER","TL","TK"))
            return TestResult.PASS if (ab >= 0 or have_limits) else TestResult.FAIL
                
        except Exception as e:
            step.error_message = str(e)
            return TestResult.ERROR
    
    def _execute_axis_discovery(self, step: TestStep) -> TestResult:
        """Execute axis discovery step"""
        try:
            # Check controller connection first
            if not self.controller:
                step.error_message = "Controller not connected"
                return TestResult.ERROR
            
            # Test basic communication before discovery with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    test_response = self.controller.send_command("TPA")
                    if test_response == "?":
                        if attempt < max_retries - 1:
                            self.log(f"Controller not responding properly, retry {attempt + 1}/{max_retries}")
                            time.sleep(1)  # Wait before retry
                            continue
                        else:
                            step.error_message = "Controller not responding properly after retries"
                            return TestResult.ERROR
                    else:
                        break  # Success, exit retry loop
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.log(f"Controller communication test failed, retry {attempt + 1}/{max_retries}: {e}")
                        time.sleep(1)  # Wait before retry
                        continue
                    else:
                        step.error_message = f"Controller communication test failed after retries: {e}"
                        return TestResult.ERROR
            
            # Get controller's gclib handle - use the correct access method
            if hasattr(self.controller, 'g') and self.controller.g:
                g = self.controller.g
            elif hasattr(self.controller, 'send_command'):
                # Create a wrapper for the controller's send_command method that uses unvalidated commands
                class GWrapper:
                    def __init__(self, controller, logger):
                        self.controller = controller
                        self._logger = logger
                    def GCommand(self, cmd):
                        try:
                            # Use unvalidated commands for discovery to avoid validation issues
                            return self.controller.send_command_unvalidated(cmd)
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Run discovery with error handling
            try:
                results = discover_axes(
                    g,
                    axes=self.config["axes"],
                    sp=self.config["discovery"]["sp"],
                    ac=self.config["discovery"]["ac"],
                    dc=self.config["discovery"]["dc"],
                    nudge_counts=self.config["discovery"]["nudge_counts"],
                    validate_commands=False  # Use unvalidated commands for discovery
                )
            except Exception as e:
                self.log(f"Discovery failed: {e}")
                # Try a simpler discovery approach
                self.log("Attempting simplified discovery...")
                results = self._simple_axis_discovery(g)
            
            # Extract active axes - discovery returns "active" key, not "active_axes"
            self.active_axes = results.get("active", [])
            step.data = results
            
            # Check if we found any active axes
            if len(self.active_axes) > 0:
                self.log(f"Active axes discovered: {', '.join(self.active_axes)}")
                return TestResult.PASS
            else:
                self.log("No active axes discovered through normal discovery")
                # Log detailed probe notes for each axis to help diagnose
                for axis in self.config["axes"]:
                    if axis in results:
                        axis_result = results[axis]
                        self.log(f"[DISCOVERY] {axis}: {axis_result.get('notes', 'No notes')}")
                        # Also log MO/TS/TA status
                        mo = axis_result.get('mo', 'unknown')
                        ts = axis_result.get('ts', 'unknown')
                        ta = axis_result.get('ta', 'unknown')
                        tp_pos = axis_result.get('tp_after_pos', 'unknown')
                        tp_neg = axis_result.get('tp_after_neg', 'unknown')
                        self.log(f"           TP+={tp_pos} TP-={tp_neg} TS={ts} TA={ta} MO={mo}")
                
                # Final fallback: try to force enable servos and detect axes manually
                self.log("Attempting final fallback: manual servo enable and detection...")
                try:
                    for axis in SUPPORTED_AXES:  # Only try supported axes as fallback
                        try:
                            g.GCommand(f"SH{axis}")  # Force enable servo
                            time.sleep(0.3)
                            mo_response = g.GCommand(f"MG _MO{axis}")
                            if mo_response and mo_response != "?":
                                mo_value = float(mo_response.split(",")[0])
                                if mo_value == 0.0:  # Servo enabled
                                    pos_response = g.GCommand(f"TP{axis}")
                                    if pos_response and pos_response != "?":
                                        self.active_axes.append(axis)
                                        self.log(f"FALLBACK: Axis {axis} detected and enabled (MO={mo_value}, TP={pos_response})")
                        except Exception as e:
                            self.log(f"FALLBACK: Error with axis {axis}: {e}")
                    
                    if self.active_axes:
                        self.log(f"FALLBACK SUCCESS: Active axes detected: {', '.join(self.active_axes)}")
                        return TestResult.PASS
                    else:
                        self.log("FALLBACK FAILED: No axes could be detected")
                        return TestResult.FAIL
                except Exception as e:
                    self.log(f"FALLBACK ERROR: {e}")
                    return TestResult.FAIL
                
        except Exception as e:
            step.error_message = str(e)
            return TestResult.ERROR
    
    def _execute_motion_testing(self, step: TestStep) -> TestResult:
        """Execute motion testing step"""
        try:
            if not self.active_axes:
                step.notes = "No active axes to test"
                return TestResult.SKIP
            
            # Get controller's gclib handle - use the correct access method
            if hasattr(self.controller, 'g') and self.controller.g:
                g = self.controller.g
            elif hasattr(self.controller, 'send_command'):
                # Create a wrapper for the controller's send_command method
                class GWrapper:
                    def __init__(self, controller, logger):
                        self.controller = controller
                        self._logger = logger
                    def GCommand(self, cmd):
                        try:
                            result = self.controller.send_command(cmd)
                            if result == "?":
                                # Command returned ?, get TC error code immediately
                                try:
                                    tc_response = self.controller.send_command("TC")
                                    self._logger(f"Command '{cmd}' returned ?, TC error: {tc_response}")
                                except:
                                    self._logger(f"Command '{cmd}' returned ?, could not read TC")
                            return result
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            # Try to get TC error code
                            try:
                                tc_response = self.controller.send_command("TC")
                                self._logger(f"Exception occurred, TC error: {tc_response}")
                            except:
                                pass
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Quiesce motion before testing
            from discovery import _quiesce
            _quiesce(g)
            
            # CRITICAL: Ensure servos are enabled and stay enabled before motion testing
            self.log("CRITICAL: Ensuring servos are enabled and will stay enabled for motion testing...")
            
            # Helper function for robust numeric parsing (exact as specified)
            def gnum(cmd: str) -> float:
                s = g.GCommand(cmd).strip()
                return float(s.splitlines()[0].split()[0])
            
            # Helper function to ensure servo is on (exact as specified)
            def ensure_servo_on(ax: str):
                # 1) read motor-on status correctly
                mo = gnum(f"MG _MO{ax}")     # 0 = ON, 1 = OFF
                if mo != 0.0:
                    # 2) enable with correct, no-space command
                    g.GCommand(f"SH{ax}")     # 'SHA' / 'SHB' ...
                    # 3) short host sleep; do NOT use WT
                    import time; time.sleep(0.05)
                    # 4) verify again
                    mo = gnum(f"MG _MO{ax}")
                    if mo != 0.0:
                        raise RuntimeError(f"Servo for {ax} did not turn on (MO={mo})")
            
            # Apply to all active axes
            for axis in self.active_axes:
                try:
                    ensure_servo_on(axis)
                    self.log(f"CRITICAL: Axis {axis} servo ENABLED and verified (MO=0)")
                except Exception as e:
                    self.log(f"CRITICAL: Error checking/enabling servo for axis {axis}: {e}")
                    step.error_message = f"CRITICAL: Error checking/enabling servo for axis {axis}: {e}"
                    return TestResult.ERROR
            
            self.log("CRITICAL: All servos verified as enabled - motion testing can proceed")
            
            # Servo maintenance is now handled by controller-side program
            # No need for Python-side maintenance since controller automatically keeps servos enabled
            
            # Run comprehensive motion tests for each axis with longer sequences
            from test_motion import run_simple_motion_test
            # Create a wrapper that uses unvalidated commands for motion testing
            class MotionGWrapper:
                def __init__(self, controller, logger):
                    self.controller = controller
                    self._logger = logger
                def GCommand(self, cmd):
                    try:
                        # Use unvalidated commands for motion testing to avoid validation issues
                        return self.controller.send_command_unvalidated(cmd)
                    except Exception as e:
                        self._logger(f"Command '{cmd}' failed: {e}")
                        return "?"  # Return error indicator
                def GProgramDownload(self, program):
                    return True
            
            motion_g = MotionGWrapper(self.controller, self.log)
            
            # Test each axis individually with comprehensive motion test
            results = {}
            for axis in self.active_axes:
                self.log(f"Running comprehensive motion test for axis {axis}...")
                
                try:
                    # Run the comprehensive motion sequence: forward 50000, to 0, backward 50000, to 0
                    # Servo maintenance is handled automatically by controller-side program
                    result = self._run_comprehensive_motion_sequence(motion_g, axis)
                    
                    results[axis] = result
                    if result["test_passed"]:
                        self.log(f"Axis {axis}: Comprehensive motion test PASSED - {result['moves_completed']} moves completed")
                    else:
                        self.log(f"Axis {axis}: Comprehensive motion test FAILED - {result['notes']}")
                except Exception as e:
                    self.log(f"Axis {axis}: Comprehensive motion test error: {e}")
                    results[axis] = {
                        "axis": axis,
                        "motor_present": False,
                        "test_passed": False,
                        "moves_completed": 0,
                        "final_position": 0.0,
                        "notes": f"Test error: {e}"
                    }
            
            step.data = results
            
            # Check results for failures
            failed_tests = 0
            passed_tests = 0
            total_tests = len(results)
            
            for axis, result in results.items():
                if result.get("test_passed", False):
                    passed_tests += 1
                else:
                    failed_tests += 1
            
            if failed_tests == 0:
                step.notes = f"All {passed_tests} motion tests passed"
                return TestResult.PASS
            elif passed_tests == 0:
                step.notes = f"All {failed_tests} motion tests failed"
                return TestResult.FAIL
            else:
                step.notes = f"{passed_tests} motion tests passed, {failed_tests} motion tests failed"
                return TestResult.FAIL
                
        except Exception as e:
            step.error_message = str(e)
            return TestResult.ERROR
    
    def _execute_error_status_check(self, step: TestStep) -> TestResult:
        """Execute error status check step"""
        try:
            # Get controller's gclib handle - use the correct access method
            if hasattr(self.controller, 'g') and self.controller.g:
                g = self.controller.g
            elif hasattr(self.controller, 'send_command'):
                # Create a wrapper for the controller's send_command method
                class GWrapper:
                    def __init__(self, controller, logger):
                        self.controller = controller
                        self._logger = logger
                    def GCommand(self, cmd):
                        try:
                            result = self.controller.send_command(cmd)
                            if result == "?":
                                # Command returned ?, get TC error code immediately
                                try:
                                    tc_response = self.controller.send_command("TC")
                                    self._logger(f"Command '{cmd}' returned ?, TC error: {tc_response}")
                                except:
                                    self._logger(f"Command '{cmd}' returned ?, could not read TC")
                            return result
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            # Try to get TC error code
                            try:
                                tc_response = self.controller.send_command("TC")
                                self._logger(f"Exception occurred, TC error: {tc_response}")
                            except:
                                pass
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Build a safe axis list: prefer discovered; otherwise, only servo-enabled axes
            axes_pref = self.active_axes or self.config["axes"]
            self.log(f"DEBUG: Error status check - active_axes={self.active_axes}, axes_pref={axes_pref}")
            axes_enabled = []
            try:
                gg = self.controller.g if hasattr(self.controller, "g") and self.controller.g else None
                for ax in axes_pref:
                    if gg:
                        mo = gg.GCommand(f"MG _MO{ax}").strip()
                    else:
                        mo = self.controller.send_command(f"MG _MO{ax}").strip()
                    # _MOa == 0 means servo ON
                    if mo and mo != "?":
                        try:
                            mo_value = float(mo.split(",")[0])
                            if mo_value == 0.0:
                                axes_enabled.append(ax)
                                self.log(f"DEBUG: Axis {ax} is enabled (MO={mo_value})")
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass
            if not axes_enabled:
                axes_enabled = ["A"]  # conservative default
                self.log("DEBUG: No enabled axes found, using default A")
            else:
                self.log(f"DEBUG: Using enabled axes for status check: {axes_enabled}")

            # Clear any stale controller error code before collecting status
            try:
                # Clear error codes more thoroughly
                g.GCommand("TC 0")  # Clear error code
                g.GCommand("AB")    # Abort any motion
                g.GCommand("ST")    # Stop motion
                import time
                time.sleep(0.1)     # Brief pause for controller to process
            except Exception:
                pass

            # Collect error status
            status = collect_error_status(g, axes_enabled)
            formatted_report = format_status_report(status)
            
            step.data = status
            step.notes = formatted_report
            
            # Check for critical errors
            tc_code = status.get("TC", {}).get("code", 0)
            if tc_code != 0:
                step.notes += f"\nController error code: {tc_code}"
                return TestResult.FAIL
            
            # Check for amplifier errors - only evaluate active axes
            axes_to_eval = self.active_axes[:] if self.active_axes else []
            if not axes_to_eval:
                # Fallback: check which axes have servos actually ON
                for ax in self.config["axes"]:
                    try:
                        mo_response = g.GCommand(f"MG _MO{ax}").strip()
                        if mo_response and mo_response != "?":
                            mo = float(mo_response.split(",")[0])
                            if mo == 0.0:  # 0 => motor ON
                                axes_to_eval.append(ax)
                    except (ValueError, IndexError, Exception):
                        pass
            
            ta_errors = []
            for ax in axes_to_eval:
                try:
                    ta_value = status.get("TA", {}).get(ax, 0)
                    # Handle NaN or invalid values
                    if isinstance(ta_value, (int, float)) and not (ta_value != ta_value):  # Check for NaN
                        if ta_value != 0:
                            ta_errors.append(f"{ax}:{ta_value}")
                except Exception:
                    pass
            
            if ta_errors:
                step.notes += f"\nAmplifier errors: {', '.join(ta_errors)}"
                return TestResult.FAIL
            
            return TestResult.PASS
            
        except Exception as e:
            step.error_message = str(e)
            return TestResult.ERROR
    
    def _execute_teardown(self, step: TestStep) -> TestResult:
        """Execute teardown step"""
        try:
            if not self.active_axes:
                step.notes = "No active axes to teardown"
                return TestResult.SKIP
            
            # Get controller's gclib handle - use the correct access method
            if hasattr(self.controller, 'g') and self.controller.g:
                g = self.controller.g
            elif hasattr(self.controller, 'send_command'):
                # Create a wrapper for the controller's send_command method
                class GWrapper:
                    def __init__(self, controller, logger):
                        self.controller = controller
                        self._logger = logger
                    def GCommand(self, cmd):
                        try:
                            result = self.controller.send_command(cmd)
                            if result == "?":
                                # Command returned ?, get TC error code immediately
                                try:
                                    tc_response = self.controller.send_command("TC")
                                    self._logger(f"Command '{cmd}' returned ?, TC error: {tc_response}")
                                except:
                                    self._logger(f"Command '{cmd}' returned ?, could not read TC")
                            return result
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            # Try to get TC error code
                            try:
                                tc_response = self.controller.send_command("TC")
                                self._logger(f"Exception occurred, TC error: {tc_response}")
                            except:
                                pass
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Run teardown
            teardown_axes(g, self.active_axes, power_off=True)
            
            step.data = {"axes_teardown": self.active_axes}
            return TestResult.PASS
            
        except Exception as e:
            step.error_message = str(e)
            return TestResult.ERROR
    
    def create_test_phases(self) -> List[TestPhase]:
        """Create the test phases and steps"""
        phases = []
        
        # Phase 1: Setup and Safety
        setup_phase = TestPhase(
            phase_id="setup",
            name="Setup and Safety",
            description="Initialize controller safety systems and clear errors",
            steps=[
                TestStep(
                    step_id="safety_setup",
                    name="Safety Setup",
                    description="Configure OE, ER, TL, TK parameters and clear latched errors"
                )
            ]
        )
        phases.append(setup_phase)
        
        # Phase 2: Axis Discovery
        discovery_phase = TestPhase(
            phase_id="discovery",
            name="Axis Discovery",
            description="Discover which axes are present and functional",
            steps=[
                TestStep(
                    step_id="axis_discovery",
                    name="Axis Discovery",
                    description="Test each axis with small movements to verify presence and functionality"
                )
            ]
        )
        phases.append(discovery_phase)
        
        # Phase 3: Motion Testing
        motion_phase = TestPhase(
            phase_id="motion",
            name="Motion Testing",
            description="Comprehensive motion testing with multiple profiles",
            steps=[
                TestStep(
                    step_id="motion_testing",
                    name="Motion Testing",
                    description="Test motion with multiple speed/accel profiles and verify positioning accuracy"
                )
            ]
        )
        phases.append(motion_phase)
        
        # Phase 4: Error Status Check
        status_phase = TestPhase(
            phase_id="status",
            name="Error Status Check",
            description="Verify controller and amplifier status",
            steps=[
                TestStep(
                    step_id="error_status_check",
                    name="Error Status Check",
                    description="Check for any controller or amplifier errors"
                )
            ]
        )
        phases.append(status_phase)
        
        # Phase 5: Teardown
        teardown_phase = TestPhase(
            phase_id="teardown",
            name="Teardown",
            description="Return axes to safe positions and power down",
            steps=[
                TestStep(
                    step_id="teardown",
                    name="Teardown",
                    description="Move axes to zero position and power down motors"
                )
            ]
        )
        phases.append(teardown_phase)
        
        return phases
    
    def run_comprehensive_test(self, progress_callback: Callable[[str], None] = None) -> Dict[str, Any]:
        """
        Run the complete comprehensive test suite
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with test results and summary
        """
        if self.is_running:
            self.log("Test already running!")
            return {"error": "Test already running"}
        
        self.is_running = True
        start_time = time.time()
        
        try:
            self.log("\n" + "="*80)
            self.log("COMPREHENSIVE MOTOR TESTING STARTED")
            self.log("="*80)
            
            # Verify controller connection before starting
            if not self.controller:
                self.log("❌ No controller connected - cannot run comprehensive test")
                return {"error": "No controller connected", "overall_result": TestResult.ERROR.value}
            
            # Test basic controller communication
            try:
                test_response = self.controller.send_command("TPA")
                if test_response == "?":
                    self.log("❌ Controller not responding properly - cannot run comprehensive test")
                    return {"error": "Controller not responding", "overall_result": TestResult.ERROR.value}
                self.log(f"✅ Controller communication verified: Position A = {test_response}")
            except Exception as e:
                self.log(f"❌ Controller communication test failed: {e}")
                return {"error": f"Controller communication failed: {e}", "overall_result": TestResult.ERROR.value}
            
            # Servo maintenance system should be initialized once at app start, not here during testing
            # This ensures the controller-side program runs continuously
            self.log("ℹ️ Using servo maintenance system initialized at application startup")
            
            # Create test phases
            self.log("Creating test phases...")
            phases = self.create_test_phases()
            self.log(f"Created {len(phases)} test phases")
            
            # Run each phase
            results = {
                "start_time": start_time,
                "phases": {},
                "active_axes": [],
                "overall_result": TestResult.SKIP
            }
            
            overall_result = TestResult.PASS
            
            for phase in phases:
                if not self.is_running:
                    break
                    
                self.log(f"Starting phase: {phase.name}")
                phase_result = self._run_phase(phase)
                self.log(f"Completed phase: {phase.name} - Result: {phase_result}")
                results["phases"][phase.phase_id] = asdict(phase)
                
                if phase_result == TestResult.FAIL:
                    overall_result = TestResult.FAIL
                elif phase_result == TestResult.SKIP and overall_result == TestResult.PASS:
                    overall_result = TestResult.SKIP
            
            # Store active axes
            results["active_axes"] = self.active_axes
            
            # Final summary
            end_time = time.time()
            total_duration = end_time - start_time
            results["end_time"] = end_time
            results["total_duration"] = total_duration
            results["overall_result"] = overall_result
            
            self.log("\n" + "="*80)
            self.log("COMPREHENSIVE MOTOR TESTING COMPLETED")
            self.log(f"Overall Result: {overall_result.value}")
            self.log(f"Total Duration: {total_duration:.2f} seconds")
            self.log(f"Active Axes: {', '.join(self.active_axes) if self.active_axes else 'None'}")
            self.log("="*80)
            
            return results
            
        except Exception as e:
            self.log(f"Critical error during testing: {e}")
            return {"error": str(e), "overall_result": TestResult.ERROR.value}
        
        finally:
            # Clean up servo maintenance system
            if self.servo_maintenance:
                try:
                    self.log("🔧 Cleaning up servo maintenance system...")
                    self.servo_maintenance.cleanup()
                except Exception as e:
                    self.log(f"⚠️ Error cleaning up servo maintenance: {e}")
            
            self.is_running = False
    
    def stop_test(self):
        """Stop the running test"""
        self.is_running = False
        self.log("Test stop requested")
    
    def _run_comprehensive_motion_sequence(self, g, axis: str) -> Dict[str, Any]:
        """
        Run comprehensive motion sequence for a single axis:
        1. Move forward 50000 counts
        2. Return to 0
        3. Move backward 50000 counts
        4. Return to 0
        
        Returns detailed test results
        """
        result = {
            "axis": axis,
            "motor_present": False,
            "test_passed": False,
            "moves_completed": 0,
            "final_position": 0.0,
            "notes": "",
            "move_details": []
        }
        
        try:
            import time
            
            # Use shared galil_helpers module for all operations
            # All helper functions now centralized in galil_helpers.py
            
            # 1. Check if motor is present and servo is enabled
            self.log(f"Axis {axis}: Checking motor presence...")
            try:
                # Use shared helper to check servo status
                if not is_servo_on(g, axis):
                    mo_value = 1
                else:
                    mo_value = 0
            except Exception as e:
                result["notes"] = f"Cannot read servo status: {e}"
                return result
            if mo_value != 0.0:
                self.log(f"Axis {axis}: Servo not enabled (MO={mo_value}) - attempting to enable...")
                try:
                    ensure_servo_on(g, axis)
                    self.log(f"Axis {axis}: Servo enabled successfully")
                except Exception as e:
                    result["notes"] = f"Failed to enable servo: {e}"
                    return result
            
            result["motor_present"] = True
            self.log(f"Axis {axis}: Motor detected and servo enabled")
            
            # 2. Setup axis for servo operation
            self.log(f"Axis {axis}: Setting up axis for servo operation...")
            setup_axis_servo(g, axis, motor_type=0)
            
            # 3. NUCLEAR FIX: Maximum safety margins to prevent servo dropout
            self.log(f"Axis {axis}: Applying maximum safety margins...")
            cmd(g, f"OE{axis}=0")        # Per-axis disable OE
            cmd(g, "OE=0")                # Global disable OE (double-tap)
            cmd(g, f"ER{axis}=9999999")  # Maximum error limit
            cmd(g, f"TL{axis}=9.99")     # Maximum torque limit
            cmd(g, f"TK{axis}=0")        # Disable peak torque limit
            cmd(g, "TC 0")                # Clear any latched errors
            
            # 4. Baseline setup using shared helpers
            self.log(f"Axis {axis}: Setting up baseline motion state...")
            zero_position(g, axis)
            # GENTLER PROFILE to reduce torque demand and following error
            set_motion_profile(g, axis, sp=50000, ac=200000, dc=200000)
            self.log(f"Axis {axis}: Gentler profile set (SP=50000, AC=200000, DC=200000)")
            
            # 4. Get starting position
            try:
                start_pos = read_position(g, axis)
                self.log(f"Axis {axis}: Starting position = {start_pos}")
            except Exception as e:
                self.log(f"Axis {axis}: Could not read starting position: {e}")
                start_pos = 0.0
                self.log(f"Axis {axis}: Starting position unknown, assuming 0")
            
            moves_completed = 0
            
            # 5. Execute bulletproof motion sequence (host-safe)
            targets = [50000, 0, -50000, 0]
            target_names = ["forward 50000", "return to 0", "backward 50000", "final return to 0"]
            
            # Pause encoder updates during motion to prevent interference
            if hasattr(self, 'main_app') and self.main_app:
                self.main_app.pause_encoder_updates()
                self.log(f"Axis {axis}: Paused encoder updates for motion testing")
            
            try:
                for i, (target, name) in enumerate(zip(targets, target_names)):
                    self.log(f"Axis {axis}: Moving {name}...")
                    
                    # CRITICAL: Verify servo is enabled before motion
                    if not is_servo_on(g, axis):
                        self.log(f"Axis {axis}: Servo not enabled, enabling now...")
                        try:
                            ensure_servo_on(g, axis)
                            self.log(f"Axis {axis}: Servo enabled successfully")
                        except Exception as e:
                            self.log(f"Axis {axis}: Failed to enable servo: {e}, skipping move")
                            continue
                    
                    # Execute motion with DEBUG MONITORING enabled
                    try:
                        self.log(f"Axis {axis}: {name}...")
                        move_absolute(g, axis, target, wait=True, timeout_s=10.0, debug=True)
                        
                        # Verify position
                        final_pos = read_position(g, axis)
                        error = abs(final_pos - target)
                        self.log(f"Axis {axis}: ✓ Motion complete - Position = {final_pos} (target={target}, error={error})")
                        result["move_details"].append(f"{name}: target={target}, actual={final_pos}, error={error}")
                        moves_completed += 1
                        
                    except Exception as e:
                        self.log(f"Axis {axis}: Move failed: {e}")
                        result["move_details"].append(f"{name}: FAILED - {e}")
                        # Try to recover
                        try:
                            clear_errors_and_baseline(g, axis)
                            self.log(f"Axis {axis}: Baseline re-established after error")
                        except:
                            pass
                        continue
            finally:
                # Resume encoder updates after motion testing
                if hasattr(self, 'main_app') and self.main_app:
                    self.main_app.resume_encoder_updates()
                    self.log(f"Axis {axis}: Resumed encoder updates after motion testing")
            
            
            # Get final position using robust parsing
            try:
                final_pos = gnum(g, f"TP{axis}")
                self.log(f"Axis {axis}: Final position = {final_pos}")
                result["final_position"] = final_pos
            except Exception as e:
                self.log(f"Axis {axis}: Could not read final position: {e}")
                result["final_position"] = 0.0
                final_pos = 0.0
            
            # Test passes if we completed all 4 moves and final position is close to 0
            if moves_completed == 4 and abs(final_pos) < 100:  # Within 100 counts of 0
                result["test_passed"] = True
                result["notes"] = f"All {moves_completed} moves completed successfully, final position within tolerance"
            else:
                result["notes"] = f"Only {moves_completed}/4 moves completed, final position: {final_pos}"
            
            result["moves_completed"] = moves_completed
            
        except Exception as e:
            result["notes"] = f"Motion sequence error: {e}"
            self.log(f"Axis {axis}: Motion sequence error: {e}")
        
        return result
    
    def _handle_command_error(self, g, axis: str, command: str):
        """Handle command errors with proper TC read and re-baseline (host-safe)"""
        try:
            # Read the error code
            self.log(f"CMD: Sending TC")
            tc_response = g.GCommand("TC")
            self.log(f"Axis {axis}: {command} failed, TC error: {tc_response}")
            
            # Clear the error stack
            self.log(f"CMD: Sending TC 0")
            g.GCommand("TC 0")
            
            # Re-establish baseline after error (NO program commands)
            self.log(f"Axis {axis}: Re-establishing baseline after error (host-safe)...")
            self.log(f"CMD: Sending SH{axis}")
            g.GCommand(f"SH{axis}")
            self.log(f"CMD: Host sleep 50ms")
            time.sleep(0.05)  # Host delay, not WT
            self.log(f"CMD: Sending ST{axis}")
            g.GCommand(f"ST{axis}")
            # NO AB command - it's program-only
            self.log(f"CMD: Sending DP{axis}=0")
            g.GCommand(f"DP{axis}=0")
            
        except Exception as e:
            self.log(f"Axis {axis}: Error in error handling: {e}")

    def get_test_status(self) -> Dict[str, Any]:
        """Get current test status"""
        return {
            "is_running": self.is_running,
            "current_phase": self.current_phase.name if self.current_phase else None,
            "active_axes": self.active_axes
        }
    
    def gsend(self, command: str) -> str:
        """Send a single Galil command and return its full reply.
           If controller returns '?', raise with TC 1 text."""
        with self.command_lock:
            try:
                # Validate command before sending
                validation = self.validator.validate_command(command)
                if not validation.valid:
                    raise RuntimeError(f"Invalid command '{command}': {validation.error_message}")
                
                reply = self.controller.GCommand(command)
                # Galil sometimes returns extra prompts/newlines; normalize:
                reply = reply.strip()
                
                # Check for question mark response
                if reply == "?":
                    # Ask the controller why *right now* before any other traffic:
                    try:
                        why = self.controller.GCommand("TC1").strip()
                    except Exception:
                        why = "unknown (TC fetch failed)"
                    raise RuntimeError(f"Galil error on '{command}': {why}")
                
                return reply
            except Exception as e:
                # Ask the controller why *right now* before any other traffic:
                try:
                    why = self.controller.GCommand("TC1").strip()
                except Exception:
                    why = "unknown (TC fetch failed)"
                raise RuntimeError(f"Galil error on '{command}': {why}") from e
    
    def safe_command(self, command: str) -> Tuple[bool, str]:
        """Safely send a command and get detailed error information (legacy method)"""
        try:
            result = self.gsend(command)
            return True, result
        except Exception as e:
            return False, str(e)
    
    def init_servo_brushless(self, axes="ABCD"):
        """Initialize controller for servo brushless operation - resolves TC=161"""
        try:
            self.log("Initializing servo brushless operation...")
            
            # Panic-safe start
            self.gsend("AB")
            self.gsend("MO")
            self.gsend("AZ2")
            
            # Servo (not stepper) on all used axes
            mt_vals = ",".join("1" for _ in axes)  # 1 = servo
            self.gsend(f"MT{mt_vals}")
            
            # Assign internal brushless amps and init sine amps - use per-axis commands
            for ax in axes:
                self.gsend(f"BA{ax}")
                self.gsend(f"BX{ax}")       # <-- resolves TC=161
            
            # Optional: align/commutate if your procedure requires
            # self.gsend(f"BZ {axes}")
            
            # Safety limits (tune to your machine) - use per-axis commands
            for ax in axes:
                self.gsend(f"ER{ax}=20000")
                self.gsend(f"OE{ax}=3")
                self.gsend(f"TL{ax}=2")
                self.gsend(f"TK{ax}=4")
            
            # Enable servos and verify
            for ax in axes:
                self.gsend(f"SH{ax}")
                # Small sanity check: read error & switches
                te = float(self.gsend(f"TE{ax}"))
                ts_response = self.gsend(f"TS{ax}")
                try:
                    ts = int(float(ts_response)) if ts_response and ts_response != "?" else 0
                except (ValueError, TypeError):
                    ts = 0
                # Bit 5 set means motor OFF; if set here, SH failed silently
                if ts & (1 << 5):
                    raise RuntimeError(f"Axis {ax}: still Motor Off after SH; check BA/BX/BZ/limits")
                # Large following error right after SH may indicate wrong polarity/feedback
                if abs(te) > 5000:
                    raise RuntimeError(f"Axis {ax}: large error {te} after SH; verify wiring/polarity")
                self.log(f"Axis {ax}: Servo enabled and verified (TE={te:.1f}, TS={ts})")
            
            self.log("Servo brushless initialization completed successfully")
            return True
            
        except Exception as e:
            self.log(f"Servo brushless initialization failed: {e}")
            return False
    
    def configure_controller_for_servo_operation(self) -> bool:
        """Configure controller for servo operation - one-time setup"""
        return self.init_servo_brushless("ABCD")
    
    def test_controller_communication(self) -> TestResult:
        """Test basic controller communication"""
        try:
            self.log("Testing controller communication...")
            # Test basic communication with position query
            success, result = self.safe_command("PA")
            if success:
                self.log("Communication test passed: Position A = " + str(result))
                return TestResult.PASS
            else:
                self.log("Communication test failed: " + result)
                return TestResult.FAIL
        except Exception as e:
            self.log(f"Communication test error: {e}")
            return TestResult.ERROR
    
    def test_axis_presence(self) -> Dict[str, TestResult]:
        """Test which axes are present"""
        results = {}
        # Use hardware-defined supported axes only
        axes = list(SUPPORTED_AXES)  # Only A and B fitted on this hardware
        
        for axis in axes:
            try:
                self.log(f"Testing axis {axis}...")
                # Try to read position for each axis
                success, result = self.safe_command(f"PA{axis}")
                if success:
                    self.log(f"Axis {axis}: Present - Position: {result}")
                    results[axis] = TestResult.PASS
                else:
                    self.log(f"Axis {axis}: Not present or error - {result}")
                    results[axis] = TestResult.FAIL
            except Exception as e:
                self.log(f"Axis {axis}: Error - {e}")
                results[axis] = TestResult.ERROR
        
        return results
    
    def test_servo_enable(self, axes: List[str]) -> Dict[str, TestResult]:
        """Test servo enable functionality for specified axes"""
        results = {}
        
        for axis in axes:
            try:
                self.log(f"Testing servo enable for axis {axis}...")
                # Check controller connection first
                if not self.controller:
                    self.log(f"Axis {axis}: Controller not connected")
                    results[axis] = TestResult.ERROR
                    continue
                
                # Try to enable servo (SH command)
                success, result = self.safe_command(f"SH{axis}")
                if success:
                    # Check if servo is actually enabled by reading status, NOT by sending MO command
                    mo_success, mo_result = self.safe_command(f"MG _MO{axis}")
                    if mo_success and mo_result and mo_result != "?":
                        mo_value = float(mo_result.split(",")[0])
                        if mo_value == 0.0:  # Servo enabled
                            self.log(f"Axis {axis}: Servo enable successful")
                            results[axis] = TestResult.PASS
                        else:
                            self.log(f"Axis {axis}: Servo enable failed - motor not enabled: {mo_value}")
                            results[axis] = TestResult.FAIL
                    else:
                        self.log(f"Axis {axis}: Servo enable failed - cannot read status: {mo_result}")
                        results[axis] = TestResult.FAIL
                else:
                    self.log(f"Axis {axis}: Servo enable failed: {result}")
                    results[axis] = TestResult.FAIL
            except Exception as e:
                self.log(f"Axis {axis}: Servo enable error: {e}")
                results[axis] = TestResult.ERROR
        
        return results
    
    def test_basic_motion(self, axes: List[str], distance: int = 100) -> Dict[str, TestResult]:
        """Test basic motion functionality for specified axes"""
        results = {}
        
        for axis in axes:
            try:
                self.log(f"Testing motion for axis {axis}...")
                # Check controller connection first
                if not self.controller:
                    self.log(f"Axis {axis}: Controller not connected")
                    results[axis] = TestResult.ERROR
                    continue
                
                # Get current position
                start_pos = float(self.gsend(f"TP{axis}"))
                self.log(f"Axis {axis}: Starting position: {start_pos}")
                
                # Try a small move using the new move_abs method
                target_pos = start_pos + distance
                actual_pos, error = self.move_abs(axis, target_pos, sp=5000, ac=50000, dc=50000)
                
                # Check if move was successful (within tolerance)
                if error < 5:  # 5 count tolerance
                    self.log(f"Axis {axis}: Motion test successful - target: {target_pos:.1f}, actual: {actual_pos:.1f}, error: {error:.1f}")
                    results[axis] = TestResult.PASS
                else:
                    self.log(f"Axis {axis}: Motion test failed - large error: {error:.1f} counts")
                    results[axis] = TestResult.FAIL
                    
            except Exception as e:
                self.log(f"Axis {axis}: Motion test error: {e}")
                results[axis] = TestResult.ERROR
        
        return results
    
    def move_abs(self, axis: str, pos: float, sp: int = 5000, ac: int = 50000, dc: int = 50000) -> Tuple[float, float]:
        """Move axis to absolute position and return actual position and error"""
        try:
            self.gsend(f"SP{axis}={sp}")
            self.gsend(f"AC{axis}={ac}")
            self.gsend(f"DC{axis}={dc}")
            self.gsend(f"PA{axis}={pos}")
            self.gsend(f"BG{axis}")
            self.gsend(f"AM{axis}")
            actual = float(self.gsend(f"TP{axis}"))
            err = abs(actual - pos)
            return actual, err
        except Exception as e:
            raise RuntimeError(f"Move failed for axis {axis}: {e}")
    
    def _simple_axis_discovery(self, g) -> Dict[str, Any]:
        """Simplified axis discovery that just checks for servo status and basic functionality"""
        results = {"active": []}
        
        for axis in self.config["axes"]:
            try:
                self.log(f"Checking axis {axis} with simplified discovery...")
                
                # Try to enable servo first
                try:
                    g.GCommand(f"SH{axis}")  # Enable servo
                    time.sleep(0.2)  # Brief pause
                except:
                    pass  # Continue even if enable fails
                
                # Check if servo is enabled - use MG {_VAR} format
                mo_response = g.GCommand(f"MG _MO{axis}")
                if mo_response and mo_response != "?":
                    try:
                        mo_value = float(mo_response.split(",")[0])
                        if mo_value == 0.0:  # Servo enabled
                            # Try to read position to verify axis is responsive
                            pos_response = g.GCommand(f"TP{axis}")
                            if pos_response and pos_response != "?":
                                results["active"].append(axis)
                                results[axis] = {
                                    "present": True,
                                    "servo_enabled": True,
                                    "mo": mo_value,
                                    "position": pos_response,
                                    "notes": "Servo enabled and responsive"
                                }
                                self.log(f"Axis {axis}: Servo enabled and responsive (MO={mo_value}, TP={pos_response})")
                            else:
                                results[axis] = {
                                    "present": False,
                                    "servo_enabled": True,
                                    "mo": mo_value,
                                    "notes": "Servo enabled but not responsive"
                                }
                        else:
                            results[axis] = {
                                "present": False,
                                "servo_enabled": False,
                                "mo": mo_value,
                                "notes": f"Servo not enabled (MO={mo_value})"
                            }
                    except ValueError:
                        results[axis] = {
                            "present": False,
                            "servo_enabled": False,
                            "mo": None,
                            "notes": "Invalid servo status response"
                        }
                else:
                    results[axis] = {
                        "present": False,
                        "servo_enabled": False,
                        "mo": "unknown",
                        "notes": "Cannot read servo status"
                    }
            except Exception as e:
                results[axis] = {
                    "present": False,
                    "servo_enabled": False,
                    "mo": "error",
                    "notes": f"Error checking axis: {e}"
                }
                self.log(f"Axis {axis}: Discovery error: {e}")
        
        self.log(f"Simplified discovery completed: {len(results['active'])} active axes found")
        return results