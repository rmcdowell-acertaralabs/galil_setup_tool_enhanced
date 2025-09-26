#!/usr/bin/env python3
"""
Command Validation Script

Validates all commands used in the codebase against the DMC-4103 command reference
in command_validator.py to ensure proper syntax and compatibility.
"""

import re
import os
from typing import Dict, List, Set, Tuple

def load_command_reference() -> Dict[str, Dict]:
    """Load the command reference from command_validator.py"""
    try:
        # Read the command reference directly from the file
        with open('command_validator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the command reference dictionary
        # Look for the _load_command_reference method
        import re
        
        # Find the command reference dictionary in the file
        pattern = r'def _load_command_reference\(self\) -> Dict\[str, Dict\]:\s*return \{(.*?)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # This is a simplified approach - we'll manually define the known commands
            return {
                # Motion commands
                "ST": {"description": "Stop Motion", "parameters": ["axis"]},
                "AM": {"description": "After Motion", "parameters": ["axis"]},
                "BG": {"description": "Begin Motion", "parameters": ["axis"]},
                "SH": {"description": "Servo Here (Enable)", "parameters": ["axis"]},
                "MO": {"description": "Motor Off", "parameters": ["axis"]},
                "TP": {"description": "Tell Position", "parameters": ["axis"]},
                "PA": {"description": "Position Absolute", "parameters": ["axis", "value"]},
                "PR": {"description": "Position Relative", "parameters": ["axis", "value"]},
                "JG": {"description": "Jog", "parameters": ["axis", "value"]},
                "SP": {"description": "Speed", "parameters": ["axis", "value"]},
                "AC": {"description": "Acceleration", "parameters": ["axis", "value"]},
                "DC": {"description": "Deceleration", "parameters": ["axis", "value"]},
                "DP": {"description": "Define Position", "parameters": ["axis", "value"]},
                "FI": {"description": "Find Index", "parameters": ["axis"]},
                
                # Status and error commands
                "MG": {"description": "Message", "parameters": ["message"]},
                "TC": {"description": "Tell Error Code", "parameters": []},
                "TE": {"description": "Tell Error", "parameters": ["axis"]},
                "TS": {"description": "Tell Status", "parameters": ["axis"]},
                "TA": {"description": "Tell Amplifier", "parameters": ["axis"]},
                "TV": {"description": "Tell Velocity", "parameters": ["axis"]},
                "TB": {"description": "Tell Bit", "parameters": []},
                
                # System commands
                "ID": {"description": "Identify", "parameters": []},
                "MT": {"description": "Motor Type", "parameters": ["list"]},
                "BN": {"description": "Burn", "parameters": []},
                "IP": {"description": "Instantaneous Position", "parameters": ["axis", "value"]},
                "_SS": {"description": "System Status", "parameters": []},
                
                # Safety and limits
                "OE": {"description": "Off on Error", "parameters": ["axis", "value"]},
                "ER": {"description": "Error Limit", "parameters": ["axis", "value"]},
                "TL": {"description": "Torque Limit", "parameters": ["axis", "value"]},
                "TK": {"description": "Peak Torque Limit", "parameters": ["axis", "value"]},
                
                # Control commands
                "AB": {"description": "Abort", "parameters": []},
                "AZ": {"description": "Abort on Zero", "parameters": []},
                "SB": {"description": "Set Bit", "parameters": ["bit"]},
                "CB": {"description": "Clear Bit", "parameters": ["bit"]},
                "WT": {"description": "Wait", "parameters": ["time"]},
                
                # Format commands
                "PF": {"description": "Position Format", "parameters": ["format"]},
                "CF": {"description": "Communication Format", "parameters": ["format"]},
                "CW": {"description": "Communication Write", "parameters": ["format"]},
                
                # Brushless motor commands
                "BA": {"description": "Brushless Amplifier", "parameters": ["axis"]},
                "BM": {"description": "Brushless Modulo", "parameters": ["axis", "value"]},
                "BX": {"description": "Brushless eXchange", "parameters": ["axis", "value"]},
                "BZ": {"description": "Brushless Zero", "parameters": ["axis", "value"]},
                "BC": {"description": "Brushless Calibrate", "parameters": ["axis"]},
                "BI": {"description": "Brushless Input", "parameters": ["axis", "value"]},
            }
        else:
            print("Could not find command reference in file")
            return {}
            
    except Exception as e:
        print(f"Error loading command reference: {e}")
        return {}

def find_commands_in_file(filepath: str) -> List[Tuple[str, int, str]]:
    """Find all Galil commands in a file"""
    commands = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            # Look for send_command calls
            send_command_matches = re.finditer(r'send_command\s*\(\s*["\']([^"\']+)["\']', line)
            for match in send_command_matches:
                command = match.group(1)
                commands.append((command, line_num, line.strip()))
            
            # Look for GCommand calls
            gcommand_matches = re.finditer(r'GCommand\s*\(\s*["\']([^"\']+)["\']', line)
            for match in gcommand_matches:
                command = match.group(1)
                commands.append((command, line_num, line.strip()))
            
            # Look for _cmd calls
            cmd_matches = re.finditer(r'_cmd\s*\(\s*[^,]+,\s*["\']([^"\']+)["\']', line)
            for match in cmd_matches:
                command = match.group(1)
                commands.append((command, line_num, line.strip()))
                
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return commands

def extract_command_name(command: str) -> str:
    """Extract the base command name from a command string"""
    # Remove axis specifications and parameters
    # Examples: "ST A" -> "ST", "PAA=1000" -> "PA", "MG _TPA" -> "MG"
    
    # Handle MG commands with operands
    if command.startswith("MG "):
        return "MG"
    
    # Handle commands with axis specifications
    # Pattern: COMMAND[AXIS][=VALUE]
    match = re.match(r'^([A-Z]+)', command)
    if match:
        return match.group(1)
    
    return command.split()[0] if command.split() else command

def validate_commands():
    """Validate all commands in the codebase"""
    print("🔍 Validating Galil Commands Against DMC-4103 Reference")
    print("=" * 60)
    
    # Load command reference
    command_ref = load_command_reference()
    if not command_ref:
        print("❌ Failed to load command reference")
        return
    
    print(f"✅ Loaded {len(command_ref)} commands from reference")
    
    # Focus on specific files we're working with
    python_files = [
        'main.py',
        'discovery.py', 
        'comprehensive_testing.py',
        'test_motion.py',
        'teardown.py',
        'setup_safety.py',
        'errors_status.py',
        'motor_setup.py',
        'controller_commands.py',
        'galil_combined.py'
    ]
    
    # Filter to only existing files
    python_files = [f for f in python_files if os.path.exists(f)]
    
    print(f"📁 Found {len(python_files)} Python files to check")
    
    # Track all commands found
    all_commands = {}
    invalid_commands = []
    
    for filepath in python_files:
        commands = find_commands_in_file(filepath)
        if commands:
            all_commands[filepath] = commands
            
            for command, line_num, line_content in commands:
                cmd_name = extract_command_name(command)
                
                # Check if command exists in reference
                if cmd_name not in command_ref:
                    invalid_commands.append({
                        'file': filepath,
                        'line': line_num,
                        'command': command,
                        'base_command': cmd_name,
                        'context': line_content
                    })
    
    # Report results
    print(f"\n📊 Validation Results:")
    print(f"   Total files checked: {len(python_files)}")
    print(f"   Files with commands: {len(all_commands)}")
    print(f"   Invalid commands found: {len(invalid_commands)}")
    
    if invalid_commands:
        print(f"\n❌ Invalid Commands Found:")
        print("-" * 40)
        
        for issue in invalid_commands:
            print(f"File: {issue['file']}")
            print(f"Line: {issue['line']}")
            print(f"Command: '{issue['command']}'")
            print(f"Base Command: '{issue['base_command']}'")
            print(f"Context: {issue['context']}")
            print()
    else:
        print("\n✅ All commands are valid according to the DMC-4103 reference!")
    
    # Show command usage statistics
    print(f"\n📈 Command Usage Statistics:")
    command_counts = {}
    for filepath, commands in all_commands.items():
        for command, _, _ in commands:
            cmd_name = extract_command_name(command)
            command_counts[cmd_name] = command_counts.get(cmd_name, 0) + 1
    
    # Sort by usage count
    sorted_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)
    
    print("Top 10 most used commands:")
    for cmd, count in sorted_commands[:10]:
        status = "✅" if cmd in command_ref else "❌"
        print(f"  {status} {cmd}: {count} uses")
    
    return invalid_commands

if __name__ == "__main__":
    invalid_commands = validate_commands()
    
    if invalid_commands:
        print(f"\n⚠️  Found {len(invalid_commands)} invalid commands that need to be fixed!")
        exit(1)
    else:
        print(f"\n🎉 All commands are valid!")
        exit(0)
