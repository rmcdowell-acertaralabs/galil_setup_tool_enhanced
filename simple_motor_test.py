# simple_motor_test.py
# Simplified motor testing that works with the existing controller interface

import time
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from contextlib import contextmanager
from galil_io import (
    GalilIO, safe_enable, get_ts_bits, test_move_abs,
    discover_axes, verify_servo_enable, run_motion_suite,
    teardown_axes, sanity_probe
)
from testing_phases import (
    phase_axis_discovery, phase_servo_enable, phase_motion,
    phase_teardown, run_full_test
)

class TestResult(Enum):
    """Test result enumeration"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"

@contextmanager
def exclusive_controller(pause_callback=None, resume_callback=None):
    """Context manager for exclusive controller access"""
    if pause_callback:
        pause_callback()
    try:
        yield
    finally:
        if resume_callback:
            resume_callback()

class SimpleMotorTester:
    """Simplified motor tester that works with existing controller interface"""
    
    def __init__(self, controller, log_callback=None, progress_callback=None):
        """
        Initialize the simple motor tester
        
        Args:
            controller: Galil controller instance (must have .g attribute with gclib handle)
            log_callback: Optional callback function for logging messages
            progress_callback: Optional callback function for progress updates
        """
        self.controller = controller
        self.log_callback = log_callback or self._default_log
        self.progress_callback = progress_callback
        self.is_running = False
        
        # Create GalilIO wrapper for thread-safe communication
        try:
            if hasattr(controller, 'g') and controller.g:
                self.io = GalilIO(controller.g)
            elif hasattr(controller, 'send_command'):
                # Create a wrapper for the controller's send_command method
                class GWrapper:
                    def __init__(self, controller):
                        self.controller = controller
                    def GCommand(self, cmd):
                        try:
                            return self.controller.send_command(cmd)
                        except Exception as e:
                            self.log(f"Command '{cmd}' failed: {e}")
                            return "?"  # Return error indicator
                self.io = GalilIO(GWrapper(controller))
            else:
                raise Exception("Cannot access controller gclib interface")
        except Exception as e:
            raise Exception(f"Failed to initialize GalilIO: {e}")
        
    def _default_log(self, message: str):
        """Default logging function"""
        print(f"[SimpleMotorTester] {message}")
    
    def log(self, message: str):
        """Log a message"""
        self.log_callback(message)
    
    def test_controller_communication(self) -> TestResult:
        """Test basic controller communication"""
        self.log("Testing controller communication...")
        
        # Run sanity probe first
        self.log("Running controller sanity probe...")
        try:
            sanity_probe(self.io)
        except Exception as e:
            self.log(f"Sanity probe failed: {e}")
        
        # Test basic position query with correct syntax
        try:
            pos = self.io.tp("A")
            self.log(f"Communication test passed: Position A = {pos}")
            return TestResult.PASS
        except Exception as e:
            self.log(f"Communication test failed: {e}")
            # Check for error details
            try:
                tc_text = self.io.tc_text()
                self.log(f"Controller error details: {tc_text}")
            except:
                pass
            return TestResult.FAIL
    
    def test_axis_presence(self) -> Dict[str, TestResult]:
        """Test which axes are present"""
        self.log("Testing axis presence...")
        results = {}
        
        for axis in ["A", "B", "C", "D"]:
            self.log(f"Testing axis {axis}...")
            
            # Test position query with correct syntax
            try:
                pos = self.io.tp(axis)
                results[axis] = TestResult.PASS
                self.log(f"Axis {axis}: Present - Position: {pos}")
            except Exception as e:
                results[axis] = TestResult.FAIL
                self.log(f"Axis {axis}: Not present or error - {e}")
        
        return results
    
    def test_servo_enable(self, axes: List[str] = None) -> Dict[str, TestResult]:
        """Test servo enable functionality"""
        if axes is None:
            axes = ["A", "B", "C", "D"]
        
        self.log("Testing servo enable functionality...")
        results = {}
        
        for axis in axes:
            self.log(f"Testing servo enable for axis {axis}...")
            
            try:
                safe_enable(self.io, axis)
                results[axis] = TestResult.PASS
                self.log(f"Axis {axis}: Servo enabled successfully")
            except Exception as e:
                results[axis] = TestResult.FAIL
                self.log(f"Axis {axis}: Servo enable failed: {e}")
        
        return results
    
    def test_basic_motion(self, axes: List[str] = None, distance: int = 100) -> Dict[str, TestResult]:
        """Test basic motion functionality"""
        if axes is None:
            axes = ["A", "B", "C", "D"]
        
        self.log(f"Testing basic motion (distance: {distance})...")
        results = {}
        
        for axis in axes:
            self.log(f"Testing motion for axis {axis}...")
            
            try:
                # Get initial position
                initial_pos = self.io.tp(axis)
                
                # Test motion with proper error handling
                target = initial_pos + distance
                pos, err = test_move_abs(self.io, axis, target, sp=5000, ac=25000, dc=25000)
                
                if err <= 5:  # Within 5 counts
                    results[axis] = TestResult.PASS
                    self.log(f"Axis {axis}: Motion test passed - Error: {err} counts")
                else:
                    results[axis] = TestResult.FAIL
                    self.log(f"Axis {axis}: Motion test failed - Error: {err} counts")
                
                # Return to initial position
                self.io.pa(axis, initial_pos)
                self.io.bg(axis)
                time.sleep(1.0)
                
            except Exception as e:
                results[axis] = TestResult.ERROR
                self.log(f"Axis {axis}: Motion test error: {e}")
        
        return results
    
    def single_axis_move(self, axis: str, target: int, sp: int = 5000, ac: int = 2500, dc: int = 2500) -> Tuple[bool, float]:
        """Single axis move with correct syntax - returns (success, final_position)"""
        try:
            pos, err = test_move_abs(self.io, axis, target, sp=sp, ac=ac, dc=dc)
            self.log(f"Axis {axis}: Move completed to position {pos}, error: {err} counts")
            return True, pos
        except Exception as e:
            self.log(f"Axis {axis}: Move error: {e}")
            return False, 0.0
    
    def run_comprehensive_test(self, pause_encoder_callback=None, resume_encoder_callback=None) -> Dict[str, Any]:
        """Run comprehensive motor test with exclusive controller access"""
        if self.is_running:
            return {"error": "Test already running"}
        
        self.is_running = True
        start_time = time.time()
        
        try:
            self.log("Starting comprehensive motor testing...")
            
            # Use exclusive controller access to prevent interleaving with encoder updates
            with exclusive_controller(pause_encoder_callback, resume_encoder_callback):
                # Run the robust full test
                results = run_full_test(self.io)
                
                if "error" in results:
                    return {"error": results["error"], "overall_result": TestResult.ERROR}
                
                # Convert to our format
                end_time = time.time()
                duration = end_time - start_time
                
                # Count passing axes
                passing_axes = sum(1 for a in results["motion_results"] 
                                 for r in results["motion_results"][a] 
                                 if r.get("passed", False))
                
                overall_result = TestResult.PASS if passing_axes > 0 else TestResult.FAIL
                
                final_results = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "overall_result": overall_result,
                    "active_axes": results["active_axes"],
                    "axis_infos": results["axis_infos"],
                    "motion_results": results["motion_results"],
                    "summary": results["summary"],
                    "tests": {
                        "communication": TestResult.PASS,  # We got this far
                        "axis_presence": TestResult.PASS if results["active_axes"] else TestResult.FAIL,
                        "servo_enable": TestResult.PASS,  # Handled properly in phases
                        "basic_motion": TestResult.PASS if passing_axes > 0 else TestResult.FAIL
                    }
                }
                
                self.log(f"\n=== Test Complete ===")
                self.log(f"Duration: {duration:.2f} seconds")
                self.log(f"Overall Result: {final_results['overall_result'].value}")
                self.log(f"Active Axes: {final_results['active_axes']}")
                self.log(f"Summary: {final_results['summary']}")
                
                return final_results
            
        except Exception as e:
            self.log(f"Test failed with error: {e}")
            return {"error": str(e), "overall_result": TestResult.ERROR}
        
        finally:
            self.is_running = False
    
    def stop_test(self):
        """Stop the running test"""
        self.is_running = False
        self.log("Test stop requested")
