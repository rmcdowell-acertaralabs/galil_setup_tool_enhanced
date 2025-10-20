"""
Proper Command Validator for DMC-4103 Controller

This module provides a complete implementation of command validation
based on the DMC-4103 command reference.
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, List, Set, Tuple, Any
from enum import Enum

class ValidationResult(Enum):
    """Validation result types"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"

@dataclass
class CommandValidation:
    """Command validation result"""
    valid: bool
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    description: str = ""
    result_type: ValidationResult = ValidationResult.VALID

class DMC4103CommandValidator:
    """DMC-4103 Command Validator - Complete implementation"""
    
    def __init__(self):
        """Initialize the command validator with DMC-4103 command definitions"""
        self.valid_commands = self._build_command_database()
        self.axis_commands = self._build_axis_commands()
        self.global_commands = self._build_global_commands()
        
    def _build_command_database(self) -> Dict[str, Dict[str, Any]]:
        """Build the complete DMC-4103 command database"""
        return {
            # Motion/Servo Commands
            "MO": {
                "description": "Motor Off",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": True
            },
            "SH": {
                "description": "Servo Here (Enable)",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "ST": {
                "description": "Stop Motion",
                "parameters": ["axis"],
                "axis_required": False,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": True
            },
            "BG": {
                "description": "Begin Motion",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "AM": {
                "description": "After Motion",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "AB": {
                "description": "Abort Motion",
                "parameters": ["value"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            
            # Positioning Commands
            "TP": {
                "description": "Tell Position",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "DP": {
                "description": "Define Position",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "PA": {
                "description": "Position Absolute",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "PR": {
                "description": "Position Relative",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "JG": {
                "description": "Jog",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            
            # Motion Profile Commands
            "SP": {
                "description": "Speed",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "AC": {
                "description": "Acceleration",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "DC": {
                "description": "Deceleration",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            
            # PID/Tuning Commands
            "KP": {
                "description": "Proportional Gain",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "KI": {
                "description": "Integral Gain",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "KD": {
                "description": "Derivative Gain",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "TL": {
                "description": "Torque Limit",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "TK": {
                "description": "Peak Torque Limit",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "AG": {
                "description": "Amplifier Gain",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "AU": {
                "description": "Current Loop Gain",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            
            # Motor Type Commands
            "MT": {
                "description": "Motor Type",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "CE": {
                "description": "Encoder Configuration",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            
            # Brushless Commands
            "BA": {
                "description": "Brushless Enable",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "BM": {
                "description": "Brushless Modulo",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "BI": {
                "description": "Brushless Initialize",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "BC": {
                "description": "Brushless Calibrate",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "BX": {
                "description": "Brushless Initialize with Hold",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "BZ": {
                "description": "Brushless Drive to Electrical Zero",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            
            # Safety/Limit Commands
            "OE": {
                "description": "Off-on-Error",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": True
            },
            "ER": {
                "description": "Error Limit",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": True
            },
            "FL": {
                "description": "Find Limit",
                "parameters": ["axis"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "BL": {
                "description": "Backlash",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            "CN": {
                "description": "Configure",
                "parameters": ["axis", "value"],
                "axis_required": True,
                "valid_axes": ["A", "B", "C", "D"],
                "global_allowed": False
            },
            
            # System Commands
            "BN": {
                "description": "Burn Settings",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "RS": {
                "description": "Reset",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "AZ": {
                "description": "Clear Errors",
                "parameters": ["value"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "TC": {
                "description": "Tell Error Code",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "TE": {
                "description": "Tell Error",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "MG": {
                "description": "Message",
                "parameters": ["expression"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "ID": {
                "description": "Identify",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            
            # Network Commands
            "IA": {
                "description": "IP Address",
                "parameters": ["address"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "DH": {
                "description": "DHCP",
                "parameters": ["value"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "SM": {
                "description": "Subnet Mask",
                "parameters": ["address"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "GW": {
                "description": "Gateway",
                "parameters": ["address"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "TH": {
                "description": "Network Info",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "IH": {
                "description": "IP Hostname",
                "parameters": ["hostname"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "WH": {
                "description": "Web Hostname",
                "parameters": ["hostname"],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            },
            "CF": {
                "description": "Configure Network",
                "parameters": [],
                "axis_required": False,
                "valid_axes": [],
                "global_allowed": True
            }
        }
    
    def _build_axis_commands(self) -> Set[str]:
        """Build set of commands that require axis specification"""
        return {cmd for cmd, info in self.valid_commands.items() 
                if info.get("axis_required", False)}
    
    def _build_global_commands(self) -> Set[str]:
        """Build set of commands that can be used globally"""
        return {cmd for cmd, info in self.valid_commands.items() 
                if info.get("global_allowed", False)}
    
    def validate_command(self, command: str) -> CommandValidation:
        """
        Validate a Galil command against DMC-4103 specifications
        
        Args:
            command: The command string to validate
            
        Returns:
            CommandValidation object with validation results
        """
        if not command or not command.strip():
            return CommandValidation(
                valid=False,
                error_message="Empty command",
                description="Command cannot be empty"
            )
        
        command = command.strip()
        
        # Handle multi-command sequences (semicolon separated)
        if ';' in command:
            commands = [cmd.strip() for cmd in command.split(';') if cmd.strip()]
            for cmd in commands:
                result = self.validate_command(cmd)
                if not result.valid:
                    return result
            return CommandValidation(
                valid=True,
                description=f"Multi-command sequence with {len(commands)} commands"
            )
        
        # Parse command components - handle both space and concatenated formats
        # Examples: "MTA=1", "MT A=1", "SHA", "SH A"
        base_command = self._extract_base_command(command)
        
        # Check if command exists
        if base_command not in self.valid_commands:
            return CommandValidation(
                valid=False,
                error_message=f"Unknown command: {base_command}",
                description=f"Command '{base_command}' is not recognized"
            )
        
        cmd_info = self.valid_commands[base_command]
        
        # Validate axis specification
        axis_validation = self._validate_axis_specification(command, cmd_info)
        if not axis_validation.valid:
            return axis_validation
        
        # Validate parameters
        param_validation = self._validate_parameters(command, cmd_info)
        if not param_validation.valid:
            return param_validation
        
        # Validate special formats (IP addresses, etc.)
        format_validation = self._validate_special_formats(command, cmd_info)
        if not format_validation.valid:
            return format_validation
        
        return CommandValidation(
            valid=True,
            description=cmd_info["description"],
            warning_message=format_validation.warning_message
        )
    
    def _validate_axis_specification(self, command: str, cmd_info: Dict[str, Any]) -> CommandValidation:
        """Validate axis specification for commands that require it"""
        if not cmd_info.get("axis_required", False):
            return CommandValidation(valid=True)
        
        # Check for axis specification patterns
        axis_patterns = [
            r'^[A-Z]{2,3}[A-D]',  # Command with axis (e.g., MTA, SHA)
            r'^[A-Z]{2,3}\s+[A-D]',  # Command space axis (e.g., MO A)
            r'^[A-Z]{2,3}[A-D]\s*=',  # Command axis equals (e.g., MTA=1)
            r'^[A-Z]{2,3}\s+[A-D]\s*=',  # Command space axis equals (e.g., MO A=1)
        ]
        
        has_axis = any(re.match(pattern, command.upper()) for pattern in axis_patterns)
        
        if not has_axis:
            return CommandValidation(
                valid=False,
                error_message=f"Command '{command}' requires axis specification",
                description=f"Command requires axis (A, B, C, or D)"
            )
        
        # Extract and validate axis
        axis_match = re.search(r'([A-D])', command.upper())
        if axis_match:
            axis = axis_match.group(1)
            valid_axes = cmd_info.get("valid_axes", ["A", "B", "C", "D"])
            if axis not in valid_axes:
                return CommandValidation(
                    valid=False,
                    error_message=f"Invalid axis '{axis}' for command",
                    description=f"Valid axes: {', '.join(valid_axes)}"
                )
        
        return CommandValidation(valid=True)
    
    def _validate_parameters(self, command: str, cmd_info: Dict[str, Any]) -> CommandValidation:
        """Validate command parameters"""
        expected_params = cmd_info.get("parameters", [])
        
        if not expected_params:
            return CommandValidation(valid=True)
        
        # Check for parameter patterns
        if '=' in command:
            # Command with assignment (e.g., MTA=1, KPA=6.0)
            param_part = command.split('=', 1)[1].strip()
            if not param_part:
                return CommandValidation(
                    valid=False,
                    error_message="Missing parameter value after '='",
                    description="Command requires a parameter value"
                )
        elif len(command.split()) > 1:
            # Command with space-separated parameters
            param_part = ' '.join(command.split()[1:])
            if not param_part:
                return CommandValidation(
                    valid=False,
                    error_message="Missing parameters",
                    description="Command requires parameters"
                )
        
        return CommandValidation(valid=True)
    
    def _validate_special_formats(self, command: str, cmd_info: Dict[str, Any]) -> CommandValidation:
        """Validate special command formats (IP addresses, etc.)"""
        base_command = command.split()[0].upper()
        warning = None
        
        # IP address validation for network commands
        if base_command in ["IA", "SM", "GW"]:
            if '=' in command:
                param_part = command.split('=', 1)[1].strip()
                # Check for comma-separated IP format (Galil standard)
                if ',' in param_part:
                    parts = param_part.split(',')
                    if len(parts) == 4:
                        try:
                            for part in parts:
                                val = int(part.strip())
                                if val < 0 or val > 255:
                                    return CommandValidation(
                                        valid=False,
                                        error_message=f"Invalid IP component: {val}",
                                        description="IP components must be 0-255"
                                    )
                        except ValueError:
                            return CommandValidation(
                                valid=False,
                                error_message="Invalid IP format",
                                description="IP must be comma-separated numbers (e.g., 192,168,1,100)"
                            )
                    else:
                        return CommandValidation(
                            valid=False,
                            error_message="Invalid IP format",
                            description="IP must have 4 comma-separated components"
                        )
                else:
                    warning = "Consider using comma-separated IP format (e.g., 192,168,1,100)"
        
        return CommandValidation(valid=True, warning_message=warning)
    
    def get_all_commands(self) -> List[str]:
        """Get list of all valid commands"""
        return list(self.valid_commands.keys())
    
    def get_command_info(self, command: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific command"""
        return self.valid_commands.get(command.upper())
    
    def is_axis_command(self, command: str) -> bool:
        """Check if command requires axis specification"""
        base_command = self._extract_base_command(command)
        return base_command in self.axis_commands
    
    def is_global_command(self, command: str) -> bool:
        """Check if command can be used globally"""
        base_command = self._extract_base_command(command)
        return base_command in self.global_commands
    
    def _extract_base_command(self, command: str) -> str:
        """Extract base command from various formats"""
        command = command.strip().upper()
        
        # Handle concatenated format (e.g., "MTA=1", "SHA", "TPA")
        # Look for command + axis pattern
        for cmd in self.valid_commands.keys():
            for axis in ["A", "B", "C", "D"]:
                # Check for concatenated format
                if command.startswith(cmd + axis):
                    return cmd
                # Check for space format
                if command.startswith(cmd + " " + axis):
                    return cmd
        
        # Fallback to first word
        parts = command.split()
        if parts:
            return parts[0]
        
        return command
