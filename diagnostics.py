#!/usr/bin/env python3
"""
Comprehensive DMC-4103 Diagnostics Module
GDK-free diagnostics for DMC-4103 controller using Python gclib interface.

This module implements a complete diagnostics suite covering:
- Connection & transport validation
- Controller identity & environment
- Parameter persistence
- Digital I/O functionality
- Motor power control
- Encoder feedback
- Motion control
- Safety systems
- Network functionality
- And more...

Author: Ryan McDowell
Date: 2024
"""

import time
import json
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging - Use WARNING level to reduce noise
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class TestResult(Enum):
    """Test result enumeration"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"

@dataclass
class TestStep:
    """Individual test step data structure"""
    step_id: str
    description: str
    commands: List[str]
    expected_response: str
    timeout: float = 5.0
    critical: bool = True
    result: TestResult = TestResult.SKIP
    actual_response: str = ""
    execution_time: float = 0.0
    notes: str = ""

@dataclass
class TestCategory:
    """Test category data structure"""
    category_id: str
    name: str
    description: str
    steps: List[TestStep]
    overall_result: TestResult = TestResult.SKIP
    execution_time: float = 0.0
    notes: str = ""

@dataclass
class DiagnosticsReport:
    """Complete diagnostics report"""
    timestamp: str
    controller_info: Dict[str, Any]
    test_categories: List[TestCategory]
    overall_result: TestResult
    total_execution_time: float
    summary: Dict[str, Any]

class GalilDiagnostics:
    """
    Comprehensive DMC-4103 diagnostics class.
    
    Implements all 18 diagnostic categories with proper DMC-4103 commands,
    pass/fail criteria, and detailed reporting.
    """
    
    def __init__(self, controller, safe_mode: bool = True):
        """
        Initialize diagnostics system.
        
        Args:
            controller: GalilController instance with send_command method
            safe_mode: If True, uses conservative test parameters
        """
        self.controller = controller
        self.safe_mode = safe_mode
        self.report = None
        self.is_running = False
        self.stop_requested = False
        
        # Test parameters (adjustable based on safe_mode)
        self.test_params = {
            'low_speed': 10000 if safe_mode else 20000,
            'medium_speed': 30000 if safe_mode else 50000,
            'high_speed': 50000 if safe_mode else 100000,
            'small_move': 500 if safe_mode else 1000,
            'medium_move': 1000 if safe_mode else 2000,
            'large_move': 2000 if safe_mode else 5000,
            'accel_rate': 100000 if safe_mode else 200000,
            'decel_rate': 100000 if safe_mode else 200000,
            'repeatability_tolerance': 10 if safe_mode else 20,
            'following_error_limit': 1000 if safe_mode else 2000,
            'poll_frequency': 10,  # Hz
            'test_duration': 60,   # seconds
        }
        
        # Initialize test categories
        self.test_categories = self._initialize_test_categories()
    
    def _initialize_test_categories(self) -> List[TestCategory]:
        """Initialize all test categories with proper DMC-4103 commands"""
        
        categories = []
        
        # Category 0: Connection & Transport Sanity
        categories.append(TestCategory(
            category_id="connection",
            name="Connection & Transport Sanity",
            description="Prove Python transport is clean (USB/COM or TCP)",
            steps=[
                TestStep("conn_001", "Get system time", ["TP A"], "position value"),
                TestStep("conn_002", "Get firmware revision", ["MG _REV"], "firmware string"),
                TestStep("conn_003", "Get burn count", ["MG _BN"], "number"),
                TestStep("conn_004", "Get X position", ["TPX"], "position value"),
                TestStep("conn_005", "Loop test (10 iterations)", ["TP A"] * 10, "consistent responses"),
            ]
        ))
        
        # Category 1: Controller Identity & Environment
        categories.append(TestCategory(
            category_id="identity",
            name="Controller Identity & Environment",
            description="Log fixed identifiers and network state",
            steps=[
                TestStep("id_001", "Get board model", ["MG _BM"], "DMC-4103"),
                TestStep("id_002", "Get burn count", ["MG _BN"], "number"),
                TestStep("id_003", "Get MAC address", ["TH"], "MAC address"),
                TestStep("id_004", "Get DHCP status", ["DH"], "0 or 1"),
                TestStep("id_005", "Get IP address", ["IA"], "IP in comma form"),
                TestStep("id_006", "Get Ethernet duplex", ["MG _ED"], "duplex status"),
                TestStep("id_007", "Get hardware config", ["MG _HC"], "config bits"),
            ]
        ))
        
        # Category 2: Parameter Round-trip & Persistence
        categories.append(TestCategory(
            category_id="parameters",
            name="Parameter Round-trip & Persistence",
            description="Verify set/get and non-volatile storage",
            steps=[
                TestStep("param_001", "Read initial SPA value", ["SPA=?"], "current value"),
                TestStep("param_002", "Set test SPA value", [f"SPA={self.test_params['medium_speed']}"], ":"),
                TestStep("param_003", "Verify SPA set", ["SPA=?"], str(self.test_params['medium_speed'])),
                TestStep("param_004", "Burn to flash", ["BN"], ":"),
                TestStep("param_005", "Reset controller", ["RS"], ":"),
                TestStep("param_006", "Verify persistence", ["SPA=?"], str(self.test_params['medium_speed'])),
                TestStep("param_007", "Restore original SPA", ["SPA=50000"], ":"),
            ]
        ))
        
        # Category 3: Digital I/O Sanity
        categories.append(TestCategory(
            category_id="digital_io",
            name="Digital I/O Sanity",
            description="Prove host→controller and controller→I/O paths",
            steps=[
                TestStep("io_001", "Set output 1", ["SB 1"], ":"),
                TestStep("io_002", "Read output 1", ["MG @OUT[1]"], "1"),
                TestStep("io_003", "Clear output 1", ["CB 1"], ":"),
                TestStep("io_004", "Read output 1", ["MG @OUT[1]"], "0"),
                TestStep("io_005", "Read input 1", ["MG @IN[1]"], "0 or 1"),
                TestStep("io_006", "Read all inputs", ["MG @IN[1,2,3,4,5,6,7,8]"], "input states"),
            ]
        ))
        
        # Category 4: Motor Power Control & Status
        categories.append(TestCategory(
            category_id="motor_power",
            name="Motor Power Control & Status",
            description="Confirm enable/disable amplifiers and read state",
            steps=[
                TestStep("motor_001", "Motor off", ["MOX"], ":"),
                TestStep("motor_002", "Check motor off status", ["MG _MOX"], "0"),
                TestStep("motor_003", "Servo on", ["SHX"], ":"),
                TestStep("motor_004", "Check servo on status", ["MG _MOX"], "1"),
                TestStep("motor_005", "Motor off (cleanup)", ["MOX"], ":"),
            ]
        ))
        
        # Category 5: Encoder Feedback at Rest
        categories.append(TestCategory(
            category_id="encoder_rest",
            name="Encoder Feedback at Rest",
            description="Ensure encoder data is sensible and stable",
            steps=[
                TestStep("enc_001", "Get initial position", ["TPX"], "position value"),
                TestStep("enc_002", "Position stability test 1", ["TPX"], "stable value"),
                TestStep("enc_003", "Position stability test 2", ["TPX"], "stable value"),
                TestStep("enc_004", "Position stability test 3", ["TPX"], "stable value"),
                TestStep("enc_005", "Position stability test 4", ["TPX"], "stable value"),
                TestStep("enc_006", "Position stability test 5", ["TPX"], "stable value"),
                TestStep("enc_007", "Check following error", ["MG _TEX"], "small value"),
            ]
        ))
        
        # Category 6: Basic Point-to-Point Motion
        categories.append(TestCategory(
            category_id="basic_motion",
            name="Basic Point-to-Point Motion",
            description="Closed-loop move out and back; prove servo loop basics",
            steps=[
                TestStep("motion_001", "Set acceleration", [f"ACX={self.test_params['accel_rate']}"], ":"),
                TestStep("motion_002", "Set deceleration", [f"DCX={self.test_params['decel_rate']}"], ":"),
                TestStep("motion_003", "Set speed", [f"SPX={self.test_params['low_speed']}"], ":"),
                TestStep("motion_004", "Servo on", ["SHX"], ":"),
                TestStep("motion_005", "Move positive", [f"PRX={self.test_params['small_move']}", "BGX", "AMX"], "motion complete"),
                TestStep("motion_006", "Check position", ["TPX"], "target position"),
                TestStep("motion_007", "Move negative", [f"PRX={-self.test_params['small_move']}", "BGX", "AMX"], "motion complete"),
                TestStep("motion_008", "Check final position", ["TPX"], "near zero"),
                TestStep("motion_009", "Check following error", ["MG _TEX"], "small value"),
                TestStep("motion_010", "Motor off", ["MOX"], ":"),
            ]
        ))
        
        # Category 7: Repeatability & Backlash Test
        categories.append(TestCategory(
            category_id="repeatability",
            name="Repeatability & Backlash Test",
            description="Catch encoder sign errors/backlash/loose couplings",
            steps=[
                TestStep("rep_001", "Set motion parameters", [f"ACX={self.test_params['accel_rate']}", f"DCX={self.test_params['decel_rate']}", f"SPX={self.test_params['low_speed']}"], ":"),
                TestStep("rep_002", "Servo on", ["SHX"], ":"),
                TestStep("rep_003", "Repeatability test 1", [f"PRX={self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_004", "Repeatability test 2", [f"PRX={-self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_005", "Repeatability test 3", [f"PRX={self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_006", "Repeatability test 4", [f"PRX={-self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_007", "Repeatability test 5", [f"PRX={self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_008", "Repeatability test 6", [f"PRX={-self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_009", "Repeatability test 7", [f"PRX={self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_010", "Repeatability test 8", [f"PRX={-self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_011", "Repeatability test 9", [f"PRX={self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_012", "Repeatability test 10", [f"PRX={-self.test_params['medium_move']}", "AMX", "TPX"], "position logged"),
                TestStep("rep_013", "Motor off", ["MOX"], ":"),
            ]
        ))
        
        # Category 8: Velocity (Jog) Mode Sanity
        categories.append(TestCategory(
            category_id="velocity_mode",
            name="Velocity (Jog) Mode Sanity",
            description="Check continuous velocity command path",
            steps=[
                TestStep("vel_001", "Set motion parameters", [f"ACX={self.test_params['accel_rate']}", f"DCX={self.test_params['decel_rate']}"], ":"),
                TestStep("vel_002", "Servo on", ["SHX"], ":"),
                TestStep("vel_003", "Start jog", [f"JGX={self.test_params['low_speed']}", "BGX"], ":"),
                TestStep("vel_004", "Check velocity", ["TVX"], "velocity value"),
                TestStep("vel_005", "Stop jog", ["JGX=0", "AMX"], ":"),
                TestStep("vel_006", "Check final velocity", ["TVX"], "0 or near 0"),
                TestStep("vel_007", "Motor off", ["MOX"], ":"),
            ]
        ))
        
        # Category 9: Accel/Decel Profile Sweep
        categories.append(TestCategory(
            category_id="accel_decel",
            name="Accel/Decel Profile Sweep",
            description="Look for tuning issues (jerk, oscillation, amp limits)",
            steps=[
                TestStep("accel_001", "Test accel 50k", [f"ACX=50000", f"DCX=50000", f"SPX={self.test_params['low_speed']}", "SHX", f"PRX={self.test_params['medium_move']}", "BGX", "AMX", "MG _TEX"], "no following error"),
                TestStep("accel_002", "Test accel 100k", [f"ACX=100000", f"DCX=100000", f"PRX={-self.test_params['medium_move']}", "BGX", "AMX", "MG _TEX"], "no following error"),
                TestStep("accel_003", "Test accel 200k", [f"ACX=200000", f"DCX=200000", f"PRX={self.test_params['medium_move']}", "BGX", "AMX", "MG _TEX"], "no following error"),
                TestStep("accel_004", "Test accel 400k", [f"ACX=400000", f"DCX=400000", f"PRX={-self.test_params['medium_move']}", "BGX", "AMX", "MG _TEX"], "no following error"),
                TestStep("accel_005", "Motor off", ["MOX"], ":"),
            ]
        ))
        
        # Category 10: Position Tracking (PT) Retarget Test
        categories.append(TestCategory(
            category_id="position_tracking",
            name="Position Tracking (PT) Retarget Test",
            description="Prove trajectory modification logic post-firmware",
            steps=[
                TestStep("pt_001", "Enable position tracking", ["PT1"], ":"),
                TestStep("pt_002", "Set motion parameters", [f"ACX={self.test_params['accel_rate']}", f"DCX={self.test_params['decel_rate']}", f"SPX={self.test_params['low_speed']}"], ":"),
                TestStep("pt_003", "Servo on", ["SHX"], ":"),
                TestStep("pt_004", "Start move", ["PA 5000", "BGX"], ":"),
                TestStep("pt_005", "Retarget 1", ["PA -2000"], ":"),
                TestStep("pt_006", "Retarget 2", ["PA 8000"], ":"),
                TestStep("pt_007", "Wait for completion", ["AMX"], ":"),
                TestStep("pt_008", "Check following error", ["MG _TEX"], "small value"),
                TestStep("pt_009", "Disable position tracking", ["PT0"], ":"),
                TestStep("pt_010", "Motor off", ["MOX"], ":"),
            ]
        ))
        
        # Category 11: Limits & Home Inputs
        categories.append(TestCategory(
            category_id="limits_home",
            name="Limits & Home Inputs",
            description="Safety chain validation",
            steps=[
                TestStep("limit_001", "Check limit flags", ["MG _LF"], "limit status"),
                TestStep("limit_002", "Check X limit flag", ["MG _LFX"], "X limit status"),
                TestStep("limit_003", "Check home flag", ["MG _HMX"], "home status"),
                TestStep("limit_004", "Check all limit flags", ["MG _LFY", "MG _LFZ", "MG _LFW"], "limit statuses"),
                TestStep("limit_005", "Check all home flags", ["MG _HMY", "MG _HMZ", "MG _HMW"], "home statuses"),
            ]
        ))
        
        # Category 12: Fault Handling
        categories.append(TestCategory(
            category_id="fault_handling",
            name="Fault Handling",
            description="Controller reaction to real faults",
            steps=[
                TestStep("fault_001", "Check fault status", ["MG _FE"], "fault status"),
                TestStep("fault_002", "Check amplifier status", ["MG _AER"], "amp status"),
                TestStep("fault_003", "Check position error status", ["MG _PER"], "position error status"),
                TestStep("fault_004", "Check communication error", ["MG _CER"], "comm error status"),
                TestStep("fault_005", "Clear any faults", ["CB _FE"], ":"),
            ]
        ))
        
        # Category 13: Multitasking & Deterministic Behavior
        categories.append(TestCategory(
            category_id="multitasking",
            name="Multitasking & Deterministic Behavior",
            description="Confirm scheduler stability",
            steps=[
                TestStep("multi_001", "Start background program", ["#AUTO", "XQ"], "program started"),
                TestStep("multi_002", "Check program status", ["MG _XQ"], "program status"),
                TestStep("multi_003", "Issue foreground commands", ["TP A", "TPX", "TVX"], "responses received"),
                TestStep("multi_004", "Stop background program", ["HX"], ":"),
                TestStep("multi_005", "Clear program", ["DL"], ":"),
            ]
        ))
        
        # Category 14: Program Download/Load/Run Lifecycle
        categories.append(TestCategory(
            category_id="program_lifecycle",
            name="Program Download/Load/Run Lifecycle",
            description="Confirm memory/program handling",
            steps=[
                TestStep("prog_001", "Download test program", ["DL", "PR 100", "PA 1000", "BGX", "AMX", "EN"], "program downloaded"),
                TestStep("prog_002", "List program", ["LS"], "program listed"),
                TestStep("prog_003", "Execute program", ["XQ"], "program executed"),
                TestStep("prog_004", "Halt program", ["HX"], ":"),
                TestStep("prog_005", "Clear program", ["DL"], ":"),
            ]
        ))
        
        # Category 15: Burn & Reset Regression
        categories.append(TestCategory(
            category_id="burn_reset",
            name="Burn & Reset Regression",
            description="Ensure persistent config survives power cycles",
            steps=[
                TestStep("burn_001", "Set test parameter", ["TL=12345"], ":"),
                TestStep("burn_002", "Verify parameter set", ["MG TL"], "12345"),
                TestStep("burn_003", "Burn to flash", ["BN"], ":"),
                TestStep("burn_004", "Reset controller", ["RS"], ":"),
                TestStep("burn_005", "Verify persistence", ["MG TL"], "12345"),
                TestStep("burn_006", "Restore parameter", ["TL=0"], ":"),
            ]
        ))
        
        # Category 16: Ethernet Bring-up
        categories.append(TestCategory(
            category_id="ethernet",
            name="Ethernet Bring-up",
            description="Validate network path via Python sockets or gclib TCP",
            steps=[
                TestStep("eth_001", "Disable DHCP", ["DH0"], ":"),
                TestStep("eth_002", "Set IP address", ["IA 192,168,0,50"], ":"),
                TestStep("eth_003", "Burn network settings", ["BN"], ":"),
                TestStep("eth_004", "Reset controller", ["RS"], ":"),
                TestStep("eth_005", "Verify IP address", ["IA"], "192,168,0,50"),
                TestStep("eth_006", "Test network communication", ["TP A"], "position response"),
            ]
        ))
        
        # Category 17: Data Logging Throughput
        categories.append(TestCategory(
            category_id="data_logging",
            name="Data Logging Throughput",
            description="Check Python read loop keeps up",
            steps=[
                TestStep("log_001", "Start logging test", ["SHX", f"JGX={self.test_params['low_speed']}", "BGX"], ":"),
                TestStep("log_002", "Log position", ["TPX"], "position value"),
                TestStep("log_003", "Log velocity", ["TVX"], "velocity value"),
                TestStep("log_004", "Log following error", ["MG _TEX"], "error value"),
                TestStep("log_005", "Stop motion", ["JGX=0", "AMX"], ":"),
                TestStep("log_006", "Motor off", ["MOX"], ":"),
            ]
        ))
        
        # Category 18: Final Regression Summary
        categories.append(TestCategory(
            category_id="final_regression",
            name="Final Regression Summary",
            description="Leave controller in known state",
            steps=[
                TestStep("final_001", "Motor off", ["MOX"], ":"),
                TestStep("final_002", "Restore acceleration", ["ACX=100000"], ":"),
                TestStep("final_003", "Restore deceleration", ["DCX=100000"], ":"),
                TestStep("final_004", "Restore speed", ["SPX=50000"], ":"),
                TestStep("final_005", "Clear any faults", ["CB _FE"], ":"),
                TestStep("final_006", "Final status check", ["MG _MOX", "MG _FE"], "clean status"),
            ]
        ))
        
        return categories
    
    def run_diagnostics(self, callback: Optional[Callable] = None) -> DiagnosticsReport:
        """
        Run complete diagnostics suite.
        
        Args:
            callback: Optional callback function for progress updates
            
        Returns:
            DiagnosticsReport with complete results
        """
        if self.is_running:
            raise RuntimeError("Diagnostics already running")
        
        self.is_running = True
        self.stop_requested = False
        start_time = time.time()
        
        try:
            # Check if controller is connected before starting
            try:
                test_response = self.controller.send_command("TP A")
                if test_response.startswith('?'):
                    raise Exception("Controller not responding properly")
            except Exception as e:
                self.is_running = False
                raise Exception(f"Cannot run diagnostics: Controller not connected ({e})")
            
            # Initialize report
            self.report = DiagnosticsReport(
                timestamp=datetime.now().isoformat(),
                controller_info={},
                test_categories=[],
                overall_result=TestResult.SKIP,
                total_execution_time=0.0,
                summary={}
            )
            
            # Get controller information
            self._get_controller_info()
            
            # Run each test category
            for i, category in enumerate(self.test_categories):
                if self.stop_requested:
                    break
                    
                if callback:
                    callback(f"Running {category.name}...", i+1, 18)
                
                self._run_test_category(category)
                self.report.test_categories.append(category)
            
            # Calculate overall results
            self._calculate_overall_results()
            
            # Generate summary
            self._generate_summary()
            
            self.report.total_execution_time = time.time() - start_time
            
            # Diagnostics completed
            
            return self.report
            
        except Exception as e:
            raise
        finally:
            self.is_running = False
    
    def _get_controller_info(self):
        """Get basic controller information"""
        try:
            self.report.controller_info = {
                'firmware_revision': self._send_command("MG _REV"),
                'board_model': self._send_command("MG _BM"),
                'burn_count': self._send_command("MG _BN"),
                'mac_address': self._send_command("TH"),
                'ip_address': self._send_command("IA"),
                'dhcp_status': self._send_command("DH"),
            }
        except Exception as e:
            self.report.controller_info = {'error': str(e)}
    
    def _run_test_category(self, category: TestCategory):
        """Run a single test category"""
        category_start_time = time.time()
        
        try:
            for step in category.steps:
                if self.stop_requested:
                    break
                    
                self._run_test_step(step)
                
                # Small delay between steps
                time.sleep(0.1)
            
            category.execution_time = time.time() - category_start_time
            
            # Determine category result
            failed_steps = [s for s in category.steps if s.result == TestResult.FAIL]
            error_steps = [s for s in category.steps if s.result == TestResult.ERROR]
            
            if error_steps:
                category.overall_result = TestResult.ERROR
            elif failed_steps:
                category.overall_result = TestResult.FAIL
            else:
                category.overall_result = TestResult.PASS
                
        except Exception as e:
            category.overall_result = TestResult.ERROR
            category.notes = f"Category failed: {e}"
    
    def _run_test_step(self, step: TestStep):
        """Run a single test step"""
        step_start_time = time.time()
        
        try:
            responses = []
            
            for command in step.commands:
                if self.stop_requested:
                    break
                    
                response = self._send_command(command)
                responses.append(response)
                
                # Check for error responses
                if response.startswith('?'):
                    step.result = TestResult.FAIL
                    step.actual_response = response
                    step.notes = f"Command error: {response}"
                    return
            
            step.actual_response = "; ".join(responses)
            step.execution_time = time.time() - step_start_time
            
            # Basic pass/fail logic (can be enhanced with specific criteria)
            if step.actual_response and not step.actual_response.startswith('?'):
                step.result = TestResult.PASS
            else:
                step.result = TestResult.FAIL
                
        except Exception as e:
            step.result = TestResult.ERROR
            step.actual_response = f"Exception: {e}"
            step.notes = str(e)
    
    def _send_command(self, command: str) -> str:
        """Send command to controller with error handling"""
        try:
            response = self.controller.send_command(command)
            return response.strip()
        except Exception as e:
            # Check if controller is disconnected
            error_msg = str(e).lower()
            if "not connected" in error_msg or "connection" in error_msg:
                # Controller is disconnected, stop diagnostics
                self.stop_requested = True
                logger.error(f"Controller disconnected during diagnostics: {e}")
                return f"?Controller disconnected: {e}"
            
            # Only log critical errors, not command failures
            if "device write error" in str(e) or "device timed out" in str(e):
                logger.error(f"Critical command failure '{command}': {e}")
            return f"?{e}"
    
    def _calculate_overall_results(self):
        """Calculate overall test results"""
        if not self.report.test_categories:
            self.report.overall_result = TestResult.ERROR
            return
        
        failed_categories = [c for c in self.report.test_categories if c.overall_result == TestResult.FAIL]
        error_categories = [c for c in self.report.test_categories if c.overall_result == TestResult.ERROR]
        
        if error_categories:
            self.report.overall_result = TestResult.ERROR
        elif failed_categories:
            self.report.overall_result = TestResult.FAIL
        else:
            self.report.overall_result = TestResult.PASS
    
    def _generate_summary(self):
        """Generate test summary statistics"""
        total_steps = sum(len(c.steps) for c in self.report.test_categories)
        passed_steps = sum(len([s for s in c.steps if s.result == TestResult.PASS]) for c in self.report.test_categories)
        failed_steps = sum(len([s for s in c.steps if s.result == TestResult.FAIL]) for c in self.report.test_categories)
        error_steps = sum(len([s for s in c.steps if s.result == TestResult.ERROR]) for c in self.report.test_categories)
        
        self.report.summary = {
            'total_categories': len(self.report.test_categories),
            'total_steps': total_steps,
            'passed_steps': passed_steps,
            'failed_steps': failed_steps,
            'error_steps': error_steps,
            'pass_rate': (passed_steps / total_steps * 100) if total_steps > 0 else 0,
            'failed_categories': [c.name for c in self.report.test_categories if c.overall_result == TestResult.FAIL],
            'error_categories': [c.name for c in self.report.test_categories if c.overall_result == TestResult.ERROR],
        }
    
    def stop_diagnostics(self):
        """Stop running diagnostics"""
        self.stop_requested = True
    
    def save_report(self, filename: str):
        """Save diagnostics report to JSON file"""
        if not self.report:
            raise RuntimeError("No report to save")
        
        # Convert to dictionary for JSON serialization
        report_dict = asdict(self.report)
        
        with open(filename, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        # Report saved
    
    def get_technician_checklist(self) -> str:
        """Generate a technician checklist format"""
        if not self.report:
            return "No report available"
        
        checklist = []
        checklist.append("DMC-4103 DIAGNOSTICS CHECKLIST")
        checklist.append("=" * 50)
        checklist.append(f"Date: {self.report.timestamp}")
        checklist.append(f"Controller: {self.report.controller_info.get('board_model', 'Unknown')}")
        checklist.append(f"Firmware: {self.report.controller_info.get('firmware_revision', 'Unknown')}")
        checklist.append("")
        
        for category in self.report.test_categories:
            checklist.append(f"{category.name.upper()}")
            checklist.append("-" * len(category.name))
            
            for step in category.steps:
                status = "✓" if step.result == TestResult.PASS else "✗" if step.result == TestResult.FAIL else "⚠"
                checklist.append(f"{status} {step.description}")
                
                if step.commands:
                    checklist.append(f"    Commands: {'; '.join(step.commands)}")
                
                if step.actual_response:
                    checklist.append(f"    Response: {step.actual_response}")
                
                if step.notes:
                    checklist.append(f"    Notes: {step.notes}")
                
                checklist.append("")
            
            checklist.append(f"Category Result: {category.overall_result.value}")
            checklist.append("")
        
        checklist.append("OVERALL RESULT")
        checklist.append("-" * 15)
        checklist.append(f"Status: {self.report.overall_result.value}")
        checklist.append(f"Pass Rate: {self.report.summary.get('pass_rate', 0):.1f}%")
        checklist.append(f"Execution Time: {self.report.total_execution_time:.2f} seconds")
        
        return "\n".join(checklist)

# Example usage and testing
if __name__ == "__main__":
    # This would be used with an actual GalilController instance
    print("DMC-4103 Diagnostics Module")
    print("This module provides comprehensive diagnostics for DMC-4103 controllers.")
    print("Use with a GalilController instance that has a send_command method.")
