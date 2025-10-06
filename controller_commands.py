"""
Controller Command Functions for Galil Setup Tool

This module contains all the controller command functions that were previously
in main.py, organized for better code structure and maintainability.
"""

import time
import logging
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

class ControllerCommands:
    """Class containing all controller command functions"""
    
    def __init__(self, controller, log_callback=None):
        """
        Initialize the controller commands handler
        
        Args:
            controller: The Galil controller instance
            log_callback: Optional callback function for logging messages
        """
        self.controller = controller
        self.log_callback = log_callback or self._default_log
    
    def _default_log(self, message: str):
        """Default logging function if no callback provided"""
        print(message)
    
    def log(self, message: str):
        """Log a message using the callback"""
        self.log_callback(message)
    
    def test_basic_controller_communication(self) -> bool:
        """Test basic controller communication to ensure commands are working"""
        if not self.controller:
            return False
            
        try:
            # Test basic communication with a simple command
            response = self.controller.send_command("TPA").strip()
            if response == "?":
                self.log("WARNING: Basic controller communication test failed - controller may not be responding properly")
                return False
            elif response == "":
                self.log("WARNING: Basic controller communication test returned empty - controller may not be responding properly")
                return False
            else:
                self.log(f"Basic communication test passed - position response: {response}")
                return True
        except Exception as e:
            self.log(f"ERROR: Basic communication test failed: {e}")
            return False
    
    def test_motor_type_commands(self) -> Dict[str, Any]:
        """Test various motor type command formats to find working syntax"""
        if not self.controller:
            return {"working_commands": [], "failed_commands": []}
        
        self.log("Testing motor type command formats...")
        
        # Test different command formats
        test_formats = [
            ("MTA=1", "servo motor - correct syntax"),
            ("MTA=-1", "servo motor reversed"),
            ("MTA=2", "stepper motor"),
            ("MTA=-2", "stepper motor reversed"),
            ("MTA=1", "brushless servo motor"),
            ("MTA", "query current setting"),
            ("MTA", "query current setting"),
            ("MT ?", "query all motor types"),
            ("MTA=?", "query axis A motor type")
        ]
        
        working_commands = []
        failed_commands = []
        
        for command, description in test_formats:
            try:
                response = self.controller.send_command(command).strip()
                if response == "?":
                    self.log(f"{command} ({description}): ERROR - question mark returned by controller")
                    failed_commands.append(command)
                elif response == "":
                    self.log(f"{command} ({description}): ''")
                else:
                    self.log(f"{command} ({description}): '{response}'")
                    working_commands.append(command)
            except Exception as e:
                self.log(f"{command} ({description}): ERROR - {e}")
                failed_commands.append(command)
        
        # Check for motor type discrepancy
        self.log("Checking motor type discrepancy...")
        try:
            mt_all = self.controller.send_command("MT ?").strip()
            self.log(f"MT ? (all axes): {mt_all}")
            
            mta_single = self.controller.send_command("MTA=?").strip()
            self.log(f"MTA=? (axis A only): {mta_single}")
            
            if mt_all != mta_single:
                self.log(f"⚠ WARNING: Motor type discrepancy detected!")
                self.log(f"  MT ? returns: {mt_all}")
                self.log(f"  MTA=? returns: {mta_single}")
        except Exception as e:
            self.log(f"Motor type discrepancy check failed: {e}")
        
        self.log(f"Found {len(working_commands)} working motor type commands")
        return {"working_commands": working_commands, "failed_commands": failed_commands}
    
    def test_motion_commands(self) -> Dict[str, Any]:
        """Test motion commands to verify they work"""
        if not self.controller:
            return {"working_commands": [], "failed_commands": []}
        
        self.log("Testing motion commands...")
        
        motion_commands = [
            ("PRA=100", "position relative"),
            ("PAA=100", "position absolute"),
            ("JGA=100", "jog"),
            ("BGA", "begin motion"),
            ("STA", "stop motion")
        ]
        
        working_commands = []
        failed_commands = []
        
        for command, description in motion_commands:
            try:
                response = self.controller.send_command(command).strip()
                if response == "?":
                    self.log(f"{command} ({description}): ERROR - question mark returned by controller")
                    failed_commands.append(command)
                elif response == "":
                    self.log(f"{command} ({description}): ''")
                    working_commands.append(command)
                else:
                    self.log(f"{command} ({description}): '{response}'")
                    working_commands.append(command)
            except Exception as e:
                self.log(f"{command} ({description}): ERROR - {e}")
                failed_commands.append(command)
        
        return {"working_commands": working_commands, "failed_commands": failed_commands}
    
    def test_software_limit_commands(self) -> Dict[str, Any]:
        """Test software limit commands"""
        if not self.controller:
            return {"working_commands": [], "failed_commands": []}
        
        self.log("Testing software limit commands...")
        
        limit_commands = [
            ("FL A=0", "forward limit"),
            ("BL A=0", "backward limit"),
            ("TL A=0", "torque limit"),
            ("MG _FLA", "query forward limit"),
            ("MG _BLA", "query backward limit")
        ]
        
        working_commands = []
        failed_commands = []
        
        for command, description in limit_commands:
            try:
                response = self.controller.send_command(command).strip()
                if response == "?":
                    self.log(f"{command} ({description}): ERROR - question mark returned by controller")
                    failed_commands.append(command)
                elif response == "":
                    self.log(f"{command} ({description}): ''")
                    working_commands.append(command)
                else:
                    self.log(f"{command} ({description}): '{response}'")
                    working_commands.append(command)
            except Exception as e:
                self.log(f"{command} ({description}): ERROR - {e}")
                failed_commands.append(command)
        
        return {"working_commands": working_commands, "failed_commands": failed_commands}
    
    def detect_motor_on_axis(self, axis: str) -> bool:
        """Detect if a motor is connected and responding on the specified axis"""
        if not self.controller:
            return False
            
        try:
            # Method 1: Try to read position - if it returns "?" or fails, no motor
            try:
                pos_response = self.controller.send_command(f"TP {axis}").strip()
                if pos_response == "?":
                    self.log(f"Motor detection: Axis {axis} position returns '?' - no motor")
                    return False
                elif pos_response == "":
                    self.log(f"Motor detection: Axis {axis} position returns empty - no motor")
                    return False
                # Try to convert to int to ensure it's a valid position
                int(pos_response)
            except (ValueError, TypeError):
                self.log(f"Motor detection: Axis {axis} position not a valid number - no motor")
                return False
            
            # Method 2: Try to enable servo and see if it actually enables
            try:
                # Get initial servo status
                initial_servo = self.controller.send_command(f"MG _MO{axis}").strip()
                if initial_servo == "?":
                    self.log(f"Motor detection: Axis {axis} initial servo status returns '?' - no motor")
                    return False
                
                # Clear any errors before motor detection
                try:
                    self.controller.send_command("AB")  # Abort all motion
                    self.controller.send_command("ST")  # Stop all motion
                    self.controller.send_command("TE 0")  # Clear error register
                    time.sleep(0.1)
                except:
                    pass
                
                # Set motor type to servo (1) for proper detection
                try:
                    # Query current motor type
                    current_mt = self.controller.send_command(f"MT{axis}=?").strip()
                    if current_mt == "?":
                        self.log(f"Motor detection: Axis {axis} cannot query motor type - no motor")
                        return False
                    elif current_mt == "":
                        self.log(f"Motor detection: Axis {axis} motor type query returned empty - no motor")
                        return False
                    
                    self.log(f"Motor detection: Axis {axis} current motor type: {current_mt}")
                    
                    # Ensure motor is off before setting motor type (required by Galil)
                    self.controller.send_command(f"MO {axis}")  # Motor off
                    time.sleep(0.1)
                    
                    # Set motor type to servo (1) - this is required for servo motors
                    if current_mt != "1" and current_mt != "1.0":
                        self.log(f"Motor detection: Axis {axis} setting motor type to servo (MT=1)")
                        mt_response = self.controller.send_command(f"MT{axis}=1")  # Servo motor
                        if mt_response == "?":
                            self.log(f"Motor detection: Axis {axis} motor type command failed - no motor")
                            return False
                        elif mt_response == "":
                            self.log(f"Motor detection: Axis {axis} motor type set successfully (empty response)")
                        else:
                            self.log(f"Motor detection: Axis {axis} motor type set response: {mt_response}")
                        time.sleep(0.2)  # Give time for motor type to be set
                    else:
                        self.log(f"Motor detection: Axis {axis} motor type already set to servo (MT=1)")
                        
                    # Initialize brushless servo amplifier and motor if needed
                    try:
                        # BA command makes axis brushless (required before BZ)
                        ba_response = self.controller.send_command(f"BA {axis}")
                        if ba_response == "?":
                            self.log(f"Motor detection: Axis {axis} brushless amplifier setup failed")
                        elif ba_response == "":
                            self.log(f"Motor detection: Axis {axis} brushless amplifier setup successful (empty response)")
                        else:
                            self.log(f"Motor detection: Axis {axis} brushless amplifier setup response: {ba_response}")
                        time.sleep(0.1)
                        
                        # BZ command initializes commutation for brushless servos
                        bz_response = self.controller.send_command(f"BZ {axis}=-2")
                        if bz_response == "?":
                            self.log(f"Motor detection: Axis {axis} brushless zero initialization failed")
                        elif bz_response == "":
                            self.log(f"Motor detection: Axis {axis} brushless zero initialization successful (empty response)")
                        else:
                            self.log(f"Motor detection: Axis {axis} brushless zero initialization response: {bz_response}")
                        time.sleep(0.2)
                    except Exception as e:
                        self.log(f"Motor detection: Axis {axis} brushless initialization error: {e}")
                        
                except Exception as e:
                    self.log(f"Motor detection: Axis {axis} motor type setting error - no motor: {e}")
                    return False
                
                # Try to enable servo
                try:
                    sh_response = self.controller.send_command(f"SH {axis}")
                    if sh_response == "?":
                        self.log(f"Motor detection: Axis {axis} servo enable command failed - no motor")
                        return False
                    elif sh_response == "":
                        self.log(f"Motor detection: Axis {axis} servo enable command successful (empty response)")
                    else:
                        self.log(f"Motor detection: Axis {axis} servo enable command response: {sh_response}")
                    time.sleep(0.3)  # Give more time for servo to enable
                except Exception as e:
                    self.log(f"Motor detection: Axis {axis} servo enable command error - no motor: {e}")
                    return False
                
                # Method 3: Test motion parameters and small movement
                try:
                    # Set conservative motion parameters for servo detection
                    self.controller.send_command(f"SP {axis}=1000")   # Low speed
                    self.controller.send_command(f"AC {axis}=500")   # Low acceleration
                    self.controller.send_command(f"DC {axis}=500")   # Low deceleration
                    
                    # Verify parameters were set
                    speed_response = self.controller.send_command(f"MG _SP {axis}").strip()
                    if speed_response == "?":
                        self.log(f"Motor detection: Axis {axis} speed setting failed - no motor")
                        self.controller.send_command(f"MO {axis}")  # Disable servo
                        return False
                    elif speed_response == "":
                        self.log(f"Motor detection: Axis {axis} speed setting successful (empty response)")
                    else:
                        self.log(f"Motor detection: Axis {axis} speed setting successful - response: {speed_response}")
                except Exception as e:
                    self.log(f"Motor detection: Axis {axis} motion parameter test failed - no motor: {e}")
                    self.controller.send_command(f"MO {axis}")  # Disable servo
                    return False
                
                # Try a small relative move (100 encoder counts for servo detection)
                try:
                    pr_response = self.controller.send_command(f"PR{axis}=100")
                    if pr_response == "?":
                        self.log(f"Motor detection: Axis {axis} PR command failed - no motor: {pr_response}")
                        self.controller.send_command(f"MO {axis}")  # Disable servo
                        return False
                    elif pr_response == "":
                        self.log(f"Motor detection: Axis {axis} PR command successful (empty response)")
                    else:
                        self.log(f"Motor detection: Axis {axis} PR command response: {pr_response}")
                    
                    bg_response = self.controller.send_command(f"BG {axis}")
                    if bg_response == "?":
                        self.log(f"Motor detection: Axis {axis} BG command failed - no motor: {bg_response}")
                        self.controller.send_command(f"MO {axis}")  # Disable servo
                        return False
                    elif bg_response == "":
                        self.log(f"Motor detection: Axis {axis} BG command successful (empty response)")
                    else:
                        self.log(f"Motor detection: Axis {axis} BG command response: {bg_response}")
                    
                    time.sleep(0.5)  # Shorter wait for servo movement
                    
                    # Check if position changed
                    final_pos = int(self.controller.send_command(f"TP {axis}").strip())
                    if final_pos != int(pos_response):
                        self.log(f"Motor detection: Axis {axis} position changed from {pos_response} to {final_pos} - MOTOR DETECTED")
                        self.controller.send_command(f"MO {axis}")  # Disable servo
                        return True
                    else:
                        self.log(f"Motor detection: Axis {axis} position did not change - no motor movement")
                        self.controller.send_command(f"MO {axis}")  # Disable servo
                        return False
                        
                except Exception as e:
                    self.log(f"Motor detection: Axis {axis} motion test failed - no motor: {e}")
                    self.controller.send_command(f"MO {axis}")  # Disable servo
                    return False
                
            except Exception as e:
                self.log(f"Motor detection: Axis {axis} servo enable test failed - no motor: {e}")
                return False
                
        except Exception as e:
            self.log(f"Motor detection: Axis {axis} general error - no motor: {e}")
            return False
    
    def enable_all_servos(self) -> bool:
        """Enable servos for all axes"""
        if not self.controller:
            self.log("ERROR: Controller not connected")
            return False
            
        try:
            self.log("Enabling servos for all axes...")
            
            for axis in ["A", "B", "C", "D"]:
                try:
                    # First, ensure motor is off before setting motor type (required by Galil)
                    self.controller.send_command(f"MO {axis}")  # Motor off
                    time.sleep(0.1)
                    
                    # Set motor type to servo (1) - required for servo motors
                    mt_response = self.controller.send_command(f"MT{axis}=1")  # Servo motor (3-phased brushless)
                    if mt_response == "?":
                        self.log(f"Axis {axis}: Motor type command failed - {mt_response}")
                    elif mt_response == "":
                        self.log(f"Axis {axis}: Motor type set successfully (empty response)")
                    else:
                        self.log(f"Axis {axis}: Motor type set response: {mt_response}")
                    time.sleep(0.2)  # Give time for motor type to be set
                    
                    # Enable servo
                    self.controller.send_command(f"SH {axis}")
                    time.sleep(0.2)
                    
                    # Verify servo is enabled
                    servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                    if servo_status != "0":
                        self.log(f"Axis {axis}: Servo enabled (status: {servo_status})")
                    else:
                        self.log(f"Axis {axis}: WARNING - Servo may not be enabled (status: {servo_status})")
                        
                except Exception as e:
                    self.log(f"Axis {axis}: Error enabling servo - {e}")
            
            self.log("Servo enable operation completed")
            return True
            
        except Exception as e:
            error_msg = f"Enable all servos error: {str(e)}"
            self.log(f"ERROR: {error_msg}")
            return False
    
    def check_controller_status(self) -> Dict[str, Any]:
        """Check comprehensive controller status"""
        if not self.controller:
            return {"error": "Controller not connected"}
        
        try:
            self.log("Checking controller status...")
            
            # Check error status
            try:
                tc_detailed = self.controller.send_command("TC 1").strip()
                tc_code = self.controller.send_command("TC 0").strip()
                te_errors = self.controller.send_command("TE").strip()
                
                self.log(f"TC 1 (detailed error): {tc_detailed}")
                self.log(f"TC 0 (error code): {tc_code}")
                self.log(f"TE (position errors): {te_errors}")
                
                return {
                    "tc_detailed": tc_detailed,
                    "tc_code": tc_code,
                    "te_errors": te_errors
                }
            except Exception as e:
                self.log(f"Error during controller status check: {e}")
                return {"error": str(e)}
                
        except Exception as e:
            self.log(f"Controller status check failed: {e}")
            return {"error": str(e)}
    
    def run_automatic_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive automatic diagnostics"""
        if not self.controller:
            return {"error": "Controller not connected"}
        
        try:
            self.log("=== AUTOMATIC DIAGNOSTICS START ===")
            
            # Test basic communication
            comm_result = self.test_basic_controller_communication()
            if not comm_result:
                return {"error": "Basic communication failed"}
            
            # Test motor type commands
            mt_result = self.test_motor_type_commands()
            
            # Test motion commands
            motion_result = self.test_motion_commands()
            
            # Test software limit commands
            limit_result = self.test_software_limit_commands()
            
            # Check controller status
            status_result = self.check_controller_status()
            
            # Detect motors on all axes
            motor_detection_results = {}
            for axis in ["A", "B", "C", "D"]:
                motor_detection_results[axis] = self.detect_motor_on_axis(axis)
            
            self.log("=== AUTOMATIC DIAGNOSTICS COMPLETE ===")
            
            return {
                "communication": comm_result,
                "motor_type_commands": mt_result,
                "motion_commands": motion_result,
                "limit_commands": limit_result,
                "controller_status": status_result,
                "motor_detection": motor_detection_results
            }
            
        except Exception as e:
            self.log(f"Automatic diagnostics failed: {e}")
            return {"error": str(e)}
    
    def ensure_servo_enabled(self, axis: str) -> bool:
        """Ensure servo is enabled for the specified axis"""
        if not self.controller:
            return False
        
        try:
            # Check current servo status
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
            if servo_status == "0":
                # Servo is off, try to enable it
                self.controller.send_command(f"SH {axis}")
                time.sleep(0.3)
                
                # Check again
                servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
                if servo_status == "0":
                    self.log(f"WARNING: Could not enable servo for axis {axis}")
                    return False
                else:
                    self.log(f"Servo enabled for axis {axis} (status: {servo_status})")
                    return True
            else:
                self.log(f"Servo already enabled for axis {axis} (status: {servo_status})")
                return True
                
        except Exception as e:
            self.log(f"Error ensuring servo enabled for axis {axis}: {e}")
            return False
    
    def ensure_servo_enabled_after_motion(self, axis: str) -> bool:
        """Ensure servo is enabled after motion commands"""
        if not self.controller:
            return False
        
        try:
            # Check servo status after motion
            servo_status = self.controller.send_command(f"MG _MO{axis}").strip()
            if servo_status == "0":
                self.log(f"Re-enabling servo after motion...")
                self.controller.send_command(f"SH {axis}")
                time.sleep(0.1)
                return True
            return True
        except Exception as e:
            self.log(f"Error checking final servo status: {e}")
            return False
    
    def remove_axis_limits(self, axis):
        """Remove software limits for the specified axis"""
        try:
            if not self.controller:
                self.log(f"ERROR: No controller connected")
                return False
            
            # Clear software limits (SL=0 means no limits)
            sl_response = self.controller.send_command(f"SL{axis}=0")
            if sl_response == "?":
                self.log(f"Failed to remove software limits for axis {axis}")
                return False
            else:
                self.log(f"Successfully removed software limits for axis {axis}")
                return True
                
        except Exception as e:
            self.log(f"Error removing limits for axis {axis}: {e}")
            return False
