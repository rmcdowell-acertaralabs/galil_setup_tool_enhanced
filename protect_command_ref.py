#!/usr/bin/env python3
"""
Command Reference Protection Script

This script protects lines 1-10715 of command_validator.py from modification.
These lines contain the DMC-4103 command reference and should not be changed.

Usage:
    python protect_command_ref.py check    # Check if protected lines were modified
    python protect_command_ref.py restore  # Restore protected lines from Git
"""

import sys
import subprocess
import os
from pathlib import Path

PROTECTED_FILE = "command_validator.py"
PROTECTED_LINES = (1, 10715)

def check_protected_lines():
    """Check if any changes were made to protected lines"""
    try:
        # Get the diff between working directory and HEAD
        result = subprocess.run(
            ["git", "diff", "HEAD", PROTECTED_FILE],
            capture_output=True,
            text=True,
            check=True
        )
        
        if not result.stdout:
            print("✅ No changes detected in command_validator.py")
            return True
            
        # Parse the diff to check line numbers
        lines = result.stdout.split('\n')
        modified_lines = []
        
        for line in lines:
            if line.startswith('@@'):
                # Parse line numbers from diff header
                # Format: @@ -old_start,old_count +new_start,new_count @@
                parts = line.split()
                if len(parts) >= 3:
                    old_info = parts[1]  # -old_start,old_count
                    new_info = parts[2]  # +new_start,new_count
                    
                    # Parse old line range
                    if old_info.startswith('-') and ',' in old_info:
                        old_start = int(old_info[1:].split(',')[0])
                        old_count = int(old_info[1:].split(',')[1]) if ',' in old_info[1:] else 1
                        old_end = old_start + old_count - 1
                        
                        # Check if any part of the change overlaps with protected lines
                        if old_start <= PROTECTED_LINES[1] and old_end >= PROTECTED_LINES[0]:
                            modified_lines.append(f"{old_start}-{old_end}")
                    
                    # Parse new line range
                    if new_info.startswith('+') and ',' in new_info:
                        new_start = int(new_info[1:].split(',')[0])
                        new_count = int(new_info[1:].split(',')[1]) if ',' in new_info[1:] else 1
                        new_end = new_start + new_count - 1
                        
                        # Check if any part of the change overlaps with protected lines
                        if new_start <= PROTECTED_LINES[1] and new_end >= PROTECTED_LINES[0]:
                            modified_lines.append(f"{new_start}-{new_end}")
        
        if modified_lines:
            print("❌ ERROR: Protected lines in command_validator.py have been modified!")
            print(f"   Protected lines: {PROTECTED_LINES[0]}-{PROTECTED_LINES[1]}")
            print(f"   Modified lines detected: {modified_lines}")
            print("   These lines contain the DMC-4103 command reference and should not be changed.")
            print("   You can only modify lines after 10715.")
            return False
        else:
            print("✅ No protected lines were modified")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"Error checking Git diff: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def restore_protected_lines():
    """Restore protected lines from Git HEAD"""
    try:
        print("Restoring protected lines from Git HEAD...")
        subprocess.run(
            ["git", "checkout", "HEAD", "--", PROTECTED_FILE],
            check=True
        )
        print("✅ Protected lines restored successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restoring from Git: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python protect_command_ref.py [check|restore]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "check":
        if check_protected_lines():
            sys.exit(0)
        else:
            sys.exit(1)
    elif command == "restore":
        if restore_protected_lines():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("Invalid command. Use 'check' or 'restore'")
        sys.exit(1)

if __name__ == "__main__":
    main()
