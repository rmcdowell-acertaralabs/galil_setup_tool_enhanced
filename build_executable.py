#!/usr/bin/env python3
"""
Build script for Galil Setup Tool executable
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_previous_builds():
    """Clean previous build artifacts."""
    print("Cleaning previous builds...")
    
    dirs_to_clean = ['build', 'dist']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    for pattern in files_to_clean:
        for file_path in Path('.').glob(pattern):
            print(f"  Removing {file_path}")
            file_path.unlink()

def check_required_files():
    """Check if all required files are present."""
    print("Checking required files...")
    
    required_files = [
        'main.py',
        'gclib.dll',
        'gclibo.dll',
        'config.json',
        'utils.py',
        'constants.py',
        'network_config.py',
        'network_utils.py',
        'galil_interface.py',
        'diagnostics.py',
        'motor_setup.py',
        'motion_controls.py',
        'encoder_overlay.py',
        'config_manager.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (MISSING)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\nERROR: Missing required files: {missing_files}")
        return False
    
    print("  All required files found!")
    return True

def build_executable():
    """Build the executable using PyInstaller."""
    print("\nBuilding executable with PyInstaller...")
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', 'Galil_Setup_Tool',
        '--add-data', 'gclib.dll;.',
        '--add-data', 'gclibo.dll;.',
        '--add-data', 'config.json;.',
        '--add-data', 'assets;assets',
        '--hidden-import', 'tkinter',
        '--hidden-import', 'tkinter.ttk',
        '--hidden-import', 'tkinter.messagebox',
        '--hidden-import', 'tkinter.simpledialog',
        '--hidden-import', 'serial',
        '--hidden-import', 'serial.tools.list_ports',
        '--hidden-import', 'ctypes',
        '--hidden-import', 'platform',
        '--hidden-import', 'subprocess',
        '--hidden-import', 're',
        '--hidden-import', 'os',
        '--hidden-import', 'time',
        '--hidden-import', 'datetime',
        '--hidden-import', 'json',
        '--hidden-import', 'math',
        '--hidden-import', 'threading',
        '--hidden-import', 'typing',
        'main.py'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✓ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed with error code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return False

def verify_executable():
    """Verify the executable was created successfully."""
    print("\nVerifying executable...")
    
    exe_path = os.path.join('dist', 'Galil_Setup_Tool.exe')
    
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path)
        print(f"✓ Executable created: {exe_path}")
        print(f"  Size: {file_size / (1024*1024):.1f} MB")
        return True
    else:
        print(f"✗ Executable not found: {exe_path}")
        return False

def main():
    """Main build process."""
    print("=" * 50)
    print("Galil Setup Tool - Executable Builder")
    print("=" * 50)
    print()
    
    # Step 1: Clean previous builds
    clean_previous_builds()
    
    # Step 2: Check required files
    if not check_required_files():
        print("\nBuild aborted due to missing files.")
        return False
    
    # Step 3: Build executable
    if not build_executable():
        print("\nBuild failed.")
        return False
    
    # Step 4: Verify executable
    if not verify_executable():
        print("\nExecutable verification failed.")
        return False
    
    print("\n" + "=" * 50)
    print("BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print()
    print("Executable location: dist\\Galil_Setup_Tool.exe")
    print()
    print("Files included in executable:")
    print("- All Python modules")
    print("- gclib.dll and gclibo.dll")
    print("- config.json")
    print("- assets folder")
    print()
    print("The executable is self-contained and can be run on any Windows machine.")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
