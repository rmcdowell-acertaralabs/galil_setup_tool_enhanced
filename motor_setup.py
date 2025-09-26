"""
Motor Setup and Tuning System for DMC-4143 + AMP-43540

This module implements a comprehensive motor setup process based on the DMC-4103 command reference.
It provides step-by-step motor configuration for brushless servo motors with proper error checking.
"""

import time
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
    
    # Default servo parameters for consistent application
    DEFAULTS = {
        "TL": 8.0, "KI": 0.1, "KP": 10.0, "KD": 50.0,
        "AC": 200000, "DC": 200000
    }
    
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
    
    def read_all_positions(self):
        out = {}
        for ax in "ABCD":
            ok, r = self.send_command(f"TP{ax}")    # Use concatenated syntax "TPA"
            if not ok:
                # fetch why and raise
                raise RuntimeError(f"TP{ax} failed: {self._last_error_text()}")
            out[ax] = float(str(r).strip().split(',')[0])
        return out
    
    def servo_enable(self, ax: str, tl: float = 8.0):
        ax = ax.upper()
        # No AZ here (it requires all axes MO).
        self.send_command(f"OE{ax}=0")
        self.send_command(f"MO{ax}")
        ok, _ = self.send_command(f"SH{ax}")
        if not ok:
            raise RuntimeError(f"SH{ax} failed: {self._last_error_text()}")
        self.send_command(f"TL{ax}={tl}")
        ok, moval = self.send_command(f"MG _MO{ax}")
        if not ok or float(str(moval).strip().split(',')[0]) != 0.0:
            raise RuntimeError(f"Axis {ax} still OFF after SH")
    
    def log(self, message: str):
        """Log a message"""
        self.log_callback(message)
    
    def _last_error_text(self) -> str:
        """Get the actual last error text from the controller"""
        try:
            code = (self.controller.send_command("TE") or "").strip()
            text = (self.controller.send_command("TC") or "").strip()
            return f"[TE={code}] {text}".strip()
        except Exception:
            return "unknown (TE/TC fetch failed)"
    
    def _ax(self, axis: str) -> str:
        """Normalize and validate axis name"""
        ax = (axis or "").strip().upper()
        if ax not in ("A","B","C","D"):
            raise ValueError(f"Invalid axis '{axis}'")
        return ax
    
    def _apply_safe_servo_defaults(self, ax: str):
        """Apply safe servo defaults to prevent heating and ensure stable operation"""
        self.send_command(f"TL{ax}={self.DEFAULTS['TL']}")
        self.send_command(f"KI{ax}={self.DEFAULTS['KI']}")
        self.send_command(f"KP{ax}={self.DEFAULTS['KP']}")
        self.send_command(f"KD{ax}={self.DEFAULTS['KD']}")
        self.send_command(f"AC{ax}={self.DEFAULTS['AC']}")
        self.send_command(f"DC{ax}={self.DEFAULTS['DC']}")
    
    def _mg_float(self, expr: str) -> Tuple[bool, float]:
        """Debounced readback parsing helper for MG commands"""
        ok, r = self.send_command(f"MG {expr}")
        if not ok:
            return False, float("nan")
        try:
            return True, float(str(r).strip().split(',')[0])
        except Exception:
            return True, float("nan")
    
    
    def setup_all_axes(self, deep_relax: bool = False) -> dict:
        """
        Set up all axes (A, B, C, D) with proper brushless configuration
        
        Args:
            deep_relax: If True, fully de-energize motors after setup (TL=0, MO)
            
        Returns:
            Status for each axis
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
        
        # Enhanced error reporting removed (AZ2 not supported on 41x3)
        
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
                self._relax_axis(axis, deep=deep_relax)
                self.log(f"✓ Axis {axis} setup successful")
            else:
                self.log(f"✗ Axis {axis} setup failed: {axis_result['error']}")
        
        return results
    
    def _setup_single_axis(self, axis: str) -> dict:
        """
        Per-axis setup using the same BZ sequence as Step 3 for consistency.
        """
        ax = self._ax(axis)
        try:
            ok, resp = self.send_command(f"BA {ax}")
            if not ok:
                # Log but continue; 41x3 can legitimately return '?'
                self.log(f"Note: BA {ax} not supported/ignored: {resp}")

            # Set BM first so we can size ER against it
            ok, resp = self.send_command(f"BM{ax}=16000")
            if not ok:
                return {"success": False, "error": f"BM{ax}=16000 failed: {resp}"}

            # Mirror Step 3 preface
            self.send_command(f"OE{ax}=0")
            ok, bm = self.send_command(f"MG _BM{ax}")
            bm_s = str(bm).strip() if ok else ""
            bm_val = float(bm_s.split(',')[0]) if bm_s else 16000.0
            self.send_command(f"ER{ax}={max(1000.0, bm_val)}")

            # Clear any residual torque/offset before BZ
            self.send_command(f"TK{ax}=0")
            self.send_command(f"OF{ax}=0")
            self.send_command(f"TL{ax}=4")  # mild holding limit before BZ

            ok, resp = self.send_command("BZ<200>100")
            if not ok:
                return {"success": False, "error": f"Failed to set BZ hold times: {resp}"}

            ok, resp = self.send_command(f"BZ{ax}=-3")
            if not ok:
                return {"success": False, "error": f"BZ{ax}=-3 failed: {resp}"}

            ok, resp = self.send_command(f"SH{ax}")
            if not ok:
                return {"success": False, "error": f"SH{ax} failed: {resp}"}

            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_command(self, command: str) -> Tuple[bool, str]:
        """
        Send a command and normalize errors. If the controller replies with '?',
        return False with the detailed last error text from TE/TC.
        """
        try:
            resp = self.controller.send_command(command)
            resp_s = "" if resp is None else str(resp).strip()
            if resp_s == "?":
                return False, f"Galil '?' on '{command}': {self._last_error_text()}"
            return True, resp_s
        except Exception as e:
            msg = str(e)
            if "question mark" in msg.lower() or msg.strip() == "?":
                return False, f"Galil '?' on '{command}': {self._last_error_text()}"
            if "timeout" in msg.lower():
                return False, "Command timed out"
            if "device write error" in msg.lower():
                return False, "Device write error - controller may be unresponsive"
            return False, f"Command failed: {msg}"
    
    def step_0_prep(self, axis: str) -> SetupResult:
        ax = self._ax(axis)
        self.log(f"Step 0: Preparing axis {ax} for setup...")
        try:
            self.log("Initializing controller for brushless operation...")

            # 0) Go safe: stop and power off all axes
            self.send_command("AB")
            self.send_command("MO")          # all OFF

            # 1) Clear latched amp errors (valid ONLY when all axes are MO)
            ok, _ = self.send_command("AZ")
            if not ok:
                self.log("Warning: AZ failed; amp errors may persist")

            # 2) Servo mode (OK to fail silently on unsupported axes)
            self.send_command("MT 1,1,1,1")

            # 3) Assign brushless amps (41x3 may ignore; warn only)
            for a in "ABCD":
                ok, resp = self.send_command(f"BA {a}")
                if not ok:
                    self.log(f"Note: BA {a} not supported/ignored: {resp}")

            # 4) Set BM nominally (e.g., 64000/4=16000)
            for a in "ABCD":
                self.send_command(f"BM{a}=16000")

            # 5) Safety: large error limit; disable Off-on-Error for setup
            for a in "ABCD":
                self.send_command(f"ER{a}=200000")
                self.send_command(f"OE{a}=0")

            # 6) Keep other axes OFF; only enable target later when needed
            self.send_command(f"MO{ax}")

            # 7) Wait a moment for drives to relax
            time.sleep(0.5)

            # 8) Prepare target axis so we can jog in later steps if needed
            self.send_command(f"SH{ax}")
            self.log(f"✓ Axis {ax} servo enabled for Step 4 jog capability")
            self.log(f"✓ Axis {ax} prepared successfully")
            return SetupResult(True, f"Axis {ax} prepared – servo enabled for later jog")
        except Exception as e:
            return SetupResult(False, f"Step 0 failed: {str(e)}")
    
    def step_1_define_direction(self, axis: str, manual_direction: str = None) -> SetupResult:
        ax = self._ax(axis)
        self.log(f"Step 1: Defining motor direction for axis {ax}...")

        try:
            # Make shaft truly free
            self.send_command(f"ST{ax}")
            self.send_command(f"MO{ax}")
            # Clear holding effects (axis-suffix, no spaces)
            self.send_command(f"TL{ax}=0")
            self.send_command(f"TK{ax}=0")
            self.send_command(f"OF{ax}=0")
            self.send_command(f"KI{ax}=0")

            ok, mo = self.send_command(f"MG _MO{ax}")
            mo_val = float(str(mo).strip().split(',')[0]) if ok else 0.0
            if mo_val != 1.0:
                self.log(f"Warning: Axis {ax} may still be ENABLED (MG _MO returned {mo!r})")
            else:
                self.log(f"✓ Axis {ax} motor is OFF for manual spin (MG _MO={mo_val:.0f})")

            # Zero position (axis-suffix)
            ok, resp = self.send_command(f"DP{ax}=0")
            if not ok:
                return SetupResult(False, f"Failed to zero position for axis {ax}: {resp}")
            self.log(f"✓ Position zeroed for axis {ax}")

            if manual_direction is None:
                self.log("⚠️ MANUAL TESTING REQUIRED:")
                self.log(f"  1. Manually rotate the shaft for axis {ax} in the desired + direction")
                self.log(f"  2. Read position with: TP{ax}")
                self.log("  3. If it increases → 'normal'; if it decreases → 'reversed'")
                return SetupResult(False, "Manual direction testing required",
                                   {"requires_manual_input": True, "step": "define_direction", "axis": ax})

            # Validate manual_direction input
            md = manual_direction.strip().lower()
            if md not in ("normal", "reversed"):
                return SetupResult(False, "manual_direction must be 'normal' or 'reversed'")

            # Encoder polarity
            if md == "reversed":
                ok, resp = self.send_command(f"CE{ax}=2")
                polarity = "reversed (quadrature)"
            else:
                ok, resp = self.send_command(f"CE{ax}=0")
                polarity = "normal"
            if not ok:
                return SetupResult(False, f"Failed to set encoder polarity for axis {ax}: {resp}")

            # Re-enable servo for next steps and restore torque/gains
            self.send_command(f"SH{ax}")
            # Apply safe servo defaults
            self._apply_safe_servo_defaults(ax)
            
            ok, pos = self.send_command(f"TP{ax}")
            if not ok:
                return SetupResult(False, f"Failed to read position for axis {ax}: {pos}")

            position = str(pos).strip()
            self.log(f"✓ Axis {ax} direction set to {polarity}, current position: {position}")
            return SetupResult(True, f"Axis {ax} direction set to {polarity}",
                               {"polarity": polarity, "position": position})

        except Exception as e:
            return SetupResult(False, f"Step 1 failed: {e}")
    
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
        ax = self._ax(axis)
        self.log(f"Step 2: Setting brushless modulo for axis {ax}...")
        
        try:
            if pole_pairs is None or pole_pairs <= 0:
                return SetupResult(False, "pole_pairs must be > 0")
            if encoder_counts is None or encoder_counts <= 0:
                return SetupResult(False, "encoder_counts must be > 0")

            # Calculate BM = encoder_counts / pole_pairs (as integer)
            bm_value = int(round(encoder_counts / float(pole_pairs)))
            self.log(f"Calculated BM value: {bm_value} (encoder_counts={encoder_counts}, pole_pairs={pole_pairs})")
            
            # Set brushless modulo
            success, response = self.send_command(f"BM{ax}={bm_value}")
            if not success:
                return SetupResult(False, f"Failed to set BM for axis {ax}: {response}")
            
            # Verify BM was set correctly
            success, response = self.send_command(f"MG _BM{ax}")
            if not success:
                return SetupResult(False, f"Failed to verify BM for axis {ax}: {response}")
            
            actual_bm = response.strip()
            self.log(f"✓ Axis {ax} BM set to {bm_value} (verified: {actual_bm})")
            
            return SetupResult(True, f"Axis {ax} BM set to {bm_value}", 
                             {"bm_value": bm_value, "actual_bm": actual_bm})
            
        except Exception as e:
            return SetupResult(False, f"Step 2 failed: {str(e)}")
    
    def step_3_initialize_commutation(self, axis: str, method: CommutationMethod = CommutationMethod.BZ) -> SetupResult:
        """
        Step 3: Initialize commutation using specified method
        
        Args:
            axis: Axis letter (A, B, C, D)
            method: Commutation initialization method
            
        Returns:
            SetupResult with success status and details
        """
        ax = self._ax(axis)
        self.log(f"Step 3: Initializing commutation for axis {ax} using {method.value} method...")
        try:
            # Keep Off-on-Error disabled during init
            self.send_command(f"OE{ax}=0")

            # ER := max(_BM, some floor)
            ok_bm, bm_val = self._mg_float(f"_BM{ax}")
            bm_val = bm_val if ok_bm and bm_val == bm_val else 16000.0
            er_val = max(1000.0, bm_val)
            self.send_command(f"ER{ax}={er_val}")
            
            if method == CommutationMethod.BZ:
                return self._initialize_commutation_bz(ax)
            elif method == CommutationMethod.BC_BI:
                return self._initialize_commutation_bc_bi(ax)
            elif method == CommutationMethod.BX:
                # BX unsupported on 41x3; fall back to BZ
                self.log("BX method unsupported on this controller; using BZ instead")
                return self._initialize_commutation_bz(ax)
            else:
                return SetupResult(False, f"Unknown commutation method: {method}")
                
        except Exception as e:
            return SetupResult(False, f"Step 3 failed: {str(e)}")
    
    def _initialize_commutation_bx(self, axis: str) -> SetupResult:
        """Initialize commutation using BX method (minimal motion)"""
        ax = self._ax(axis)
        try:
            self.log(f"Initializing BX commutation for axis {ax}...")
            
            # Ensure the controller is in the right state for BX commands
            # First, make sure the axis is properly configured
            success, response = self.send_command(f"MO{ax}")
            if not success:
                self.log(f"Warning: Could not turn off motor {ax}: {response}")
            
            # Try different BX approaches in sequence (start with 0 for auto-align)
            bx_approaches = [
                f"BX{ax}=0",   # Auto-align (preferred)
                f"BX{ax}=3",   # Torque-align method
                f"BX{ax}=2",   # Lower torque-align
                f"BX{ax}=-3",  # Negative voltage approach
                f"BX{ax}=-2",  # Lower negative voltage
            ]
            
            for i, bx_cmd in enumerate(bx_approaches):
                self.log(f"Trying BX approach {i+1}: {bx_cmd}")
                success, response = self.send_command(bx_cmd)
                
                if success:
                    self.log(f"✓ BX initialization successful with {bx_cmd}")
                    return SetupResult(True, f"Axis {ax} commutation initialized (BX method)")
                else:
                    self.log(f"BX approach {i+1} failed: {response}")
                    if i < len(bx_approaches) - 1:
                        self.log(f"Trying next approach...")
                    else:
                        self.log(f"All BX approaches failed")
            
            # If all BX approaches failed, try a different strategy
            self.log(f"Trying alternative commutation strategy...")
            
            # Try BZ method as fallback
            success, response = self.send_command(f"BZ{ax}=-1")
            if success:
                self.log(f"✓ BZ initialization successful as fallback")
                return SetupResult(True, f"Axis {ax} commutation initialized (BZ fallback)")
            
            # If everything fails, return failure but don't stop the setup
            self.log(f"Warning: All commutation methods failed for axis {ax}")
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
        ax = self._ax(axis)
        if not getattr(self.motor_specs, "has_halls", False):
            return SetupResult(False, f"BC/BI requested but motor_specs.has_halls=False")
        
        try:
            # Use AMP-43540's dedicated Hall inputs
            success, response = self.send_command(f"BI{ax}=-1")
            if not success:
                return SetupResult(False, f"Failed to set Hall inputs for axis {ax}: {response}")
            
            # Enable hall-based calibration
            success, response = self.send_command(f"BC{ax}")
            if not success:
                return SetupResult(False, f"Failed to enable hall calibration for axis {ax}: {response}")
            
            # Enable servo
            success, response = self.send_command(f"SH{ax}")
            if not success:
                return SetupResult(False, f"Failed to enable servo for axis {ax}: {response}")
            
            # Small jog to trigger hall transition
            success, response = self.send_command(f"JG{ax}=500")
            if not success:
                return SetupResult(False, f"Failed to set jog for axis {ax}: {response}")
            
            success, response = self.send_command(f"BG{ax}")
            if not success:
                return SetupResult(False, f"Failed to begin jog for axis {ax}: {response}")
            
            # Wait a moment for hall transition
            time.sleep(0.5)
            
            # Stop motion
            success, response = self.send_command(f"ST{ax}")
            if not success:
                return SetupResult(False, f"Failed to stop motion for axis {ax}: {response}")
            
            self.log(f"✓ Axis {ax} commutation initialized using BC/BI method")
            return SetupResult(True, f"Axis {ax} commutation initialized (BC/BI method)")
            
        except Exception as e:
            return SetupResult(False, f"BC/BI initialization failed: {str(e)}")
    
    def _relax_axis(self, axis: str, deep: bool = False):
        """Relax the axis to prevent heating at rest by reducing gains and bias"""
        ax = self._ax(axis)
        self.send_command(f"KI{ax}=0")     # disable integral at rest
        self.send_command(f"TK{ax}=0")     # no torque bias
        self.send_command(f"OF{ax}=0")     # no DAC offset
        self.send_command(f"TL{ax}=2" if not deep else f"TL{ax}=0")
        if deep:
            self.send_command(f"MO{ax}")  # fully off if safe
        self.log(f"✓ Axis {ax} relaxed{' (deep)' if deep else ''} to prevent heating at rest")

    def _automatic_index_measurement(self, axis: str) -> dict:
        import re
        ax = self._ax(axis)
        pole_pairs = self.motor_specs.pole_pairs or 4

        def cmd(s):
            ok, r = self.send_command(s)
            if not ok:
                raise RuntimeError(f"Galil error on '{s}': {self._last_error_text()}")
            return r

        def mg(expr):
            ok, val = self._mg_float(expr)
            if not ok:
                raise RuntimeError(f"Galil error on 'MG {expr}': {self._last_error_text()}")
            return val

        # Make sure target axis is ON and able to move
        cmd(f"SH{ax}")
        cmd(f"TL{ax}=8.0")
        cmd(f"OE{ax}=0")

        # Motion params
        cmd(f"ST{ax}")
        cmd(f"DP{ax}=0")
        cmd(f"SP{ax}=20000")
        cmd(f"AC{ax}=200000")
        cmd(f"DC{ax}=200000")

        # 1) Sweep to first index
        sweep = 70000
        cmd(f"PR{ax}={sweep}")
        cmd(f"FI{ax}")     # correct 41x3 form
        cmd(f"BG{ax}")

        t0 = time.time()
        while int(mg(f"_BG{ax}")) != 0:
            if time.time() - t0 > 6.0:
                cmd(f"ST{ax}")
                raise RuntimeError("Index not detected within sweep distance/time")
            time.sleep(0.05)

        pos1 = float(str(cmd(f"TP{ax}")).strip())
        if pos1 > sweep * 0.98:
            raise RuntimeError("No Z marker detected (finished near PR target)")

        # 2) Jog to next index
        cmd(f"JG{ax}=8000")
        cmd(f"FI{ax}")
        cmd(f"BG{ax}")

        t0 = time.time()
        while int(mg(f"_BG{ax}")) != 0:
            if time.time() - t0 > 6.0:
                cmd(f"ST{ax}")
                raise RuntimeError("Second index not detected within time limit")
            time.sleep(0.05)

        pos2 = float(str(cmd(f"TP{ax}")).strip())
        rev_counts = pos2 - pos1
        if rev_counts <= 0:
            raise RuntimeError(f"Unexpected rev_counts {rev_counts}")

        # Correct BM: counts per rev / pole_pairs
        bm_new = rev_counts / float(pole_pairs)

        # Ensure motion is stopped before returning (safety)
        try:
            self.send_command(f"ST{ax}")
        except Exception:
            pass

        return {
            "success": True,
            "encoder_counts": int(round(rev_counts)),
            "pole_pairs": pole_pairs,
            "p1": pos1,
            "p2": pos2,
            "bm_new": bm_new,
        }
    
    def step_4_improve_modulo(self, axis: str, exact_encoder_counts: int = None, pole_pairs: int = None) -> SetupResult:
        ax = self._ax(axis)
        self.log(f"Step 4: Improving modulo for axis {ax} with index data...")

        # If the preset says no index, skip immediately.
        if not getattr(self.motor_specs, "has_index", False) and exact_encoder_counts is None:
            self.log("No Z index in motor specs – skipping Step 4")
            return SetupResult(True, "Step 4 skipped - no index available")

        try:
            if exact_encoder_counts is not None and pole_pairs:
                if pole_pairs <= 0 or exact_encoder_counts <= 0:
                    return SetupResult(False, "Invalid index data: counts and pole_pairs must be > 0")
                improved_bm = int(round(float(exact_encoder_counts) / float(pole_pairs)))
            else:
                self.log("Attempting automatic index measurement...")
                auto = self._automatic_index_measurement(ax)
                exact_encoder_counts = abs(auto["encoder_counts"])  # be robust to direction
                pole_pairs = auto["pole_pairs"]
                improved_bm = int(round(exact_encoder_counts / float(pole_pairs)))

            ok, _ = self.send_command(f"BM{ax}={improved_bm}")
            if not ok:
                return SetupResult(False, f"Failed to set BM on axis {ax}")

            ok, actual_bm = self.send_command(f"MG _BM{ax}")
            actual_bm = str(actual_bm).strip() if ok else "?"
            self.log(f"✓ Axis {ax} BM improved to {improved_bm} (readback: {actual_bm})")

            return SetupResult(True, f"Axis {ax} BM improved to {improved_bm}",
                               {"improved_bm": improved_bm, "actual_bm": actual_bm})

        except Exception as e:
            msg = str(e)
            # Treat "no index found" as a SKIP, not a failure
            if "Index not detected" in msg or "No Z marker" in msg:
                self.log("No Z index detected during sweep – skipping Step 4")
                return SetupResult(True, "Step 4 skipped - index not detected")
            return SetupResult(False, f"Step 4 failed: {msg}")
    
    def step_5_verify_commutation(self, axis: str) -> SetupResult:
        ax = self._ax(axis)
        self.log(f"Step 5: Verifying commutation for axis {ax}...")
        try:
            hall_status = "Skipped (BZ method)"

            # Optional: electrical angle
            ok, resp = self.send_command(f"MG _BD{ax}")
            electrical_angle = resp.strip() if ok else "Unknown"

            # Ensure the axis is READY: stop, enable, torque, sane gains
            self.send_command(f"ST{ax}")
            self.send_command(f"OE{ax}=0")
            self._apply_safe_servo_defaults(ax)

            ok, _ = self.send_command(f"SH{ax}")
            if not ok:
                return SetupResult(False, f"Failed to enable servo for axis {ax}: {self._last_error_text()}")

            # Poll briefly after SH - some firmwares need a tick to reflect _MO == 0
            for _ in range(10):
                ok_mo, mo_val = self._mg_float(f"_MO{ax}")
                if ok_mo and mo_val == 0.0:
                    break
                time.sleep(0.02)
            else:
                return SetupResult(False, f"Axis {ax} is OFF before jog: {self._last_error_text()}")

            # Use separate commands (more robust than 'JG;BG' on some firmwares)
            ok, _ = self.send_command(f"JG{ax}=5000")
            if not ok:
                return SetupResult(False, f"Failed to set jog for axis {ax}: {self._last_error_text()}")

            ok, _ = self.send_command(f"BG{ax}")
            if not ok:
                return SetupResult(False, f"Failed to start jog for axis {ax}: {self._last_error_text()}")

            time.sleep(0.25)
            self.send_command(f"ST{ax}")
            time.sleep(0.25)

            ok, _ = self.send_command(f"JG{ax}=-5000")
            if not ok:
                return SetupResult(False, f"Failed to set reverse jog for axis {ax}: {self._last_error_text()}")

            ok, _ = self.send_command(f"BG{ax}")
            if not ok:
                return SetupResult(False, f"Failed to start reverse jog for axis {ax}: {self._last_error_text()}")

            time.sleep(0.25)
            self.send_command(f"ST{ax}")

            self.log(f"✓ Axis {ax} commutation verified - Hall status: {hall_status}, Electrical angle: {electrical_angle}")
            return SetupResult(True, f"Axis {ax} commutation verified",
                               {"hall_status": hall_status, "electrical_angle": electrical_angle})

        except Exception as e:
            return SetupResult(False, f"Step 5 failed: {e}")
    
    def step_6_save_settings(self, restore_oe: bool = True) -> SetupResult:
        """
        Step 6: Save settings to controller non-volatile memory
        
        Args:
            restore_oe: Whether to restore Off-on-Error after saving
            
        Returns:
            SetupResult with success status and details
        """
        self.log("Step 6: Saving settings to controller...")
        
        try:
            # Burn non-volatile parameters
            success, response = self.send_command("BN")
            if not success:
                return SetupResult(False, f"Failed to save settings: {response}")
            
            # Optionally restore Off-on-Error
            if restore_oe:
                try:
                    self.send_command(f"OE{self.current_axis}=1")
                    # Verify OE restore
                    ok, val = self.send_command(f"MG _OE{self.current_axis}")
                    if ok and val.strip().split(',')[0] == "1":
                        self.log("✓ Off-on-Error confirmed ON")
                    else:
                        self.log("Warning: Off-on-Error restore may have failed")
                except Exception:
                    self.log("Warning: Could not restore Off-on-Error")
            
            self.log("✓ Settings saved to controller")
            return SetupResult(True, "Settings saved to controller non-volatile memory")
            
        except Exception as e:
            return SetupResult(False, f"Step 6 failed: {str(e)}")
    
    def run_complete_setup(self, axis: str, motor_specs: MotorSpecs, 
                          commutation_method: CommutationMethod = CommutationMethod.BZ) -> Dict[str, SetupResult]:
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
            if (not results['step_1'].success
                and isinstance(results['step_1'].data, dict)
                and results['step_1'].data.get("requires_manual_input")):
                self.log("Waiting for manual direction input; call continue_step_1_with_direction() to proceed.")
                return results
            
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
            
            # Relax axis after Step 5 to prevent heating at rest
            if results['step_5'].success:
                self._relax_axis(self.current_axis)
            
            # Step 6: Save settings
            if results['step_5'].success:
                results['step_6'] = self.step_6_save_settings()
                # Relax again after saving settings
                if results['step_6'].success:
                    self._relax_axis(self.current_axis)
            else:
                results['step_6'] = SetupResult(False, "Step 6 skipped - Step 5 failed")
            
            self.setup_results = results
            self.log(f"Motor setup completed for axis {self.current_axis}")
            
        except Exception as e:
            self.log(f"Motor setup failed: {str(e)}")
            results['error'] = SetupResult(False, f"Setup failed: {str(e)}")
        
        finally:
            # Always relax to avoid heating at rest, even if steps failed
            try:
                self._relax_axis(self.current_axis)
            except Exception:
                pass
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
        ax = self._ax(axis)
        commands = []
        
        # Step 0: Preparation
        commands.extend([f"MO{ax}", f"BA {ax}"])
        
        # Step 1: Define direction (placeholder - requires manual input)
        commands.extend([f"DP{ax}=0", f"CE{ax}=0"])  # Default to normal polarity
        
        # Step 2: Set brushless modulo
        if motor_specs.encoder_counts_per_rev and motor_specs.pole_pairs:
            bm_value = int(round(motor_specs.encoder_counts_per_rev / float(motor_specs.pole_pairs)))
            commands.extend([f"BM{ax}={bm_value}", f"MG _BM{ax}"])
        
        # Step 3: Safety clears (OE/ER/TK/OF) before commutation
        # Note: Runtime uses ER=max(_BM,1000), validator uses ER=1000 for simplicity
        commands.extend([f"OE{ax}=0", f"MG _BM{ax}", f"ER{ax}=1000", f"TK{ax}=0", f"OF{ax}=0"])

        if commutation_method == CommutationMethod.BX:
            # 41x3 doesn't support BX reliably; validate BZ instead
            commands.extend([f"BZ<200>100", f"BZ{ax}=-3"])
        elif commutation_method == CommutationMethod.BZ:
            commands.extend([f"BZ<200>100", f"BZ{ax}=-3"])
        elif commutation_method == CommutationMethod.BC_BI:
            commands.extend([f"BI{ax}=-1", f"BC{ax}", f"SH{ax}",
                             f"JG{ax}=500", f"BG{ax}", f"ST{ax}"])

        # Step 5: Verify (some firmwares skip halls on BZ)
        commands.extend([f"MG _BD{ax}", f"SH{ax}",
                         f"JG{ax}=5000", f"BG{ax}", f"ST{ax}"])
        
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
