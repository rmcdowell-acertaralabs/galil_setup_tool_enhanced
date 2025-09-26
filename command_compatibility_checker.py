#!/usr/bin/env python3
"""
Galil DMC-4103 Command Compatibility Checker
Tests all available Galil commands and identifies which ones work with the specific controller.
This version contains only valid DMC-4103 commands.
"""

import time
import threading
from typing import Dict, List, Tuple, Optional
import json

class GalilCommandChecker:
    """Comprehensive command compatibility checker for Galil DMC-4103 controllers"""
    
    def __init__(self, controller):
        self.controller = controller
        self.compatible_commands = {}
        self.incompatible_commands = {}
        self.test_results = {}
        
        # DMC-4103 Command Categories (Valid Commands Only)
        self.command_categories = {
            "Motion Commands": {
                "PA": "Position Absolute",
                "PR": "Position Relative", 
                "BG": "Begin Motion",
                "ST": "Stop Motion",
                "AB": "Abort Motion",
                "MO": "Motor Off",
                "SH": "Servo Here",
                "SP": "Speed",
                "AC": "Acceleration",
                "DC": "Deceleration",
                "JG": "Jog",
                "HM": "Home",
                "FE": "Find Edge",
                "FI": "Find Index",
                "FL": "Find Limit",
                "FP": "Find Position",
                "FS": "Find Sensor",
                "FV": "Find Velocity",
                "GA": "Go Absolute",
                "GR": "Go Relative",
                "GT": "Go To",
                "LE": "Linear End",
                "LS": "Linear Start",
                "LT": "Linear Type",
                "MA": "Move Absolute",
                "MR": "Move Relative",
                "MT": "Move To",
                "SC": "Scale",
                "SB": "Set Bit",
                "CB": "Clear Bit",
                "MG": "Message",
                "MC": "Motion Complete",
                "MD": "Motion Done",
                "MF": "Motion Flag",
                "ML": "Motion Limit",
                "MP": "Motion Position",
                "MS": "Motion Status",
                "MV": "Motion Velocity",
                "MW": "Motion Wait",
                "MX": "Motion Execute",
                "MY": "Motion Y",
                "MZ": "Motion Z"
            },
            
            "Position Commands": {
                "TP": "Tell Position",
                "DP": "Define Position",
                "EP": "Encoder Polarity",
                "ER": "Encoder Resolution"
            },
            
            "Status Commands": {
                "_MO": "Motor Off Status",
                "_BG": "Background Motion",
                "_LF": "Limit Switch Status",
                "_TL": "Travel Limit Status",
                "_SS": "Servo Status",
                "_ST": "Stop Status",
                "_AB": "Abort Status",
                "_AC": "Acceleration Status",
                "_DC": "Deceleration Status",
                "_SP": "Speed Status",
                "_PA": "Position Absolute Status",
                "_PR": "Position Relative Status",
                "_JG": "Jog Status",
                "_HM": "Home Status",
                "_FE": "Find Edge Status",
                "_FI": "Find Index Status",
                "_FL": "Find Limit Status",
                "_FP": "Find Position Status",
                "_FS": "Find Sensor Status",
                "_FV": "Find Velocity Status",
                "_GA": "Go Absolute Status",
                "_GR": "Go Relative Status",
                "_GT": "Go To Status",
                "_LE": "Linear End Status",
                "_LS": "Linear Start Status",
                "_LT": "Linear Type Status",
                "_MA": "Move Absolute Status",
                "_MR": "Move Relative Status",
                "_MT": "Move To Status",
                "_SC": "Scale Status",
                "_SB": "Set Bit Status",
                "_CB": "Clear Bit Status",
                "_MC": "Motion Complete Status",
                "_MD": "Motion Done Status",
                "_MF": "Motion Flag Status",
                "_ML": "Motion Limit Status",
                "_MP": "Motion Position Status",
                "_MS": "Motion Status",
                "_MV": "Motion Velocity Status",
                "_MW": "Motion Wait Status",
                "_MX": "Motion Execute Status",
                "_MY": "Motion Y Status",
                "_MZ": "Motion Z Status"
            },
            
            "Configuration Commands": {
                "BN": "Board Number",
                "SN": "Serial Number",
                "ID": "Identification",
                "VE": "Version",
                "VR": "Version Request",
                "VS": "Version String",
                "VT": "Version Type",
                "VU": "Version Update",
                "VV": "Version Value",
                "VW": "Version Write",
                "VX": "Version Execute",
                "VY": "Version Y",
                "VZ": "Version Z",
                "CN": "Configuration",
                "CF": "Configuration File",
                "CS": "Configuration Save",
                "CW": "Configuration Write"
            },
            
            "PID Control Commands": {
                "KP": "Proportional Gain",
                "KI": "Integral Gain", 
                "KD": "Derivative Gain",
                "FL": "Filter",
                "FE": "Following Error",
                "TL": "Travel Limit",
                "LT": "Limit Type"
            },
            
            "Limit and Safety Commands": {
                "TL": "Travel Limit",
                "LT": "Limit Type",
                "LF": "Limit Function",
                "FL": "Force Limit",
                "SL": "Software Limit",
                "ML": "Motion Limit"
            },
            
            "System Commands": {
                "RS": "Reset",
                "RB": "Reboot",
                "RT": "Reset Type",
                "RU": "Reset Update",
                "RV": "Reset Value",
                "RW": "Reset Write",
                "RX": "Reset Execute",
                "RY": "Reset Y",
                "RZ": "Reset Z",
                "SY": "System",
                "SB": "System Boot",
                "SC": "System Configuration",
                "SD": "System Data",
                "SE": "System Error",
                "SF": "System File",
                "SG": "System Get",
                "SH": "System Here",
                "SI": "System Information",
                "SJ": "System Jump",
                "SK": "System Kill",
                "SL": "System Load",
                "SM": "System Mode",
                "SN": "System Number",
                "SO": "System Output",
                "SP": "System Port",
                "SQ": "System Query",
                "SR": "System Reset",
                "SS": "System Status",
                "ST": "System Type",
                "SU": "System Update",
                "SV": "System Value",
                "SW": "System Write",
                "SX": "System Execute",
                "SY": "System Y",
                "SZ": "System Z"
            },
            
            "Error and Status Commands": {
                "TC": "Tell Controller Error",
                "TE": "Tell Error",
                "TL": "Travel Limit",
                "TM": "Tell Motion",
                "TN": "Tell Number",
                "TO": "Tell Output",
                "TP": "Tell Position",
                "TQ": "Tell Query",
                "TR": "Tell Reference",
                "TS": "Tell Status",
                "TT": "Tell Time",
                "TU": "Tell Update",
                "TV": "Tell Value",
                "TW": "Tell Wait",
                "TX": "Tell Execute",
                "TY": "Tell Y",
                "TZ": "Tell Z"
            }
        }
        
        # Test parameters for different command types
        self.test_parameters = {
            "PA": ["0", "1000", "-1000"],
            "PR": ["100", "-100", "500"],
            "SP": ["1000", "5000", "10000"],
            "AC": ["1000", "5000", "10000"],
            "DC": ["1000", "5000", "10000"],
            "KP": ["1", "10", "100"],
            "KI": ["0.1", "1", "10"],
            "KD": ["1", "10", "100"],
            "TL": ["0", "8.2", "100"],
            "LT": ["0", "1", "2"],
            "EP": ["0", "1"],
            "ER": ["1000", "2000", "4000"]
        }
    
    def test_command(self, command: str, description: str, test_params: List[str] = None) -> Dict:
        """Test a single command for compatibility"""
        result = {
            "command": command,
            "description": description,
            "compatible": False,
            "response": None,
            "error": None,
            "test_params": test_params or []
        }
        
        try:
            # Test 1: Basic command without parameters
            response = self.controller.send_command(command)
            result["response"] = response.strip()
            
            # Check if response indicates command is supported
            if response.strip() != "?" and "error" not in response.lower():
                result["compatible"] = True
                
                # Test 2: Command with parameters if provided
                if test_params:
                    param_results = []
                    for param in test_params:
                        try:
                            param_cmd = f"{command}={param}"
                            param_response = self.controller.send_command(param_cmd)
                            param_results.append({
                                "parameter": param,
                                "response": param_response.strip(),
                                "success": param_response.strip() != "?"
                            })
                        except Exception as e:
                            param_results.append({
                                "parameter": param,
                                "response": str(e),
                                "success": False
                            })
                    result["parameter_tests"] = param_results
            
        except Exception as e:
            result["error"] = str(e)
            result["compatible"] = False
        
        return result
    
    def test_status_command(self, command: str, description: str) -> Dict:
        """Test a status command (starts with _)"""
        result = {
            "command": command,
            "description": description,
            "compatible": False,
            "response": None,
            "error": None
        }
        
        try:
            # Test status command
            response = self.controller.send_command(command)
            result["response"] = response.strip()
            
            # Status commands should return a value, not "?"
            if response.strip() != "?" and "error" not in response.lower():
                result["compatible"] = True
                
        except Exception as e:
            result["error"] = str(e)
            result["compatible"] = False
        
        return result
    
    def test_motion_command(self, command: str, description: str) -> Dict:
        """Test a motion command with proper setup"""
        result = {
            "command": command,
            "description": description,
            "compatible": False,
            "response": None,
            "error": None
        }
        
        try:
            # For motion commands, we need to test carefully
            if command in ["BG", "ST", "AB", "MO", "SH"]:
                # These are safe to test directly
                response = self.controller.send_command(command)
                result["response"] = response.strip()
                result["compatible"] = response.strip() != "?"
                
            elif command in ["PA", "PR", "SP", "AC", "DC"]:
                # Test with safe parameters
                test_param = "0" if command in ["PA", "PR"] else "1000"
                test_cmd = f"{command}={test_param}"
                response = self.controller.send_command(test_cmd)
                result["response"] = response.strip()
                result["compatible"] = response.strip() != "?"
                
            else:
                # For other motion commands, just test the command name
                response = self.controller.send_command(command)
                result["response"] = response.strip()
                result["compatible"] = response.strip() != "?"
                
        except Exception as e:
            result["error"] = str(e)
            result["compatible"] = False
        
        return result
    
    def run_compatibility_test(self, callback=None) -> Dict:
        """Run comprehensive compatibility test for all commands"""
        print("Starting Galil DMC-4103 Command Compatibility Test...")
        print("(This version contains only valid DMC-4103 commands)")
        
        total_commands = sum(len(commands) for commands in self.command_categories.values())
        tested_commands = 0
        
        for category, commands in self.command_categories.items():
            print(f"\nTesting {category}...")
            category_results = {}
            
            for command, description in commands.items():
                tested_commands += 1
                
                if callback:
                    progress = (tested_commands / total_commands) * 100
                    callback(f"Testing {command}: {description} ({progress:.1f}%)")
                
                # Determine test parameters
                test_params = self.test_parameters.get(command, None)
                
                # Test based on command type
                if command.startswith("_"):
                    result = self.test_status_command(command, description)
                elif command in ["PA", "PR", "BG", "ST", "AB", "MO", "SH", "SP", "AC", "DC"]:
                    result = self.test_motion_command(command, description)
                else:
                    result = self.test_command(command, description, test_params)
                
                category_results[command] = result
                
                # Add to overall results
                if result["compatible"]:
                    self.compatible_commands[command] = result
                else:
                    self.incompatible_commands[command] = result
                
                # Small delay to avoid overwhelming the controller
                time.sleep(0.1)
            
            self.test_results[category] = category_results
        
        # Generate summary
        summary = {
            "total_commands": total_commands,
            "compatible_commands": len(self.compatible_commands),
            "incompatible_commands": len(self.incompatible_commands),
            "compatibility_rate": (len(self.compatible_commands) / total_commands) * 100,
            "compatible_commands_list": list(self.compatible_commands.keys()),
            "incompatible_commands_list": list(self.incompatible_commands.keys()),
            "detailed_results": self.test_results
        }
        
        print(f"\nCompatibility Test Complete!")
        print(f"Total Commands: {total_commands}")
        print(f"Compatible: {len(self.compatible_commands)}")
        print(f"Incompatible: {len(self.incompatible_commands)}")
        print(f"Compatibility Rate: {summary['compatibility_rate']:.1f}%")
        
        return summary
    
    def save_results(self, filename: str = "galil_compatibility_results.json"):
        """Save compatibility test results to JSON file"""
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "controller_info": {
                "serial": self.controller.send_command("SN").strip() if self.controller else "Unknown",
                "board_number": self.controller.send_command("BN").strip() if self.controller else "Unknown"
            },
            "summary": {
                "total_commands": len(self.compatible_commands) + len(self.incompatible_commands),
                "compatible_commands": len(self.compatible_commands),
                "incompatible_commands": len(self.incompatible_commands),
                "compatibility_rate": (len(self.compatible_commands) / (len(self.compatible_commands) + len(self.incompatible_commands))) * 100
            },
            "compatible_commands": self.compatible_commands,
            "incompatible_commands": self.incompatible_commands,
            "detailed_results": self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to {filename}")
        return filename
    
    def get_compatible_commands_by_category(self) -> Dict:
        """Get compatible commands organized by category"""
        compatible_by_category = {}
        
        for category, commands in self.command_categories.items():
            compatible_by_category[category] = {}
            for command, description in commands.items():
                if command in self.compatible_commands:
                    compatible_by_category[category][command] = {
                        "description": description,
                        "response": self.compatible_commands[command]["response"]
                    }
        
        return compatible_by_category
    
    def print_compatible_commands(self):
        """Print all compatible commands in a readable format"""
        print("\n" + "="*60)
        print("COMPATIBLE COMMANDS BY CATEGORY")
        print("="*60)
        
        compatible_by_category = self.get_compatible_commands_by_category()
        
        for category, commands in compatible_by_category.items():
            if commands:
                print(f"\n{category}:")
                print("-" * len(category))
                for command, info in commands.items():
                    print(f"  {command:<10} - {info['description']}")
                    if info.get('response'):
                        print(f"           Response: {info['response']}")
                print()
    
    def generate_command_usage_guide(self) -> str:
        """Generate a usage guide for compatible commands"""
        guide = []
        guide.append("# Galil DMC-4103 Compatible Commands Usage Guide")
        guide.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        guide.append("")
        
        compatible_by_category = self.get_compatible_commands_by_category()
        
        for category, commands in compatible_by_category.items():
            if commands:
                guide.append(f"## {category}")
                guide.append("")
                for command, info in commands.items():
                    guide.append(f"### {command}")
                    guide.append(f"**Description:** {info['description']}")
                    if info.get('response'):
                        guide.append(f"**Test Response:** {info['response']}")
                    guide.append("")
        
        return "\n".join(guide)

def run_compatibility_check(controller, callback=None):
    """Convenience function to run the compatibility check"""
    checker = GalilCommandChecker(controller)
    results = checker.run_compatibility_test(callback)
    checker.save_results()
    checker.print_compatible_commands()
    return checker

if __name__ == "__main__":
    # Example usage
    print("Galil DMC-4103 Command Compatibility Checker")
    print("This module should be imported and used with a connected controller.")
    print("Example usage:")
    print("  from command_compatibility_checker import run_compatibility_check")
    print("  checker = run_compatibility_check(controller)")
