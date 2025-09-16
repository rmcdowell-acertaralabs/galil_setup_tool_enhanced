"""
Command Validator for DMC-4103 Controller

This module validates motor setup commands against the DMC-4103 command reference
to ensure all commands are correct and properly formatted.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class CommandValidation:
    """Result of command validation"""
    valid: bool
    command: str
    description: str
    error_message: Optional[str] = None
    warning_message: Optional[str] = None

class DMC4103CommandValidator:
    """Validator for DMC-4103 commands based on official command reference"""
    
    def __init__(self):
        """Initialize command validator with DMC-4103 command definitions"""
        self.valid_commands = self._load_command_reference()
        self.axis_commands = self._load_axis_commands()
        self.parameter_commands = self._load_parameter_commands()
    
    def _load_command_reference(self) -> Dict[str, Dict]:
        """Load DMC-4103 command reference"""
        return {
            # Motor Control Commands
            "MO": {"description": "Motor Off", "parameters": ["axis"], "required": True},
            "SH": {"description": "Servo Here (Enable)", "parameters": ["axis"], "required": True},
            "ST": {"description": "Stop Motion", "parameters": ["axis"], "required": False},
            "BG": {"description": "Begin Motion", "parameters": ["axis"], "required": True},
            "AM": {"description": "After Motion", "parameters": ["axis"], "required": True},
            
            # Position Commands
            "TP": {"description": "Tell Position", "parameters": ["axis"], "required": True},
            "DP": {"description": "Define Position", "parameters": ["axis", "value"], "required": True},
            "PA": {"description": "Position Absolute", "parameters": ["axis", "value"], "required": True},
            "PR": {"description": "Position Relative", "parameters": ["axis", "value"], "required": True},
            "JG": {"description": "Jog", "parameters": ["axis", "value"], "required": True},
            
            # Brushless Motor Commands
            "BA": {"description": "Brushless Amplifier", "parameters": ["axis"], "required": True},
            "BM": {"description": "Brushless Modulo", "parameters": ["axis", "value"], "required": True},
            "BX": {"description": "Brushless eXchange", "parameters": ["axis", "value"], "required": True},
            "BZ": {"description": "Brushless Zero", "parameters": ["axis", "value"], "required": True},
            "BC": {"description": "Brushless Calibrate", "parameters": ["axis"], "required": True},
            "BI": {"description": "Brushless Input", "parameters": ["axis", "value"], "required": True},
            "QH": {"description": "Query Hall", "parameters": ["axis"], "required": True},
            
            # Encoder Commands
            "CE": {"description": "Count Enable", "parameters": ["axis", "value"], "required": True},
            "AL": {"description": "After Latch", "parameters": ["axis"], "required": True},
            "RL": {"description": "Read Latch", "parameters": ["axis"], "required": True},
            
            # Safety Commands
            "OE": {"description": "Overtravel Enable", "parameters": ["axis", "value"], "required": True},
            "ER": {"description": "Error Limit", "parameters": ["axis", "value"], "required": True},
            
            # System Commands
            "BN": {"description": "Burn", "parameters": [], "required": False},
            "RS": {"description": "Reset", "parameters": [], "required": False},
            "MG": {"description": "Message", "parameters": ["variable"], "required": True},
            "WT": {"description": "Wait", "parameters": ["time"], "required": True},
        }
    
    def _load_axis_commands(self) -> List[str]:
        """Load commands that require axis parameter"""
        return ["MO", "SH", "ST", "BG", "AM", "TP", "DP", "PA", "PR", "JG", 
                "BA", "BM", "BX", "BZ", "BC", "BI", "QH", "CE", "AL", "RL", "OE", "ER"]
    
    def _load_parameter_commands(self) -> List[str]:
        """Load commands that require parameter values"""
        return ["DP", "PA", "PR", "JG", "BM", "BX", "BZ", "BI", "CE", "ER", "WT"]
    
    def validate_command(self, command: str) -> CommandValidation:
        """
        Validate a single command against DMC-4103 reference
        
        Args:
            command: Command string to validate (e.g., "MOA", "BMA=2500")
            
        Returns:
            CommandValidation object with validation results
        """
        try:
            # Parse command
            if "=" in command:
                cmd_part, value_part = command.split("=", 1)
                value = value_part.strip()
            elif "<" in command and ">" in command:
                # Handle commands like BX<1000> or BZ<200>100
                cmd_part = command.split("<")[0].strip()
                value = command[command.find("<"):command.find(">")+1]
            elif " " in command and not "=" in command:
                # Handle commands like "WT 1000" or "QH A"
                parts = command.split(" ", 1)
                cmd_part = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else None
            else:
                cmd_part = command.strip()
                value = None
            
            # Extract base command and axis
            base_cmd = None
            axis = None
            
            # Find base command
            for cmd in self.valid_commands.keys():
                if cmd_part.startswith(cmd):
                    base_cmd = cmd
                    remaining = cmd_part[len(cmd):].strip()
                    # For commands with spaces, the axis comes after the space
                    if " " in command and not "=" in command:
                        # Commands like "QH A" - axis is in the value part
                        axis = value
                    else:
                        # Commands like "MOA" - axis is attached to command
                        axis = remaining
                    break
            
            if not base_cmd:
                return CommandValidation(
                    False, command, "Unknown command",
                    f"Command '{base_cmd}' not found in DMC-4103 reference"
                )
            
            # Validate axis parameter
            if base_cmd in self.axis_commands:
                # Special case: BX and BZ can be used without axis for hold time setting
                if base_cmd in ["BX", "BZ"] and value and value.startswith("<") and value.endswith(">"):
                    # This is a hold time setting command like "BX<1000>"
                    pass  # No axis required
                elif not axis or axis not in ['A', 'B', 'C', 'D']:
                    return CommandValidation(
                        False, command, self.valid_commands[base_cmd]["description"],
                        f"Command '{base_cmd}' requires valid axis (A, B, C, D), got '{axis}'"
                    )
            
            # Validate parameter value
            if base_cmd in self.parameter_commands:
                # Special case: BX and BZ hold time commands don't need parameter validation
                if base_cmd in ["BX", "BZ"] and value and value.startswith("<") and value.endswith(">"):
                    # This is a hold time setting command - validate the bracket format
                    validation_result = self._validate_parameter(base_cmd, value)
                    if not validation_result[0]:
                        return CommandValidation(
                            False, command, self.valid_commands[base_cmd]["description"],
                            validation_result[1]
                        )
                elif value is None:
                    return CommandValidation(
                        False, command, self.valid_commands[base_cmd]["description"],
                        f"Command '{base_cmd}' requires a parameter value"
                    )
                else:
                    # Validate parameter format
                    validation_result = self._validate_parameter(base_cmd, value)
                    if not validation_result[0]:
                        return CommandValidation(
                            False, command, self.valid_commands[base_cmd]["description"],
                            validation_result[1]
                        )
            
            # Check for warnings
            warning = self._check_warnings(base_cmd, axis, value)
            
            return CommandValidation(
                True, command, self.valid_commands[base_cmd]["description"],
                warning_message=warning
            )
            
        except Exception as e:
            return CommandValidation(
                False, command, "Parse error",
                f"Failed to parse command: {str(e)}"
            )
    
    def _validate_parameter(self, command: str, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate parameter value for specific command
        
        Args:
            command: Base command
            value: Parameter value
            
        Returns:
            Tuple of (valid, error_message)
        """
        try:
            if command in ["DP", "PA", "PR", "JG", "BM"]:
                # Numeric parameters
                float(value)
                return True, None
            
            elif command in ["BX", "BZ"]:
                # BX and BZ can have numeric values or bracket values
                if value.startswith("<") and value.endswith(">"):
                    # Handle bracket parameters in the bracket validation section
                    return True, None
                else:
                    # Numeric value
                    float(value)
                    return True, None
            
            elif command == "ER":
                # Error limit - can be numeric or variable like _BMA
                if value.startswith("_"):
                    # Variable reference (like _BMA)
                    return True, None
                else:
                    # Numeric value
                    float(value)
                    return True, None
            
            elif command == "BI":
                # Brushless Input - can be -1 or input number
                if value == "-1":
                    return True, None
                try:
                    int_val = int(value)
                    if 1 <= int_val <= 8:
                        return True, None
                    else:
                        return False, "BI parameter must be -1 or input number 1-8"
                except ValueError:
                    return False, "BI parameter must be -1 or integer 1-8"
            
            elif command == "CE":
                # Count Enable - 0 or 2
                if value in ["0", "2"]:
                    return True, None
                else:
                    return False, "CE parameter must be 0 (normal) or 2 (reversed)"
            
            elif command == "OE":
                # Overtravel Enable - 0 or 1
                if value in ["0", "1"]:
                    return True, None
                else:
                    return False, "OE parameter must be 0 (disabled) or 1 (enabled)"
            
            elif command == "WT":
                # Wait time - positive number
                time_val = float(value)
                if time_val > 0:
                    return True, None
                else:
                    return False, "WT parameter must be positive"
            
            elif command in ["BX", "BZ"] and value and value.startswith("<") and value.endswith(">"):
                # Angle bracket parameters like <1000> or <200>100
                bracket_content = value[1:-1]  # Remove < and >
                if ">" in bracket_content:
                    # Two parameters like <200>100
                    parts = bracket_content.split(">")
                    if len(parts) == 2:
                        try:
                            float(parts[0])
                            float(parts[1])
                            return True, None
                        except ValueError:
                            return False, f"Invalid bracket parameters: {value}"
                    else:
                        return False, f"Invalid bracket format: {value}"
                else:
                    # Single parameter like <1000>
                    try:
                        float(bracket_content)
                        return True, None
                    except ValueError:
                        return False, f"Invalid bracket parameter: {value}"
            
            else:
                return True, None
                
        except ValueError:
            return False, f"Invalid numeric value: {value}"
    
    def _check_warnings(self, command: str, axis: Optional[str], value: Optional[str]) -> Optional[str]:
        """
        Check for potential warnings in command usage
        
        Args:
            command: Base command
            axis: Axis parameter
            value: Parameter value
            
        Returns:
            Warning message if any
        """
        warnings = []
        
        if command == "BX" and value:
            try:
                bx_val = float(value)
                if abs(bx_val) < 2:
                    warnings.append("BX voltage may be too low, consider using -3 or -4")
                elif abs(bx_val) > 5:
                    warnings.append("BX voltage may be too high, risk of damage")
            except ValueError:
                pass
        
        if command == "BZ" and value:
            try:
                bz_val = float(value)
                if abs(bz_val) < 2:
                    warnings.append("BZ voltage may be too low, consider using -3 or -4")
                elif abs(bz_val) > 5:
                    warnings.append("BZ voltage may be too high, risk of damage")
            except ValueError:
                pass
        
        if command == "BM" and value:
            try:
                bm_val = float(value)
                if bm_val < 100:
                    warnings.append("BM value seems low, verify encoder counts and pole pairs")
                elif bm_val > 10000:
                    warnings.append("BM value seems high, verify encoder counts and pole pairs")
            except ValueError:
                pass
        
        return "; ".join(warnings) if warnings else None
    
    def validate_motor_setup_sequence(self, commands: List[str]) -> List[CommandValidation]:
        """
        Validate a sequence of motor setup commands
        
        Args:
            commands: List of command strings
            
        Returns:
            List of CommandValidation objects
        """
        results = []
        for command in commands:
            result = self.validate_command(command)
            results.append(result)
        return results
    
    def get_command_help(self, command: str) -> str:
        """
        Get help information for a command
        
        Args:
            command: Command to get help for
            
        Returns:
            Help string
        """
        if command in self.valid_commands:
            cmd_info = self.valid_commands[command]
            help_text = f"{command}: {cmd_info['description']}\n"
            
            if "parameters" in cmd_info:
                help_text += f"Parameters: {', '.join(cmd_info['parameters'])}\n"
            
            # Add specific examples
            if command == "MO":
                help_text += "Example: MOA (turn off motor A)\n"
            elif command == "SH":
                help_text += "Example: SHA (enable servo A)\n"
            elif command == "BM":
                help_text += "Example: BMA=2500 (set brushless modulo for axis A)\n"
            elif command == "BX":
                help_text += "Example: BXA=-3 (initialize commutation with -3V)\n"
            elif command == "CE":
                help_text += "Example: CEA=0 (normal encoder polarity), CEA=2 (reversed)\n"
            
            return help_text
        else:
            return f"Unknown command: {command}"
    
    def get_all_commands(self) -> List[str]:
        """Get list of all valid commands"""
        return list(self.valid_commands.keys())
    
    def get_axis_commands(self) -> List[str]:
        """Get list of commands that require axis parameter"""
        return self.axis_commands.copy()
    
    def get_parameter_commands(self) -> List[str]:
        """Get list of commands that require parameters"""
        return self.parameter_commands.copy()
