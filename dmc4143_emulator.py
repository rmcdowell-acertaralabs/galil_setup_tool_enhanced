"""
DMC-4143 Test Harness (Emulator + gclib Mock)
Emulates a Galil DMC-4143 controller for testing without hardware.

Two usage modes:
1. TCP Server Mode: Run as standalone server, connect via IP (127.0.0.1:2323)
2. Python Mock Mode: Import FakeGclib and use as drop-in replacement for gclib.py()

Compatible with galil_setup_tool_enhanced codebase patterns.
"""

import socket
import threading
import time
import re
import sys
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# Hardware configuration matching your DMC-4143 setup
SUPPORTED_AXES = ("A", "B")  # C and D not present
MAX_DI = 8  # Digital inputs 1..8
MAX_DO = 8  # Digital outputs 1..8 (not 16)


class MotionState(Enum):
    """Motion state for each axis"""
    IDLE = "idle"
    JOGGING = "jogging"
    MOVING = "moving"
    HOMING = "homing"


@dataclass
class AxisState:
    """State tracking for a single axis"""
    # Servo status
    servo_on: bool = False
    motor_off: bool = False  # MO=1 means motor off
    
    # Motion parameters
    speed: int = 0  # SP (counts/s)
    acceleration: int = 0  # AC (counts/s^2)
    deceleration: int = 0  # DC (counts/s^2)
    jog_speed: int = 0  # JG (counts/s)
    
    # Position tracking
    position: int = 0  # TP (current position)
    target_position: int = 0  # PA/PR target
    position_error: int = 0  # TE (following error)
    
    # Motion state
    motion_state: MotionState = MotionState.IDLE
    motion_start_time: float = 0.0
    last_update_time: float = 0.0
    
    # Status variables (Galil internal variables)
    _BG: int = 0  # Busy flag (0=idle, 1=busy)
    _TS: int = 0  # Torque status
    _MO: int = 1  # Motor off (0=on, 1=off)
    
    # Limits (mock values)
    positive_limit: bool = False
    negative_limit: bool = False
    home_switch: bool = False
    
    # Position definitions
    defined_position: int = 0  # DP (defined position, usually set to 0 after SH)
    scale: int = 1  # SC (scale factor)
    
    # Brushless motor parameters
    motor_type: int = 0  # MT (motor type: 1=brushless, -1=brushless reversed, 0=standard)
    brushless_modulo: int = 5000  # BM (brushless modulo, counts per pole pair)
    brushless_initialized: bool = False  # BI initialization status
    brushless_calibration: bool = False  # BC calibration enabled
    brushless_commutation_angle: float = 0.0  # _BD (commutation angle)
    
    # Hall sensor simulation
    # Hall sensors cycle through states 1-6 as motor rotates
    # Each complete electrical cycle = 6 hall states
    # Hall state changes every (brushless_modulo / 6) counts
    hall_state: int = 1  # Current hall sensor state (1-6 valid, 0/7 invalid)
    last_hall_position: int = 0  # Position when last hall transition occurred
    
    # Encoder simulation
    encoder_counts_per_rev: int = 20000  # Typical encoder resolution
    encoder_position: int = 0  # Separate encoder position (can differ from motor position)
    
    def update_motion(self, dt: float):
        """Update axis motion based on time delta"""
        if self._BG == 0:
            return
        
        old_position = self.position
        
        if self.motion_state == MotionState.JOGGING and self.jog_speed != 0:
            # Simulate jogging - continuous movement
            direction = 1 if self.jog_speed > 0 else -1
            distance = abs(self.jog_speed) * dt
            self.position += direction * int(distance)
            self.encoder_position += direction * int(distance)  # Encoder tracks motor
            
            # Check limits
            if self.position > 1000000:
                self.position = 1000000
                self.jog_speed = 0
                self.positive_limit = True
                self._BG = 0
            elif self.position < -1000000:
                self.position = -1000000
                self.jog_speed = 0
                self.negative_limit = True
                self._BG = 0
                
        elif self.motion_state == MotionState.MOVING:
            # Simulate point-to-point motion
            remaining = self.target_position - self.position
            if abs(remaining) < 10:  # Close enough
                self.position = self.target_position
                self.encoder_position = self.target_position
                self._BG = 0
                self.motion_state = MotionState.IDLE
            else:
                # Simple velocity profile (constant speed for now)
                # In reality, this would have acceleration/deceleration
                direction = 1 if remaining > 0 else -1
                max_speed = abs(self.speed) if self.speed > 0 else 10000
                
                # Calculate velocity (simplified)
                move_distance = min(abs(remaining), max_speed * dt)
                self.position += direction * int(move_distance)
                self.encoder_position += direction * int(move_distance)  # Encoder tracks motor
        
        # Update hall sensor state based on position change
        # Only update if brushless is initialized AND motor is moving
        if (self.motor_type != 0 and self.brushless_modulo > 0 and 
            self.brushless_initialized and old_position != self.position):
            self._update_hall_sensors(old_position)
        
        # Update position error (simplified)
        self.position_error = self.target_position - self.position
        
        # Update last update time
        self.last_update_time = time.time()
    
    def _update_hall_sensors(self, old_position: int):
        """Update hall sensor state based on position change"""
        # This method is only called when brushless_initialized is True
        # (checked in update_motion), so we don't need to check again here
        if not self.brushless_initialized:
            # This shouldn't happen, but if it does, preserve current state
            return
        
        # Calculate position change
        position_change = self.position - old_position
        if position_change == 0:
            return  # No movement, keep current state
        
        # Hall sensors cycle through 6 states per electrical cycle
        # Each hall state represents (brushless_modulo / 6) counts
        counts_per_hall_state = max(1, self.brushless_modulo // 6)
        
        # Calculate total position change since last hall transition
        position_since_transition = abs(self.position - self.last_hall_position)
        
        # Check if we've moved enough to trigger a hall transition
        if position_since_transition >= counts_per_hall_state:
            # Update hall state (cycle 1-6)
            direction = 1 if (self.position - old_position) > 0 else -1
            if direction > 0:
                self.hall_state = ((self.hall_state - 1 + 1) % 6) + 1
            else:
                self.hall_state = ((self.hall_state - 1 - 1) % 6) + 1
                if self.hall_state == 0:
                    self.hall_state = 6
            
            # Update last transition position
            self.last_hall_position = self.position
            
            # Update commutation angle
            # Commutation angle changes with hall state (each state = 60 electrical degrees)
            self.brushless_commutation_angle = ((self.hall_state - 1) * 60.0) % 360.0


class DMC4143Emulator:
    """Emulates a DMC-4143 controller"""
    
    def __init__(self):
        self.axes: Dict[str, AxisState] = {
            "A": AxisState(),
            "B": AxisState(),
            "C": AxisState(),  # Present but unused per your config
            "D": AxisState(),  # Present but unused per your config
        }
        
        # Global parameters
        self.error_code: int = 0  # TC (error code)
        self.output_error: int = 0  # OE (output error)
        self.error_limit: int = 2000000  # ER (error limit)
        self.torque_limit: float = 8.0  # TL (torque limit)
        self.torque_kill: float = 9.0  # TK (torque kill)
        
        # IO (mock)
        self.digital_inputs: Dict[int, bool] = {i: False for i in range(1, MAX_DI + 1)}
        self.digital_outputs: Dict[int, bool] = {i: False for i in range(1, MAX_DO + 1)}
        self.analog_inputs: Dict[int, float] = {i: 0.0 for i in range(1, 9)}
        
        # Motion timer
        self.last_update: float = time.time()
        self.update_thread: Optional[threading.Thread] = None
        self.running: bool = False
        
        # Connection tracking
        self.connected_clients: list = []
        
    def start_update_loop(self):
        """Start background thread to update motion"""
        if self.running:
            return
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def stop_update_loop(self):
        """Stop background motion update thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
    
    def _update_loop(self):
        """Background loop to update axis motion"""
        while self.running:
            dt = 0.02  # 20ms update rate (50 Hz)
            time.sleep(dt)
            
            current_time = time.time()
            actual_dt = current_time - self.last_update
            
            for axis in self.axes.values():
                axis.update_motion(actual_dt)
            
            self.last_update = current_time
    
    def parse_command(self, cmd: str) -> str:
        """Parse and execute a Galil command, return response"""
        cmd = cmd.strip().upper()
        if not cmd:
            return ""
        
        # Remove echo disable flag if present (your code uses -s ALL)
        if cmd.startswith("-S"):
            return ""
        
        # Remove CR/LF if present (from TCP commands)
        cmd = cmd.replace('\r', '').replace('\n', '').strip()
        
        # Two-letter command pattern: CMD[AXIS][=VALUE]
        # Examples: SHA, MOA, JGA=5000, BGA, TPA, PA A=1000, MG _TSA
        
        # First try: Direct format like JGA=20000, MTA=1.0, etc.
        # Extract command and axis/value
        match = re.match(r'^([A-Z]{2})([ABCD]?)(?:=([-\d.]+))?$', cmd)
        if match:
            cmd_name, axis, value_str = match.groups()
            try:
                value = int(float(value_str)) if value_str else None
            except (ValueError, OverflowError):
                # If int conversion fails, try float (for MT=1.0)
                try:
                    value = float(value_str) if value_str else None
                except (ValueError, OverflowError):
                    value = None
            axis = axis if axis else None
            
            # Handle commands
            if cmd_name == "SH":  # Servo Here
                return self._cmd_servo_here(axis)
            elif cmd_name == "MO":  # Motor Off
                return self._cmd_motor_off(axis, value)
            elif cmd_name == "JG":  # Jog
                return self._cmd_jog(axis, value)
            elif cmd_name == "BG":  # Begin Motion
                return self._cmd_begin_motion(axis)
            elif cmd_name == "ST":  # Stop
                return self._cmd_stop(axis)
            elif cmd_name == "PA":  # Position Absolute
                return self._cmd_position_absolute(axis, value)
            elif cmd_name == "PR":  # Position Relative
                return self._cmd_position_relative(axis, value)
            elif cmd_name == "TP":  # Tell Position
                return self._cmd_tell_position(axis)
            elif cmd_name == "TE":  # Tell Error (following error)
                return self._cmd_tell_error(axis)
            elif cmd_name == "ID":  # Identify
                return self._cmd_identify()
            elif cmd_name == "SP":  # Set Speed
                return self._cmd_set_speed(axis, value)
            elif cmd_name == "AC":  # Acceleration
                return self._cmd_acceleration(axis, value)
            elif cmd_name == "DC":  # Deceleration
                return self._cmd_deceleration(axis, value)
            elif cmd_name == "DP":  # Define Position
                return self._cmd_define_position(axis, value)
            elif cmd_name == "AM":  # After Motion
                return self._cmd_after_motion(axis)
            elif cmd_name == "FI":  # Find Index
                return self._cmd_find_index(axis)
            elif cmd_name == "BA":  # Brushless Align
                return self._cmd_brushless_align(axis)
            elif cmd_name == "MT":  # Motor Type
                return self._cmd_motor_type(axis, value)
            elif cmd_name == "BM":  # Brushless Modulo
                return self._cmd_brushless_modulo(axis, value)
            elif cmd_name == "BI":  # Brushless Initialize
                return self._cmd_brushless_initialize(axis, value)
            elif cmd_name == "BC":  # Brushless Calibration
                return self._cmd_brushless_calibration(axis)
            elif cmd_name == "BZ":  # Brushless Zero
                return self._cmd_brushless_zero(axis)
            elif cmd_name == "TC":  # Tell Error Code
                return self._cmd_tell_error_code(value)
            elif cmd_name == "OE":  # Output Error
                return self._cmd_output_error(value)
            elif cmd_name == "ER":  # Error Limit
                return self._cmd_error_limit(value)
            elif cmd_name == "TL":  # Torque Limit
                return self._cmd_torque_limit(value)
            elif cmd_name == "TK":  # Torque Kill
                return self._cmd_torque_kill(value)
            elif cmd_name == "MG":  # Message (query variables)
                return self._cmd_message(cmd)
            elif cmd_name == "SC":  # Scale
                return self._cmd_scale(axis, value)
        
        # Handle multi-word commands like "PA A=1000" or direct "JGA=20000" if first regex failed
        if "=" in cmd:
            parts = cmd.split("=", 1)  # Split only on first = to handle negative values
            if len(parts) == 2:
                left = parts[0].strip()
                value_str = parts[1].strip()
                try:
                    value = int(float(value_str))
                except (ValueError, OverflowError):
                    # Try float for commands like MT=1.0
                    try:
                        value = float(value_str)
                    except (ValueError, OverflowError):
                        return "?"  # Invalid value
                
                # Extract command and axis from left side
                match = re.match(r'^([A-Z]{2})([ABCD])$', left)
                if match:
                    cmd_name, axis = match.groups()
                    if cmd_name == "PA":
                        return self._cmd_position_absolute(axis, value)
                    elif cmd_name == "PR":
                        return self._cmd_position_relative(axis, value)
                    elif cmd_name == "SP":
                        return self._cmd_set_speed(axis, value)
                    elif cmd_name == "AC":
                        return self._cmd_acceleration(axis, value)
                    elif cmd_name == "DC":
                        return self._cmd_deceleration(axis, value)
                    elif cmd_name == "DP":
                        return self._cmd_define_position(axis, value)
                    elif cmd_name == "JG":
                        return self._cmd_jog(axis, value)
                    elif cmd_name == "SC":
                        return self._cmd_scale(axis, value)
                    elif cmd_name == "MT":
                        return self._cmd_motor_type(axis, value)
                    elif cmd_name == "BM":
                        return self._cmd_brushless_modulo(axis, value)
                    elif cmd_name == "BI":
                        return self._cmd_brushless_initialize(axis, value)
                    elif cmd_name == "BC":
                        return self._cmd_brushless_calibration(axis)
                    elif cmd_name == "BZ":
                        return self._cmd_brushless_zero(axis)
        
        # Handle MG (Message) command for queries
        if cmd.startswith("MG"):
            return self._cmd_message(cmd)
        
        # Handle ID (Identify) command
        if cmd == "ID":
            return self._cmd_identify()
        
        # Handle other single-letter commands
        if cmd == "VE":  # Version
            return "DMC-4143 Emulator v1.0"
        elif cmd == "TC":  # Tell Error Code (no axis)
            return self._cmd_tell_error_code(None)
        elif cmd == "TE":  # Tell Error (no axis - returns error for all axes)
            return "0"  # No error
        elif cmd == "TH":  # Tell Network Info
            return "DMC-4143 Emulator\nIP: 127.0.0.1\nPort: 2323"
        
        # Unknown command
        return "?"
    
    # Command implementations
    def _cmd_servo_here(self, axis: Optional[str]) -> str:
        """SH - Servo Here (enable servo)"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            ax.servo_on = True
            ax.motor_off = False
            ax._MO = 0
            ax._TS = 1  # Torque status on
            ax.position_error = 0
            return ""
        return "?"
    
    def _cmd_motor_off(self, axis: Optional[str], value: Optional[int]) -> str:
        """MO - Motor Off"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            if value == 1:
                ax.motor_off = True
                ax.servo_on = False
                ax._MO = 1
                ax._TS = 0
            elif value == 0:
                ax.motor_off = False
                ax._MO = 0
            return ""
        return "?"
    
    def _cmd_jog(self, axis: Optional[str], value: Optional[int]) -> str:
        """JG - Jog (set jog speed)"""
        if axis and axis in self.axes and value is not None:
            ax = self.axes[axis]
            ax.jog_speed = value
            ax.motion_state = MotionState.JOGGING
            return ""
        return "?"
    
    def _cmd_begin_motion(self, axis: Optional[str]) -> str:
        """BG - Begin Motion"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            if ax.jog_speed != 0:
                ax.motion_state = MotionState.JOGGING
                ax._BG = 1
                ax.motion_start_time = time.time()
            elif ax.target_position != ax.position:
                ax.motion_state = MotionState.MOVING
                ax._BG = 1
                ax.motion_start_time = time.time()
            return ""
        return "?"
    
    def _cmd_stop(self, axis: Optional[str]) -> str:
        """ST - Stop"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            ax._BG = 0
            ax.motion_state = MotionState.IDLE
            ax.jog_speed = 0
            return ""
        # Stop all axes if no axis specified
        for ax in self.axes.values():
            ax._BG = 0
            ax.motion_state = MotionState.IDLE
            ax.jog_speed = 0
        return ""
    
    def _cmd_position_absolute(self, axis: Optional[str], value: Optional[int]) -> str:
        """PA - Position Absolute"""
        if axis and axis in self.axes and value is not None:
            ax = self.axes[axis]
            ax.target_position = value
            ax.motion_state = MotionState.MOVING
            return ""
        return "?"
    
    def _cmd_position_relative(self, axis: Optional[str], value: Optional[int]) -> str:
        """PR - Position Relative"""
        if axis and axis in self.axes and value is not None:
            ax = self.axes[axis]
            ax.target_position = ax.position + value
            ax.motion_state = MotionState.MOVING
            return ""
        return "?"
    
    def _cmd_tell_position(self, axis: Optional[str]) -> str:
        """TP - Tell Position"""
        if axis and axis in self.axes:
            return str(self.axes[axis].position)
        return "?"
    
    def _cmd_tell_error(self, axis: Optional[str]) -> str:
        """TE - Tell Error (following error)"""
        if axis and axis in self.axes:
            return str(self.axes[axis].position_error)
        return "?"
    
    def _cmd_set_speed(self, axis: Optional[str], value: Optional[int]) -> str:
        """SP - Set Speed"""
        if axis and axis in self.axes and value is not None:
            self.axes[axis].speed = value
            return ""
        return "?"
    
    def _cmd_acceleration(self, axis: Optional[str], value: Optional[int]) -> str:
        """AC - Acceleration"""
        if axis and axis in self.axes and value is not None:
            self.axes[axis].acceleration = value
            return ""
        return "?"
    
    def _cmd_deceleration(self, axis: Optional[str], value: Optional[int]) -> str:
        """DC - Deceleration"""
        if axis and axis in self.axes and value is not None:
            self.axes[axis].deceleration = value
            return ""
        return "?"
    
    def _cmd_define_position(self, axis: Optional[str], value: Optional[int]) -> str:
        """DP - Define Position"""
        if axis and axis in self.axes and value is not None:
            ax = self.axes[axis]
            offset = value - ax.position
            ax.position = value
            ax.defined_position = value
            # Adjust target if moving
            if ax.motion_state == MotionState.MOVING:
                ax.target_position += offset
            return ""
        return "?"
    
    def _cmd_after_motion(self, axis: Optional[str]) -> str:
        """AM - After Motion"""
        if axis and axis in self.axes:
            # Wait for motion complete (synchronous in real controller)
            # In emulator, just acknowledge
            return ""
        return "?"
    
    def _cmd_find_index(self, axis: Optional[str]) -> str:
        """FI - Find Index"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            ax.defined_position = ax.position
            return ""
        return "?"
    
    def _cmd_brushless_align(self, axis: Optional[str]) -> str:
        """BA - Brushless Align (configure brushless amplifier)"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            # Configure brushless amplifier
            # This enables brushless mode
            return ""
        return "?"
    
    def _cmd_motor_type(self, axis: Optional[str], value: Optional[float]) -> str:
        """MT - Motor Type (1=brushless, -1=brushless reversed, 0=standard)"""
        if axis and axis in self.axes and value is not None:
            ax = self.axes[axis]
            ax.motor_type = int(value)
            # If setting to brushless, initialize hall sensors
            if ax.motor_type != 0:
                ax.hall_state = 1  # Start with valid hall state
                ax.last_hall_position = ax.position
            return ""
        return "?"
    
    def _cmd_brushless_modulo(self, axis: Optional[str], value: Optional[int]) -> str:
        """BM - Brushless Modulo (counts per pole pair)"""
        if axis and axis in self.axes and value is not None:
            ax = self.axes[axis]
            ax.brushless_modulo = value
            return ""
        return "?"
    
    def _cmd_brushless_initialize(self, axis: Optional[str], value: Optional[int]) -> str:
        """BI - Brushless Initialize (initialize with hall sensors)"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            # BI command initializes brushless commutation
            # value=-1 means initialize with hall sensors
            # BI returns current hall state or -1 if not initialized
            if value == -1 or value is None:
                ax.brushless_initialized = True
                # Set initial hall state (valid 1-6)
                ax.hall_state = 1
                ax.last_hall_position = ax.position
                ax.brushless_commutation_angle = 0.0
                return "1"  # Return initial hall state
            # Query mode - return current state
            if ax.brushless_initialized:
                return str(ax.hall_state)
            return "-1"  # Not initialized
        return "?"
    
    def _cmd_brushless_calibration(self, axis: Optional[str]) -> str:
        """BC - Brushless Calibration (enable hall-based calibration)"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            # BC enables hall-based calibration
            ax.brushless_calibration = True
            # Ensure brushless is initialized (BC requires BI to have been run first)
            # But if it hasn't, initialize it anyway
            if not ax.brushless_initialized:
                ax.brushless_initialized = True
                # Set valid hall state if not already set
                if ax.hall_state == 0 or ax.hall_state > 6:
                    ax.hall_state = 1
                ax.last_hall_position = ax.position
                ax.brushless_commutation_angle = 0.0
            return ""
        return "?"
    
    def _cmd_brushless_zero(self, axis: Optional[str]) -> str:
        """BZ - Brushless Zero (zero commutation angle)"""
        if axis and axis in self.axes:
            ax = self.axes[axis]
            # BZ zeros the commutation angle
            ax.brushless_commutation_angle = 0.0
            return ""
        return "?"
    
    def _cmd_identify(self) -> str:
        """ID - Identify (returns controller model and version)"""
        return "DMC-4143 Emulator v1.0"
    
    def _cmd_tell_error_code(self, value: Optional[int]) -> str:
        """TC - Tell Error Code"""
        if value is not None:
            self.error_code = value
            return ""
        return str(self.error_code)
    
    def _cmd_output_error(self, value: Optional[int]) -> str:
        """OE - Output Error"""
        if value is not None:
            self.output_error = value
            return ""
        return str(self.output_error)
    
    def _cmd_error_limit(self, value: Optional[int]) -> str:
        """ER - Error Limit"""
        if value is not None:
            self.error_limit = value
            return ""
        return str(self.error_limit)
    
    def _cmd_torque_limit(self, value: Optional[float]) -> str:
        """TL - Torque Limit"""
        if value is not None:
            self.torque_limit = value
            return ""
        return str(self.torque_limit)
    
    def _cmd_torque_kill(self, value: Optional[float]) -> str:
        """TK - Torque Kill"""
        if value is not None:
            self.torque_kill = value
            return ""
        return str(self.torque_kill)
    
    def _cmd_scale(self, axis: Optional[str], value: Optional[int]) -> str:
        """SC - Scale"""
        if axis and axis in self.axes and value is not None:
            self.axes[axis].scale = value
            return ""
        return "?"
    
    def _cmd_message(self, cmd: str) -> str:
        """MG - Message (query variables like _TSA, _BGA, _TPA, _TEA, _MOA, _QHA, _BMA, _BDA, _BIA)"""
        # Extract variable name from MG command
        # Examples: "MG _TSA", "MG {_BG}", "MG _TPA", "MG _QHA"
        cmd = cmd.replace("{", "").replace("}", "")
        parts = cmd.split()
        if len(parts) < 2:
            return "?"
        
        var_name = parts[1].strip()
        
        # Handle status variables
        if var_name.startswith("_"):
            var_base = var_name[:3]  # _TS, _BG, _TP, _TE, _MO, _QH, _BM, _BD, _BI
            axis_char = var_name[3] if len(var_name) > 3 else None
            
            if axis_char and axis_char in self.axes:
                ax = self.axes[axis_char]
                
                if var_base == "_TS":  # Torque Status
                    return str(ax._TS)
                elif var_base == "_BG":  # Busy Flag
                    return str(ax._BG)
                elif var_base == "_TP":  # Tell Position
                    return str(ax.position)
                elif var_base == "_TE":  # Tell Error (following error)
                    return str(ax.position_error)
                elif var_base == "_MO":  # Motor Off
                    return str(ax._MO)
                elif var_base == "_SC":  # Scale
                    return str(ax.scale)
                elif var_base == "_QH":  # Query Hall (hall sensor state)
                    # Return hall sensor state (1-6 valid, 0 invalid if not initialized)
                    return str(ax.hall_state)
                elif var_base == "_BM":  # Brushless Modulo
                    return str(ax.brushless_modulo)
                elif var_base == "_BD":  # Brushless Commutation Angle
                    return str(ax.brushless_commutation_angle)
                elif var_base == "_BI":  # Brushless Initialize status
                    # Return 1 if initialized, 0 if not
                    return "1" if ax.brushless_initialized else "0"
            
            # Handle multi-character variable bases (like _SP, _AC, _DC)
            elif len(var_name) >= 4:
                var_base = var_name[:2] if len(var_name) >= 4 else var_name[:3]
                axis_char = var_name[2] if len(var_name) >= 3 and var_name[2] in "ABCD" else None
                
                if axis_char and axis_char in self.axes:
                    ax = self.axes[axis_char]
                    
                    if var_base == "_SP":  # Speed
                        return str(ax.speed)
                    elif var_base == "_AC":  # Acceleration
                        return str(ax.acceleration)
                    elif var_base == "_DC":  # Deceleration
                        return str(ax.deceleration)
        
        return "?"


# TCP Server Mode
class DMC4143TCPServer:
    """TCP server that emulates a Galil controller"""
    
    def __init__(self, host="127.0.0.1", port=2323):
        self.host = host
        self.port = port
        self.emulator = DMC4143Emulator()
        self.emulator.start_update_loop()
        self.server_socket = None
        self.running = False
    
    def start(self):
        """Start the TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"[DMC4143 Emulator] TCP server listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[DMC4143 Emulator] Client connected from {addr}")
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.running:
                    print(f"[DMC4143 Emulator] Server error: {e}")
    
    def stop(self):
        """Stop the TCP server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.emulator.stop_update_loop()
        print("[DMC4143 Emulator] Server stopped")
    
    def _handle_client(self, client_socket, addr):
        """Handle a client connection"""
        try:
            # Set socket timeout to prevent hanging
            client_socket.settimeout(10.0)  # 10 second timeout for reading commands
            
            while self.running:
                # Receive command (CR/LF terminated)
                data = b""
                try:
                    while b"\r" not in data and b"\n" not in data:
                        chunk = client_socket.recv(1024)  # Read in larger chunks
                        if not chunk:
                            break
                        data += chunk
                        # Safety check: limit command size
                        if len(data) > 4096:
                            break
                except socket.timeout:
                    # Timeout reading command - continue to next iteration
                    continue
                
                if not data:
                    break
                
                # Decode command
                command = data.decode("ascii", errors="ignore").strip()
                if not command:
                    continue
                
                # Execute command
                response = self.emulator.parse_command(command)
                
                # Send response (CR/LF terminated)
                try:
                    if response:
                        client_socket.sendall((response + "\r\n").encode("ascii"))
                    else:
                        client_socket.sendall(b"\r\n")
                except (socket.error, BrokenPipeError):
                    # Client disconnected
                    break
                
        except Exception as e:
            print(f"[DMC4143 Emulator] Client {addr} error: {e}")
        finally:
            client_socket.close()
            print(f"[DMC4143 Emulator] Client {addr} disconnected")


# Python Mock Mode - Drop-in replacement for gclib.py()
class FakeGclib:
    """Drop-in mock replacement for gclib.py() class"""
    
    class py:
        """Fake gclib.py() instance"""
        
        def __init__(self):
            self.emulator = DMC4143Emulator()
            self.emulator.start_update_loop()
            self.connected = False
            self.connection_string = ""
            self.socket_client = None  # For TCP client mode
            self.use_tcp = False
        
        def GOpen(self, connection_string: str):
            """Open connection (mock or TCP client)"""
            self.connection_string = connection_string
            
            # Check if we should use TCP client mode
            # If address contains ":2323" or is "127.0.0.1" or "localhost", try TCP first
            addr_str = connection_string.split()[0]  # Get first part (address)
            if ":2323" in addr_str or addr_str in ("127.0.0.1", "localhost"):
                # Try to connect as TCP client to running server
                try:
                    self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket_client.settimeout(2.0)  # 2 second timeout
                    self.socket_client.connect(("127.0.0.1", 2323))
                    self.use_tcp = True
                    self.connected = True
                    print(f"[FakeGclib] Connected to TCP server at 127.0.0.1:2323")
                    return
                except (socket.error, ConnectionRefusedError, OSError) as e:
                    # TCP server not available, fall back to mock mode
                    print(f"[FakeGclib] TCP server not available ({e}), using mock mode")
                    if self.socket_client:
                        self.socket_client.close()
                        self.socket_client = None
            
            # Use local mock mode
            self.use_tcp = False
            self.connected = True
            print(f"[FakeGclib] Connected (mock mode): {connection_string}")
        
        def GClose(self):
            """Close connection"""
            self.connected = False
            
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
            
            if not self.use_tcp:
                self.emulator.stop_update_loop()
            
            print("[FakeGclib] Disconnected")
        
        def GCommand(self, command: str) -> str:
            """Send command and get response"""
            if not self.connected:
                raise RuntimeError("Not connected to controller")
            
            if self.use_tcp and self.socket_client:
                # TCP client mode - send to server
                try:
                    # Fix 5A: Ensure socket has timeout to prevent hanging
                    if self.socket_client.gettimeout() is None:
                        self.socket_client.settimeout(5.0)  # 5 second timeout for response (increased for reliability)
                    
                    # Send command with CR/LF
                    cmd_bytes = (command + "\r\n").encode("ascii")
                    self.socket_client.sendall(cmd_bytes)
                    
                    # Fix 5A: Read response in larger chunks with timeout
                    # Read until we get CR/LF terminator (handles fragmented responses)
                    response = b""
                    max_reads = 100  # Safety limit to prevent infinite loop
                    read_count = 0
                    
                    while b"\r\n" not in response and b"\n" not in response:
                        read_count += 1
                        if read_count > max_reads:
                            # Safety: prevent infinite loop
                            break
                        
                        try:
                            # Read larger chunks (4096 bytes) for efficiency
                            chunk = self.socket_client.recv(4096)
                            if not chunk:
                                # Connection closed
                                break
                            response += chunk
                            
                            # Check if we have complete response (CR/LF terminator)
                            if b"\r\n" in response or b"\n" in response:
                                break
                        except socket.timeout:
                            # Timeout waiting for response
                            # If we have some data, return it; otherwise raise error
                            if response:
                                break
                            raise RuntimeError(f"Timeout waiting for response to command: {command}")
                    
                    # Extract first complete response line (up to CR/LF)
                    if b"\r\n" in response:
                        response = response.split(b"\r\n")[0]
                    elif b"\n" in response:
                        response = response.split(b"\n")[0]
                    
                    # Decode and strip
                    response_str = response.decode("ascii", errors="ignore").strip()
                    return response_str
                    
                except socket.timeout as e:
                    # Timeout error
                    self.connected = False
                    if self.socket_client:
                        self.socket_client.close()
                        self.socket_client = None
                    raise RuntimeError(f"Connection timeout: {e}")
                except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                    # Connection lost
                    self.connected = False
                    if self.socket_client:
                        self.socket_client.close()
                        self.socket_client = None
                    raise RuntimeError(f"Connection lost: {e}")
            else:
                # Mock mode - use local emulator
                response = self.emulator.parse_command(command)
                return response
        
        def GInfo(self) -> str:
            """Get controller info"""
            if self.use_tcp:
                return "DMC-4143 Emulator v1.0 (TCP Server Mode)"
            return "DMC-4143 Emulator v1.0 Mock Mode"
        
        def GAddresses(self) -> Dict[str, str]:
            """Get available addresses (mock)"""
            return {
                "127.0.0.1": "DMC-4143 Emulator (Mock/TCP)",
            }


# Main entry point for TCP server mode
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DMC-4143 Controller Emulator")
    parser.add_argument("--server", action="store_true", help="Run in TCP server mode")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2323, help="Server port (default: 2323)")
    
    args = parser.parse_args()
    
    if args.server:
        server = DMC4143TCPServer(host=args.host, port=args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\n[DMC4143 Emulator] Shutting down...")
            server.stop()
    else:
        print("Usage: python dmc4143_emulator.py --server")
        print("Or import FakeGclib for Python mock mode")

