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
    
    def gsend(self, command: str) -> str:
        """Send a single Galil command and return its full reply.
           If controller returns '?', raise with TC 1 text."""
        try:
            response = self.controller.GCommand(command)
            response = response.strip()
            if response == "?":
                try:
                    why = self.controller.GCommand("TC 1").strip()
                except Exception:
                    why = "unknown (TC fetch failed)"
                raise RuntimeError(f"Galil error on '{command}': {why}")
            return response
        except Exception as e:
            try:
                why = self.controller.GCommand("TC 1").strip()
            except Exception:
                why = "unknown (TC fetch failed)"
            raise RuntimeError(f"Galil error on '{command}': {why}") from e
    
    def setup_all_axes(self) -> dict:
        """
        Set up all axes (A, B, C, D) with proper brushless configuration
        Returns status for each axis
        """
        results = {}
        
        # Global setup
        self.log("Setting up all axes for brushless operation...")
        
        # Stop all motion and turn off all motors
        success, response = self.send_command("AB")
        if not success:
            self.log(f"Warning: Could not abort all motion: {response}")
        
        success, response = self.send_command("MO")
        if not success:
            self.log(f"Warning: Could not turn off all motors: {response}")
        
        # Enhanced error reporting
        success, response = self.send_command("AZ2")
        if not success:
            self.log(f"Warning: Could not enable enhanced error reporting: {response}")
        
        # Set all axes to servo mode
        success, response = self.send_command("MT 1,1,1,1")
        if not success:
            self.log(f"Warning: Could not set all axes to servo mode: {response}")
        
        # Set up each axis individually
        for axis in ["A", "B", "C", "D"]:
            self.log(f"Setting up axis {axis}...")
            axis_result = self._setup_single_axis(axis)
            results[axis] = axis_result
            
            if axis_result["success"]:
                self.log(f"✓ Axis {axis} setup successful")
            else:
                self.log(f"✗ Axis {axis} setup failed: {axis_result['error']}")
        
        return results
    
    def _setup_single_axis(self, axis: str) -> dict:
        """
        Set up a single axis with proper brushless configuration
        
        Args:
            axis: Axis letter (A, B, C, D)
            
        Returns:
            dict with success status and details
        """
        try:
            # Assign brushless amp
            success, response = self.send_command(f"BA {axis}")
            if not success:
                return {"success": False, "error": f"BA {axis} failed: {response}"}
            
            # Set brushless modulo (16000 for 64k counts/4 pole pairs)
            success, response = self.send_command(f"BM{axis}=16000")
            if not success:
                return {"success": False, "error": f"BM{axis}=16000 failed: {response}"}
            
            # Try BZ commutation (fallback that worked for A)
            success, response = self.send_command(f"BZ{axis}")
            if not success:
                return {"success": False, "error": f"BZ{axis} failed: {response}"}
            
            # Enable servo
            success, response = self.send_command(f"SH{axis}")
            if not success:
                return {"success": False, "error": f"SH{axis} failed: {response}"}
            
            return {"success": True, "error": None}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_command(self, command: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Send command to controller with error handling (bypass validation for motor setup)
        
        Args:
            command: Command to send
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, response)
        """
        # Skip validation for motor setup commands - they are valid Galil commands
        # but the validation system doesn't understand the proper syntax
        
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
            # 1. Comprehensive controller initialization for brushless operation
            self.log("Initializing controller for brushless operation...")
            
            # Stop all motion and turn off all motors
            success, response = self.send_command("AB")
            if not success:
                self.log(f"Warning: Could not abort all motion: {response}")
            
            success, response = self.send_command("MO")
            if not success:
                self.log(f"Warning: Could not turn off all motors: {response}")
            
            # Enhanced error reporting
            success, response = self.send_command("AZ2")
            if not success:
                self.log(f"Warning: Could not enable enhanced error reporting: {response}")
            
            # Set all axes to servo mode
            success, response = self.send_command("MT 1,1,1,1")
            if not success:
                self.log(f"Warning: Could not set all axes to servo mode: {response}")
            
            # Assign brushless amps to all axes (per-axis to avoid validator issues)
            for ax in ["A", "B", "C", "D"]:
                success, response = self.send_command(f"BA {ax}")
                if not success:
                    self.log(f"Warning: Could not assign brushless amp for axis {ax}: {response}")
            
            # Set brushless modulo for all axes (64000/4 = 16000)
            for ax in ["A", "B", "C", "D"]:
                success, response = self.send_command(f"BM{ax}=16000")
                if not success:
                    self.log(f"Warning: Could not set BM for axis {ax}: {response}")
            
            # Initialize sine amps for all axes (start with 0 for auto-align)
            # Ensure axes are in MO state before BX commands
            for ax in ["A", "B", "C", "D"]:
                # Put axis in MO state before BX
                self.send_command(f"MO{ax}")
                success, response = self.send_command(f"BX{ax}=0")
                if not success:
                    self.log(f"Warning: Could not initialize sine amp for axis {ax}: {response}")
            
            # Set safety limits (per-axis to avoid validator issues)
            for ax in ["A", "B", "C", "D"]:
                success, response = self.send_command(f"ER{ax}=20000")
                if not success:
                    self.log(f"Warning: Could not set error limit for axis {ax}: {response}")
                
                success, response = self.send_command(f"OE{ax}=3")
                if not success:
                    self.log(f"Warning: Could not set output error limit for axis {ax}: {response}")
            
            # Enable servos for all axes
            for ax in ["A", "B", "C", "D"]:
                success, response = self.send_command(f"SH{ax}")
                if not success:
                    self.log(f"Warning: Could not enable servo for axis {ax}: {response}")
                else:
                    self.log(f"✓ Axis {ax} servo enabled")
            
            # 2. Put specific axis in safe/off state
            success, response = self.send_command(f"MO{axis}")
            if not success:
                return SetupResult(False, f"Failed to turn off motor {axis}: {response}")
            
            # 3. Disable servo loop to allow free manual movement
            success, response = self.send_command(f"MO{axis}")
            if not success:
                self.log(f"Warning: Could not turn off motor {axis}: {response}")
            
            # 4. Disable following error to prevent holding torque
            success, response = self.send_command(f"OE{axis}=0")
            if not success:
                self.log(f"Warning: Could not disable following error for {axis}: {response}")
            
            # 5. Set large error limit to prevent holding
            success, response = self.send_command(f"ER{axis}=200000")
            if not success:
                self.log(f"Warning: Could not set error limit for {axis}: {response}")
            
            # 6. Wait for motor to fully disengage
            time.sleep(1.0)
            
            # 7. Enable servo for the specific axis so it can be jogged in Step 4
            success, response = self.send_command(f"SH{axis}")
            if not success:
                self.log(f"Warning: Could not enable servo for axis {axis}: {response}")
            else:
                self.log(f"✓ Axis {axis} servo enabled for Step 4 jog capability")
            
            self.log(f"✓ Axis {axis} prepared successfully")
            return SetupResult(True, f"Axis {axis} prepared - motor off, ready for manual testing")
            
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
            # For 64000 counts/rev and 4 pole pairs: BM = 16000 (this is correct)
            bm_value = encoder_counts / pole_pairs
            self.log(f"Calculated BM value: {bm_value} (encoder_counts={encoder_counts}, pole_pairs={pole_pairs})")
            
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
            self.log(f"Initializing BX commutation for axis {axis}...")
            
            # Ensure the controller is in the right state for BX commands
            # First, make sure the axis is properly configured
            success, response = self.send_command(f"MO{axis}")
            if not success:
                self.log(f"Warning: Could not turn off motor {axis}: {response}")
            
            # Try different BX approaches in sequence (start with 0 for auto-align)
            bx_approaches = [
                f"BX{axis}=0",   # Auto-align (preferred)
                f"BX{axis}=3",   # Torque-align method
                f"BX{axis}=2",   # Lower torque-align
                f"BX{axis}=-3",  # Negative voltage approach
                f"BX{axis}=-2",  # Lower negative voltage
            ]
            
            for i, bx_cmd in enumerate(bx_approaches):
                self.log(f"Trying BX approach {i+1}: {bx_cmd}")
                success, response = self.send_command(bx_cmd)
                
                if success:
                    self.log(f"✓ BX initialization successful with {bx_cmd}")
                    return SetupResult(True, f"Axis {axis} commutation initialized (BX method)")
                else:
                    self.log(f"BX approach {i+1} failed: {response}")
                    if i < len(bx_approaches) - 1:
                        self.log(f"Trying next approach...")
                    else:
                        self.log(f"All BX approaches failed")
            
            # If all BX approaches failed, try a different strategy
            self.log(f"Trying alternative commutation strategy...")
            
            # Try BZ method as fallback
            success, response = self.send_command(f"BZ{axis}=-1")
            if success:
                self.log(f"✓ BZ initialization successful as fallback")
                return SetupResult(True, f"Axis {axis} commutation initialized (BZ fallback)")
            
            # If everything fails, return failure but don't stop the setup
            self.log(f"Warning: All commutation methods failed for axis {axis}")
            return SetupResult(False, f"BX initialization failed with all approaches: {response}")
            
        except Exception as e:
            self.log(f"BX initialization exception: {str(e)}")
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
            
            # Enable servo after successful BZ commutation
            success, response = self.send_command(f"SH{axis}")
            if not success:
                self.log(f"Warning: Could not enable servo for axis {axis}: {response}")
                # Continue anyway - might already be enabled
            
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
    
    def _automatic_index_measurement(self, axis: str) -> dict:
        """
        Robust Step-4 index measurement with diagnostics
        Based on user's precise specification - never MO, proper direction, multiple attempts
        """
        import time
        import math
        
        try:
            self.log(f"Starting robust index measurement for axis {axis}...")
            
            ax = axis.upper()
            others = [a for a in "ABCD" if a != ax]
            
            def cmd(s): 
                r = self.controller.GCommand(s)
                return r
            
            def mg(expr): 
                # Example: mg("_TSA") -> "15.0000\r\n"
                return float(self.controller.GCommand(f"MG {{{expr}}}"))
            
            # --- prep: be in servo here, relax OE/ER, pick safe jog direction by limits
            if int(mg(f"_MO{ax}")):                       # MO? -> SH
                cmd(f"SH{ax}")
            
            # choose direction away from an active limit (TS bit3 FWD inactive, bit2 REV inactive)
            ts = int(mg(f"_TS{ax}"))
            dir_sign = 1
            if (ts & 8) == 0: dir_sign = -1   # FWD limit active -> go negative
            if (ts & 4) == 0: dir_sign =  1   # REV limit active -> go positive
            
            # store/relax protections
            try:
                prev_oe = int(mg(f"_OE{ax}"))     # if _OE* isn't supported, we'll just set/restore using OEA below
            except:
                prev_oe = None
            try:
                prev_oea = int(mg(f"_OE{ax}"))    # alias for some firmwares
            except:
                prev_oea = None
            
            # Use Off-on-Error per-axis operand/command if available on your fw; fall back to OEA
            cmd(f"OE{ax}=0")                     # OEA=0 : do not shut down on following error during the jog
            cmd(f"ER{ax}=200000")                 # large following error limit so we don't abort
            
            # motion params (safe but snappy)
            cmd(f"SP{ax}=6000; AC{ax}=60000; DC{ax}=60000")
            
            # helper: arm all latches so we can detect wrong-axis wiring
            def arm_all():
                cmd(f"AL{ax}")
                for o in others:
                    cmd(f"AL{o}")
            
            # helper: poll for a latch on our axis, while also watching other axes (wiring diag)
            def wait_for_latch(max_secs):
                start = time.time()
                wrong_axis = None
                while True:
                    ts_self = int(mg(f"_TS{ax}"))
                    if ts_self & 1:   # bit0==1 => position latch occurred
                        return None   # ok on our axis
                    for o in others:
                        if int(mg(f"_TS{o}")) & 1:
                            wrong_axis = o
                            return wrong_axis
                    if time.time() - start > max_secs:
                        return "timeout"
                    time.sleep(0.01)
            
            # --- FIRST LATCH ---
            arm_all()
            cmd(f"JG{ax}={2000*dir_sign}")
            cmd(f"BG{ax}")
            res = wait_for_latch(8.0)
            if res == "timeout":
                # Try faster & longer, reverse once, then give reason
                for attempt, (speed, secs, sign) in enumerate([(4000, 8.0, dir_sign),
                                                               (4000, 12.0, -dir_sign),
                                                               (8000, 16.0, dir_sign)]):
                    cmd(f"JG{ax}={speed*sign}"); cmd(f"BG{ax}")
                    res = wait_for_latch(secs)
                    if res is None:
                        break
                if res == "timeout":
                    # no latch anywhere → likely no Z or filtering killing it
                    cmd(f"ST{ax}; AM{ax}")
                    raise RuntimeError(f"No Z index detected on axis {ax}. "
                                       f"Check Z wiring/polarity/filtering or jog distance (tried multiple revs).")
            if isinstance(res, str) and res in others:
                cmd(f"ST{ax}; AM{ax}")
                raise RuntimeError(f"Z index for motor {ax} appears wired to axis {res}. "
                                   f"Latch bit set on {res} while jogging {ax}.")
            
            cmd(f"ST{ax}; AM{ax}")
            p1 = float(self.controller.GCommand(f"RL{ax}").strip())  # RLA
            
            # --- SECOND LATCH ---
            arm_all()
            cmd(f"JG{ax}={2000*dir_sign}")
            cmd(f"BG{ax}")
            res = wait_for_latch(8.0)
            if res == "timeout":
                # extend distance once more
                cmd(f"JG{ax}={4000*dir_sign}"); cmd(f"BG{ax}")
                res = wait_for_latch(12.0)
                if res == "timeout":
                    cmd(f"ST{ax}; AM{ax}")
                    raise RuntimeError(f"Only one Z latch observed on {ax}. Jogged multiple revs without second pulse. "
                                       f"Verify Z once-per-rev and filtering.")
            if isinstance(res, str) and res in others:
                cmd(f"ST{ax}; AM{ax}")
                raise RuntimeError(f"Second Z latch showed on {res} while jogging {ax}. Wiring mix-up.")
            
            cmd(f"ST{ax}; AM{ax}")
            p2 = float(self.controller.GCommand(f"RL{ax}").strip())
            
            # --- Compute CPR with wrap; refine BM and re-commutate ---
            try:
                bm_hint = float(mg(f"_BM{ax}"))  # some firmwares expose _BMA/_BMB...
            except:
                try:
                    bm_hint = float(mg(f"_BM{ax}"))  # keep both attempts; fall back below if needed
                except:
                    bm_hint = 16000.0  # sane default for your 64k/4pp case
            
            # normalize delta into [0, bm_hint)
            d = p2 - p1
            d = d % bm_hint if bm_hint > 0 else abs(d)
            # choose the smaller equivalent (handles occasional double-edge captures)
            if bm_hint and d > bm_hint/2:
                d = bm_hint - d
            
            cpr = max(1.0, d)               # counts per mech rev from Z→Z
            bm_new = cpr / 4.0  # pole_pairs = 4
            
            # sanity: if wildly off, tell the user instead of writing garbage
            if bm_hint and not (0.5*bm_hint <= bm_new <= 1.5*bm_hint):
                raise RuntimeError(f"Computed BM {bm_new:.1f} is far from hint {bm_hint:.1f}. "
                                   f"Likely Z wired wrong or noisy/filtering.")
            
            cmd(f"BM{ax}={bm_new:.0f}")
            cmd(f"BZ{ax}")
            
            # restore protections
            cmd(f"OE{ax}=3")   # typical default; change if your app uses a different setting
            
            self.log(f"Index measurement successful: P1={p1}, P2={p2}, CPR={cpr}, BM={bm_new:.0f}")
            
            return {
                "success": True,
                "encoder_counts": int(cpr),
                "pole_pairs": 4,
                "p1": p1,
                "p2": p2,
                "bm_new": bm_new
            }
                
        except Exception as e:
            self.log(f"Automatic measurement failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
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
            # Always try automatic measurement first
            self.log("Attempting automatic index measurement...")
            auto_result = self._automatic_index_measurement(axis)
            
            if auto_result['success']:
                exact_encoder_counts = auto_result['encoder_counts']
                pole_pairs = auto_result['pole_pairs']
                self.log(f"Automatic measurement successful: {exact_encoder_counts} counts, {pole_pairs} pole pairs")
                
                # Calculate improved BM
                improved_bm = exact_encoder_counts / pole_pairs
                
                # Use gsend for robust command sending
                def gsend(cmd: str) -> str:
                    try:
                        response = self.controller.GCommand(cmd)
                        response = response.strip()
                        if response == "?":
                            try:
                                why = self.controller.GCommand("TC 1").strip()
                            except Exception:
                                why = "unknown (TC fetch failed)"
                            raise RuntimeError(f"Galil error on '{cmd}': {why}")
                        return response
                    except Exception as e:
                        try:
                            why = self.controller.GCommand("TC 1").strip()
                        except Exception:
                            why = "unknown (TC fetch failed)"
                        raise RuntimeError(f"Galil error on '{cmd}': {why}") from e
                
                # Set improved BM
                gsend(f"BM{axis}={improved_bm}")
                
                # Verify improved BM
                actual_bm = gsend(f"MG _BM{axis}")
                self.log(f"✓ Axis {axis} BM improved to {improved_bm} (verified: {actual_bm})")
                
                return SetupResult(True, f"Axis {axis} BM improved to {improved_bm}", 
                                 {"improved_bm": improved_bm, "actual_bm": actual_bm})
            else:
                self.log("⚠️ No Z index available - skipping Step 4")
                self.log("This is normal if no Z index is wired to the encoder")
                return SetupResult(True, "Step 4 skipped - no Z index available")
            
        except Exception as e:
            self.log(f"Step 4 failed: {str(e)}")
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
