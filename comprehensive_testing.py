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
from errors_status import collect_error_status, format_status_report, az_clear_latched
from teardown import teardown_axes
from command_validator import DMC4103CommandValidator

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
    
    def __init__(self, controller, log_callback=None, progress_callback=None):
        """
        Initialize the comprehensive tester
        
        Args:
            controller: Galil controller instance
            log_callback: Optional callback function for logging messages
            progress_callback: Optional callback function for progress updates
        """
        self.controller = controller
        self.log_callback = log_callback or self._default_log
        self.progress_callback = progress_callback
        self.is_running = False
        self.current_phase = None
        self.test_results = {}
        self.active_axes = []
        
        # Command serialization lock to prevent polling conflicts
        self.command_lock = threading.Lock()
        
        # Initialize command validator
        self.validator = DMC4103CommandValidator()
        
        # Test configuration
        self.config = {
            "axes": ["A", "B", "C", "D"],
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
                            return self.controller.send_command(cmd)
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
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
            
            # Stop all motion first to clear any stuck axes
            for axis in ["A", "B", "C", "D"]:
                try:
                    print(f"[SETUP] Stopping motion on axis {axis}...")
                    # Use the correct method to send commands with error handling
                    if hasattr(g, 'send_command'):
                        try:
                            g.send_command(f"ST{axis}")
                            g.send_command(f"AM{axis}")
                            print(f"[SETUP] Motion stopped on axis {axis}")
                        except Exception as cmd_error:
                            print(f"[SETUP] Command error on axis {axis}: {cmd_error}")
                            # Try alternative approach
                            try:
                                g.GCommand(f"ST{axis}")
                                g.GCommand(f"AM{axis}")
                                print(f"[SETUP] Motion stopped on axis {axis} (fallback)")
                            except Exception as fallback_error:
                                print(f"[SETUP] Fallback failed on axis {axis}: {fallback_error}")
                    else:
                        # Fallback to gclib method
                        g.GCommand(f"ST{axis}")
                        g.GCommand(f"AM{axis}")
                        print(f"[SETUP] Motion stopped on axis {axis}")
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
                            return self.controller.send_command(cmd)
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Connection should be stable from previous phases
            
            # Run discovery
            results = discover_axes(
                g,
                axes=self.config["axes"],
                sp=self.config["discovery"]["sp"],
                ac=self.config["discovery"]["ac"],
                dc=self.config["discovery"]["dc"],
                nudge_counts=self.config["discovery"]["nudge_counts"]
            )
            
            # Extract active axes - discovery returns "active" key, not "active_axes"
            self.active_axes = results.get("active", [])
            step.data = results
            
            # Check if we found any active axes
            if len(self.active_axes) > 0:
                self.log(f"Active axes discovered: {', '.join(self.active_axes)}")
                return TestResult.PASS
            else:
                self.log("No active axes discovered")
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
                            return self.controller.send_command(cmd)
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
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
            
            # Run comprehensive individual axis tests
            from test_motion import run_comprehensive_individual_axis_tests
            results = run_comprehensive_individual_axis_tests(
                g,
                axes=self.active_axes,
                test_speeds=[1000, 2000, 5000],  # Test at 3 different speeds
                test_duration_seconds=5,  # 5 seconds per direction per speed
                movement_distance=10000  # Maximum movement distance
            )
            
            step.data = results
            
            # Check results for failures
            failed_tests = 0
            total_tests = 0
            skipped_tests = 0
            
            for axis, axis_results in results.items():
                if axis == "active_axes":
                    continue
                    
                for test_result in axis_results:
                    test_type = test_result.get("test_type", "")
                    
                    # Skip motor detection tests - these are not motion tests
                    if test_type == "motor_detection":
                        skipped_tests += 1
                        continue
                        
                    total_tests += 1
                    if not test_result.get("pass", False):
                        failed_tests += 1
            
            if failed_tests == 0:
                if total_tests == 0:
                    step.notes = f"No motion tests to run (all axes skipped: {skipped_tests} axes without motors)"
                    return TestResult.SKIP
                else:
                    return TestResult.PASS
            else:
                step.notes = f"{failed_tests}/{total_tests} motion tests failed ({skipped_tests} axes skipped - no motors)"
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
                            return self.controller.send_command(cmd)
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
                            return "?"  # Return error indicator
                    def GProgramDownload(self, program):
                        # For now, just return success - program download would need controller-specific implementation
                        return True
                g = GWrapper(self.controller, self.log)
            else:
                raise Exception("Cannot access controller gclib interface")
            
            # Build a safe axis list: prefer discovered; otherwise, only servo-enabled axes
            axes_pref = self.active_axes or self.config["axes"]
            axes_enabled = []
            try:
                gg = self.controller.g if hasattr(self.controller, "g") and self.controller.g else None
                for ax in axes_pref:
                    if gg:
                        mo = gg.GCommand(f"MG _MO{ax}").strip()
                    else:
                        mo = self.controller.send_command(f"MG _MO{ax}").strip()
                    # _MOa == 0 means servo ON
                    if mo and float(mo.split(",")[0]) == 0.0:
                        axes_enabled.append(ax)
            except Exception:
                pass
            if not axes_enabled:
                axes_enabled = ["A"]  # conservative default

            # Clear any stale controller error code before collecting status
            try:
                g.GCommand("TC0")
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
                        mo = float(g.GCommand(f"MG _MO{ax}").strip().split(",")[0])
                        if mo == 0.0:  # 0 => motor ON
                            axes_to_eval.append(ax)
                    except Exception:
                        pass
            
            ta_errors = []
            for ax in axes_to_eval:
                ta_value = status.get("TA", {}).get(ax, 0)
                if ta_value != 0:
                    ta_errors.append(f"{ax}:{ta_value}")
            
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
                            return self.controller.send_command(cmd)
                        except Exception as e:
                            self._logger(f"Command '{cmd}' failed: {e}")
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
            self.is_running = False
    
    def stop_test(self):
        """Stop the running test"""
        self.is_running = False
        self.log("Test stop requested")
    
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
                ts = int(float(self.gsend(f"TS{ax}")))
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
        axes = ["A", "B", "C", "D"]
        
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
                # Try to enable servo (SH command)
                success, result = self.safe_command(f"SH{axis}")
                if success:
                    # Check if servo is actually enabled
                    mo_success, mo_result = self.safe_command(f"MO{axis}")
                    if mo_success:
                        self.log(f"Axis {axis}: Servo enable successful")
                        results[axis] = TestResult.PASS
                    else:
                        self.log(f"Axis {axis}: Servo enable failed - motor not enabled: {mo_result}")
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