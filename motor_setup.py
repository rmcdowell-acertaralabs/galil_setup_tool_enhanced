"""
Motor Setup and Tuning System for DMC-4143 + AMP-43540

This module implements a comprehensive motor setup process based on the DMC-4103 command reference.
It provides step-by-step motor configuration for brushless servo motors with proper error checking.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from command_validator import DMC4103CommandValidator, CommandValidation

class SetupStep(Enum):
    """Enumeration of motor setup steps"""
    PREP = "prep"
    DEFINE_DIRECTION = "define_direction"
    SET_BRUSHLESS_MODULO = "set_brushless_modulo"
    INITIALIZE_COMMUTATION = "initialize_commutation"
    IMPROVE_MODULO = "improve_modulo"
    VERIFY_COMMUTATION = "verify_commutation"
    SAVE_SETTINGS = "save_settings"

class CommutationMethod(Enum):
    """Available commutation initialization methods"""
    BX = "bx"  # Minimal motion, auto-phase
    BZ = "bz"  # Drive to electrical zero
    BC_BI = "bc_bi"  # Hall-based initialization

@dataclass
class MotorSpecs:
    """Motor specifications for setup"""
    encoder_counts_per_rev: Optional[int] = None
    pole_pairs: Optional[int] = None
    has_index: bool = False
    has_halls: bool = True  # AMP-43540 has dedicated hall inputs

@dataclass
class SetupResult:
    """Result of a setup step"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

class MotorSetup:
    """Motor setup and tuning system for DMC-4143 + AMP-43540"""
    
    def __init__(self, controller, log_callback=None):
        """
        Initialize motor setup system
        
        Args:
            controller: Galil controller instance
            log_callback: Optional callback function for logging
        """
        self.controller = controller
        self.log_callback = log_callback or self._default_log
        self.current_axis = 'A'
        self.motor_specs = MotorSpecs()
        self.setup_results = {}
        self.is_running = False
        self.command_validator = DMC4103CommandValidator()
        
    def _default_log(self, message: str):
        """Default logging function"""
        print(f"[MotorSetup] {message}")
    
    def log(self, message: str):
        """Log a message"""
        self.log_callback(message)
    
    def send_command(self, command: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Send command to controller with error handling and validation
        
        Args:
            command: Command to send
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, response)
        """
        # Validate command before sending
        validation = self.command_validator.validate_command(command)
        if not validation.valid:
            self.log(f"Command validation failed: {validation.error_message}")
            return False, f"Invalid command: {validation.error_message}"
        
        if validation.warning_message:
            self.log(f"Command warning: {validation.warning_message}")
        
        try:
            response = self.controller.send_command(command)
            return True, str(response) if response is not None else ""
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                return False, "Command timed out"
            elif "device write error" in error_msg.lower():
                return False, "Device write error - controller may be unresponsive"
            elif "question mark" in error_msg.lower():
                return False, "Controller returned error (?)"
            else:
                return False, f"Command failed: {error_msg}"
    
    def step_0_prep(self, axis: str) -> SetupResult:
        """
        Step 0: Preparation - Put axis in safe state and enable sine mode
        
        Args:
            axis: Axis letter (A, B, C, D)
            
        Returns:
            SetupResult with success status and details
        """
        self.log(f"Step 0: Preparing axis {axis} for setup...")
        
        try:
            # 1. Put axis in safe/off state
            success, response = self.send_command(f"MO{axis}")
            if not success:
                return SetupResult(False, f"Failed to turn off motor {axis}: {response}")
            
            # 2. Enable sine-drive mode
            success, response = self.send_command(f"BA {axis}")
            if not success:
                return SetupResult(False, f"Failed to enable sine mode for axis {axis}: {response}")
            
            self.log(f"✓ Axis {axis} prepared successfully")
            return SetupResult(True, f"Axis {axis} prepared - motor off, sine mode enabled")
            
        except Exception as e:
            return SetupResult(False, f"Step 0 failed: {str(e)}")
    
    def step_1_define_direction(self, axis: str, manual_direction: str = None) -> SetupResult:
        """
        Step 1: Define encoder sign (motor direction)
        
        Args:
            axis: Axis letter (A, B, C, D)
            manual_direction: "normal" or "reversed" - user's choice based on manual testing
            
        Returns:
            SetupResult with success status and details
        """
        self.log(f"Step 1: Defining motor direction for axis {axis}...")
        
        try:
            # 1. Zero position
            success, response = self.send_command(f"DP{axis}=0")
            if not success:
                return SetupResult(False, f"Failed to zero position for axis {axis}: {response}")
            
            self.log(f"✓ Position zeroed for axis {axis}")
            
            # 2. Manual direction testing required
            if manual_direction is None:
                self.log("⚠️ MANUAL TESTING REQUIRED:")
                self.log(f"  1. Manually rotate the motor shaft for axis {axis} in your desired + direction")
                self.log(f"  2. Read the position with: TP{axis}")
                self.log(f"  3. If position increases, use 'normal' polarity")
                self.log(f"  4. If position decreases, use 'reversed' polarity")
                self.log("  5. Click 'Continue' when ready to proceed")
                
                # Return a special result indicating manual input is needed
                return SetupResult(False, "Manual direction testing required", 
                                 {"requires_manual_input": True, "step": "define_direction", "axis": axis})
            
            # 3. Set encoder polarity based on user input
            if manual_direction == "reversed":
                success, response = self.send_command(f"CE{axis}=2")
                polarity = "reversed (quadrature)"
            else:
                success, response = self.send_command(f"CE{axis}=0")
                polarity = "normal"
            
            if not success:
                return SetupResult(False, f"Failed to set encoder polarity for axis {axis}: {response}")
            
            # 4. Verify position reading
            success, response = self.send_command(f"TP{axis}")
            if not success:
                return SetupResult(False, f"Failed to read position for axis {axis}: {response}")
            
            position = response.strip()
            self.log(f"✓ Axis {axis} direction set to {polarity}, current position: {position}")
            
            return SetupResult(True, f"Axis {axis} direction set to {polarity}", 
                             {"polarity": polarity, "position": position})
            
        except Exception as e:
            return SetupResult(False, f"Step 1 failed: {str(e)}")
    
    def step_2_set_brushless_modulo(self, axis: str, encoder_counts: int, pole_pairs: int) -> SetupResult:
        """
        Step 2: Set Brushless Modulo (BM) based on encoder counts and pole pairs
        
        Args:
            axis: Axis letter (A, B, C, D)
            encoder_counts: Encoder counts per mechanical revolution
            pole_pairs: Number of pole pairs in the motor
            
        Returns:
            SetupResult with success status and details
        """
        self.log(f"Step 2: Setting brushless modulo for axis {axis}...")
        
        try:
            # Calculate BM = encoder_counts / pole_pairs
            bm_value = encoder_counts / pole_pairs
            
            # Set brushless modulo
            success, response = self.send_command(f"BM{axis}={bm_value}")
            if not success:
                return SetupResult(False, f"Failed to set BM for axis {axis}: {response}")
            
            # Verify BM was set correctly
            success, response = self.send_command(f"MG _BM{axis}")
            if not success:
                return SetupResult(False, f"Failed to verify BM for axis {axis}: {response}")
            
            actual_bm = response.strip()
            self.log(f"✓ Axis {axis} BM set to {bm_value} (verified: {actual_bm})")
            
            return SetupResult(True, f"Axis {axis} BM set to {bm_value}", 
                             {"bm_value": bm_value, "actual_bm": actual_bm})
            
        except Exception as e:
            return SetupResult(False, f"Step 2 failed: {str(e)}")
    
    def step_3_initialize_commutation(self, axis: str, method: CommutationMethod = CommutationMethod.BX) -> SetupResult:
        """
        Step 3: Initialize commutation using specified method
        
        Args:
            axis: Axis letter (A, B, C, D)
            method: Commutation initialization method
            
        Returns:
            SetupResult with success status and details
        """
        self.log(f"Step 3: Initializing commutation for axis {axis} using {method.value} method...")
        
        try:
            # Set up safety parameters
            success, response = self.send_command(f"OE{axis}=1")
            if not success:
                return SetupResult(False, f"Failed to enable overtravel for axis {axis}: {response}")
            
            # Set error limit >= BM
            success, response = self.send_command(f"ER{axis}=_BM{axis}")
            if not success:
                return SetupResult(False, f"Failed to set error limit for axis {axis}: {response}")
            
            if method == CommutationMethod.BX:
                return self._initialize_commutation_bx(axis)
            elif method == CommutationMethod.BZ:
                return self._initialize_commutation_bz(axis)
            elif method == CommutationMethod.BC_BI:
                return self._initialize_commutation_bc_bi(axis)
            else:
                return SetupResult(False, f"Unknown commutation method: {method}")
                
        except Exception as e:
            return SetupResult(False, f"Step 3 failed: {str(e)}")
    
    def _initialize_commutation_bx(self, axis: str) -> SetupResult:
        """Initialize commutation using BX method (minimal motion)"""
        try:
            # Set hold time for final pulse
            success, response = self.send_command(f"BX<1000>")
            if not success:
                return SetupResult(False, f"Failed to set BX hold time: {response}")
            
            # Initialize with ~3V, end with SH (negative ends with SH)
            success, response = self.send_command(f"BX{axis}=-3")
            if not success:
                if "160" in response or "error" in response.lower():
                    # Try with more voltage
                    self.log(f"BX failed, trying with more voltage...")
                    success, response = self.send_command(f"BX{axis}=-4")
                    if not success:
                        return SetupResult(False, f"BX initialization failed even with increased voltage: {response}")
                else:
                    return SetupResult(False, f"BX initialization failed: {response}")
            
            self.log(f"✓ Axis {axis} commutation initialized using BX method")
            return SetupResult(True, f"Axis {axis} commutation initialized (BX method)")
            
        except Exception as e:
            return SetupResult(False, f"BX initialization failed: {str(e)}")
    
    def _initialize_commutation_bz(self, axis: str) -> SetupResult:
        """Initialize commutation using BZ method (drive to electrical zero)"""
        try:
            # Set hold times: p=100ms (stage 1), o=200ms (stage 2)
            success, response = self.send_command(f"BZ<200>100")
            if not success:
                return SetupResult(False, f"Failed to set BZ hold times: {response}")
            
            # Drive with ~3V, end with SH
            success, response = self.send_command(f"BZ{axis}=-3")
            if not success:
                return SetupResult(False, f"BZ initialization failed: {response}")
            
            self.log(f"✓ Axis {axis} commutation initialized using BZ method")
            return SetupResult(True, f"Axis {axis} commutation initialized (BZ method)")
            
        except Exception as e:
            return SetupResult(False, f"BZ initialization failed: {str(e)}")
    
    def _initialize_commutation_bc_bi(self, axis: str) -> SetupResult:
        """Initialize commutation using BC/BI method (Hall-based)"""
        try:
            # Use AMP-43540's dedicated Hall inputs
            success, response = self.send_command(f"BI{axis}=-1")
            if not success:
                return SetupResult(False, f"Failed to set Hall inputs for axis {axis}: {response}")
            
            # Enable hall-based calibration
            success, response = self.send_command(f"BC{axis}")
            if not success:
                return SetupResult(False, f"Failed to enable hall calibration for axis {axis}: {response}")
            
            # Enable servo
            success, response = self.send_command(f"SH{axis}")
            if not success:
                return SetupResult(False, f"Failed to enable servo for axis {axis}: {response}")
            
            # Small jog to trigger hall transition
            success, response = self.send_command(f"JG{axis}=500")
            if not success:
                return SetupResult(False, f"Failed to set jog for axis {axis}: {response}")
            
            success, response = self.send_command(f"BG{axis}")
            if not success:
                return SetupResult(False, f"Failed to begin jog for axis {axis}: {response}")
            
            # Wait a moment for hall transition
            time.sleep(0.5)
            
            # Stop motion
            success, response = self.send_command(f"ST{axis}")
            if not success:
                return SetupResult(False, f"Failed to stop motion for axis {axis}: {response}")
            
            self.log(f"✓ Axis {axis} commutation initialized using BC/BI method")
            return SetupResult(True, f"Axis {axis} commutation initialized (BC/BI method)")
            
        except Exception as e:
            return SetupResult(False, f"BC/BI initialization failed: {str(e)}")
    
    def step_4_improve_modulo(self, axis: str, exact_encoder_counts: int = None, pole_pairs: int = None) -> SetupResult:
        """
        Step 4: Improve modulo with index (if available)
        
        Args:
            axis: Axis letter (A, B, C, D)
            exact_encoder_counts: Exact encoder counts from index measurement
            pole_pairs: Number of pole pairs in the motor
            
        Returns:
            SetupResult with success status and details
        """
        self.log(f"Step 4: Improving modulo for axis {axis} with index data...")
        
        try:
            # Check if manual index measurement is required
            if exact_encoder_counts is None or pole_pairs is None:
                self.log("⚠️ MANUAL INDEX MEASUREMENT REQUIRED:")
                self.log(f"  1. Latch on index: AL T{axis}")
                self.log(f"  2. Jog to trigger index: JG{axis}=2000")
                self.log(f"  3. Begin motion: BG{axis}")
                self.log(f"  4. Wait for index pulse to occur")
                self.log(f"  5. Read latched position: RL{axis}")
                self.log(f"  6. Repeat for second index pulse")
                self.log(f"  7. Calculate exact counts per revolution")
                self.log(f"  8. Click 'Continue' when ready to proceed")
                
                # Return a special result indicating manual input is needed
                return SetupResult(False, "Manual index measurement required", 
                                 {"requires_manual_input": True, "step": "improve_modulo", "axis": axis})
            
            # Calculate improved BM
            improved_bm = exact_encoder_counts / pole_pairs
            
            # Set improved BM
            success, response = self.send_command(f"BM{axis}={improved_bm}")
            if not success:
                return SetupResult(False, f"Failed to set improved BM for axis {axis}: {response}")
            
            # Verify improved BM
            success, response = self.send_command(f"MG _BM{axis}")
            if not success:
                return SetupResult(False, f"Failed to verify improved BM for axis {axis}: {response}")
            
            actual_bm = response.strip()
            self.log(f"✓ Axis {axis} BM improved to {improved_bm} (verified: {actual_bm})")
            
            return SetupResult(True, f"Axis {axis} BM improved to {improved_bm}", 
                             {"improved_bm": improved_bm, "actual_bm": actual_bm})
            
        except Exception as e:
            return SetupResult(False, f"Step 4 failed: {str(e)}")
    
    def step_5_verify_commutation(self, axis: str) -> SetupResult:
        """
        Step 5: Verify commutation and basic motion
        
        Args:
            axis: Axis letter (A, B, C, D)
            
        Returns:
            SetupResult with success status and details
        """
        self.log(f"Step 5: Verifying commutation for axis {axis}...")
        
        try:
            # Check hall status
            success, response = self.send_command(f"QH {axis}")
            if not success:
                return SetupResult(False, f"Failed to read hall status for axis {axis}: {response}")
            
            hall_status = response.strip()
            if hall_status in ['0', '7']:
                return SetupResult(False, f"Invalid hall status for axis {axis}: {hall_status}")
            
            # Read brushless electrical angle (optional)
            success, response = self.send_command(f"MG _BD{axis}")
            if success:
                electrical_angle = response.strip()
            else:
                electrical_angle = "Unknown"
            
            # Test basic motion
            success, response = self.send_command(f"SH{axis}")
            if not success:
                return SetupResult(False, f"Failed to enable servo for axis {axis}: {response}")
            
            # Small jog test
            success, response = self.send_command(f"JG{axis}=5000")
            if not success:
                return SetupResult(False, f"Failed to set jog for axis {axis}: {response}")
            
            success, response = self.send_command(f"BG{axis}")
            if not success:
                return SetupResult(False, f"Failed to begin jog for axis {axis}: {response}")
            
            # Wait for motion
            time.sleep(1.0)
            
            # Stop motion
            success, response = self.send_command(f"ST{axis}")
            if not success:
                return SetupResult(False, f"Failed to stop motion for axis {axis}: {response}")
            
            self.log(f"✓ Axis {axis} commutation verified - Hall status: {hall_status}, Electrical angle: {electrical_angle}")
            
            return SetupResult(True, f"Axis {axis} commutation verified", 
                             {"hall_status": hall_status, "electrical_angle": electrical_angle})
            
        except Exception as e:
            return SetupResult(False, f"Step 5 failed: {str(e)}")
    
    def step_6_save_settings(self) -> SetupResult:
        """
        Step 6: Save settings to controller non-volatile memory
        
        Returns:
            SetupResult with success status and details
        """
        self.log("Step 6: Saving settings to controller...")
        
        try:
            # Burn non-volatile parameters
            success, response = self.send_command("BN")
            if not success:
                return SetupResult(False, f"Failed to save settings: {response}")
            
            self.log("✓ Settings saved to controller")
            return SetupResult(True, "Settings saved to controller non-volatile memory")
            
        except Exception as e:
            return SetupResult(False, f"Step 6 failed: {str(e)}")
    
    def run_complete_setup(self, axis: str, motor_specs: MotorSpecs, 
                          commutation_method: CommutationMethod = CommutationMethod.BX) -> Dict[str, SetupResult]:
        """
        Run complete motor setup process for specified axis
        
        Args:
            axis: Axis letter (A, B, C, D)
            motor_specs: Motor specifications
            commutation_method: Commutation initialization method
            
        Returns:
            Dictionary of step results
        """
        self.current_axis = axis.upper()
        self.motor_specs = motor_specs
        self.is_running = True
        results = {}
        
        self.log(f"Starting complete motor setup for axis {self.current_axis}")
        
        try:
            # Step 0: Preparation
            results['step_0'] = self.step_0_prep(self.current_axis)
            if not results['step_0'].success:
                return results
            
            # Step 1: Define direction (requires manual input)
            results['step_1'] = self.step_1_define_direction(self.current_axis)
            
            # Step 2: Set brushless modulo
            if motor_specs.encoder_counts_per_rev and motor_specs.pole_pairs:
                results['step_2'] = self.step_2_set_brushless_modulo(
                    self.current_axis, 
                    motor_specs.encoder_counts_per_rev, 
                    motor_specs.pole_pairs
                )
            else:
                results['step_2'] = SetupResult(False, "Motor specs missing - encoder_counts_per_rev and pole_pairs required")
            
            # Step 3: Initialize commutation
            if results['step_2'].success:
                results['step_3'] = self.step_3_initialize_commutation(self.current_axis, commutation_method)
            else:
                results['step_3'] = SetupResult(False, "Step 3 skipped - Step 2 failed")
            
            # Step 4: Improve modulo (if index available)
            if motor_specs.has_index and motor_specs.pole_pairs:
                results['step_4'] = self.step_4_improve_modulo(self.current_axis)
            else:
                results['step_4'] = SetupResult(True, "Step 4 skipped - no index available")
            
            # Step 5: Verify commutation
            if results['step_3'].success:
                results['step_5'] = self.step_5_verify_commutation(self.current_axis)
            else:
                results['step_5'] = SetupResult(False, "Step 5 skipped - Step 3 failed")
            
            # Step 6: Save settings
            if results['step_5'].success:
                results['step_6'] = self.step_6_save_settings()
            else:
                results['step_6'] = SetupResult(False, "Step 6 skipped - Step 5 failed")
            
            self.setup_results = results
            self.log(f"Motor setup completed for axis {self.current_axis}")
            
        except Exception as e:
            self.log(f"Motor setup failed: {str(e)}")
            results['error'] = SetupResult(False, f"Setup failed: {str(e)}")
        
        finally:
            self.is_running = False
        
        return results
    
    def get_setup_summary(self) -> str:
        """Get a summary of the setup results"""
        if not self.setup_results:
            return "No setup results available"
        
        summary = f"Motor Setup Summary for Axis {self.current_axis}:\n"
        summary += "=" * 50 + "\n"
        
        for step_name, result in self.setup_results.items():
            status = "✓ PASS" if result.success else "✗ FAIL"
            summary += f"{step_name.upper()}: {status} - {result.message}\n"
        
        return summary
    
    def validate_setup_sequence(self, axis: str, motor_specs: MotorSpecs, 
                               commutation_method: CommutationMethod) -> List[CommandValidation]:
        """
        Validate the complete motor setup command sequence before execution
        
        Args:
            axis: Axis letter (A, B, C, D)
            motor_specs: Motor specifications
            commutation_method: Commutation initialization method
            
        Returns:
            List of CommandValidation objects
        """
        commands = []
        
        # Step 0: Preparation
        commands.extend([f"MO{axis}", f"BA {axis}"])
        
        # Step 1: Define direction (placeholder - requires manual input)
        commands.extend([f"DP{axis}=0", f"CE{axis}=0"])  # Default to normal polarity
        
        # Step 2: Set brushless modulo
        if motor_specs.encoder_counts_per_rev and motor_specs.pole_pairs:
            bm_value = motor_specs.encoder_counts_per_rev / motor_specs.pole_pairs
            commands.extend([f"BM{axis}={bm_value}", f"MG _BM{axis}"])
        
        # Step 3: Initialize commutation
        commands.extend([f"OE{axis}=1", f"ER{axis}=_BM{axis}"])
        
        if commutation_method == CommutationMethod.BX:
            commands.extend([f"BX<1000>", f"BX{axis}=-3"])
        elif commutation_method == CommutationMethod.BZ:
            commands.extend([f"BZ<200>100", f"BZ{axis}=-3"])
        elif commutation_method == CommutationMethod.BC_BI:
            commands.extend([f"BI{axis}=-1", f"BC{axis}", f"SH{axis}", 
                           f"JG{axis}=500", f"BG{axis}", f"ST{axis}"])
        
        # Step 5: Verify commutation
        commands.extend([f"QH {axis}", f"MG _BD{axis}", f"SH{axis}", 
                        f"JG{axis}=5000", f"BG{axis}", f"WT 1000", f"ST{axis}"])
        
        # Step 6: Save settings
        commands.append("BN")
        
        # Validate all commands
        return self.command_validator.validate_motor_setup_sequence(commands)
    
    def get_command_help(self, command: str) -> str:
        """Get help information for a command"""
        return self.command_validator.get_command_help(command)
    
    def continue_step_1_with_direction(self, axis: str, manual_direction: str) -> SetupResult:
        """Continue Step 1 with manual direction input"""
        return self.step_1_define_direction(axis, manual_direction)
    
    def continue_step_4_with_index_data(self, axis: str, exact_encoder_counts: int, pole_pairs: int) -> SetupResult:
        """Continue Step 4 with manual index measurement data"""
        return self.step_4_improve_modulo(axis, exact_encoder_counts, pole_pairs)
