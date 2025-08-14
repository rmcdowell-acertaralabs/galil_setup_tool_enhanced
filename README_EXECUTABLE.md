# Galil Setup Tool - Executable Version

## Overview

The Galil Setup Tool is a comprehensive Windows application for configuring and controlling Galil DMC-4143 motion controllers. This executable version packages everything needed to run the application on any Windows machine without requiring Python installation.

## Features

### 🎛️ **Motion Control**
- **Axis Control**: Full control over 4 axes (A, B, C, D)
- **Jog Operations**: Positive/negative jogging with adjustable speeds
- **Position Monitoring**: Real-time position display with gauge visualization
- **Stop Control**: Emergency stop functionality

### 🔧 **Configuration**
- **PID Tuning**: Load and apply PID values for motor tuning
- **Axis Configuration**: Apply preset configurations to individual axes
- **Network Settings**: Configure controller IP addresses and network settings

### 🌐 **Network Management**
- **Computer Network Configuration**: 
  - Read current network settings
  - Apply target network settings (10.1.0.20, etc.)
  - Reset to DHCP
  - Test network connectivity
- **Controller Network**: Discover and configure controller network settings

### 📊 **Diagnostics & Logging**
- **Real-time Logging**: Comprehensive logging system with timestamps
- **System Diagnostics**: Controller status and health monitoring
- **Scrollable History**: View past operations and events
- **Auto-scroll**: Toggle automatic scrolling of log entries

### 🔌 **DLL Management**
- **DLL Installation**: Install gclib.dll and gclibo.dll to System32
- **Status Checking**: Verify DLL installation status
- **Automatic Detection**: Check for required DLL files

## System Requirements

### Minimum Requirements
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4 GB
- **Storage**: 50 MB free space
- **Permissions**: Administrator privileges for network configuration and DLL installation

### Recommended Requirements
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 8 GB
- **Storage**: 100 MB free space
- **Network**: Ethernet connection for network operations

## Installation

### Option 1: Direct Execution
1. Download `Galil_Setup_Tool.exe`
2. Right-click and "Run as Administrator" (recommended)
3. The application will start immediately

### Option 2: Installation Directory
1. Create a folder (e.g., `C:\Galil_Setup_Tool\`)
2. Copy `Galil_Setup_Tool.exe` to the folder
3. Create a shortcut on desktop
4. Run as Administrator when needed

## Usage

### First Time Setup
1. **Run as Administrator**: Right-click executable → "Run as Administrator"
2. **DLL Installation**: Click "INSTALL DLL FILES" to install required DLLs
3. **Network Configuration**: Use "READ NETWORK SETTINGS" to check current configuration
4. **Connect to Controller**: Use USB or Network connection

### Basic Operations
1. **Connection**: Select USB or Network and click "CONNECT"
2. **Axis Selection**: Click on axis buttons (A, B, C, D) to select
3. **Motion Control**: Use JOG +/-, STOP buttons for movement
4. **Configuration**: Use "CONFIGURE AXIS" to apply preset settings
5. **Monitoring**: Watch the diagnostics panel for real-time information

### Advanced Features
- **PID Tuning**: Load PID values and use "TUNE AXIS"
- **Network Configuration**: Use computer network config buttons
- **Diagnostics**: Monitor system status in the diagnostics panel
- **Logging**: Use log controls to manage diagnostic information

## File Structure

The executable includes all necessary files:
```
Galil_Setup_Tool.exe
├── Python Runtime (embedded)
├── All Python Modules
├── gclib.dll
├── gclibo.dll
├── config.json
└── assets/ (if present)
```

## Troubleshooting

### Common Issues

#### "DLL Not Found" Error
- **Solution**: Run as Administrator and click "INSTALL DLL FILES"
- **Alternative**: Manually copy gclib.dll and gclibo.dll to System32

#### Network Configuration Fails
- **Solution**: Ensure running as Administrator
- **Check**: Use "READ NETWORK SETTINGS" to verify current configuration

#### Controller Connection Issues
- **USB**: Check USB cable and controller power
- **Network**: Verify IP address and network connectivity
- **Test**: Use "TEST CONNECTION" button

#### Application Won't Start
- **Check**: Windows Defender or antivirus blocking
- **Solution**: Add exception for the executable
- **Alternative**: Run from command prompt to see error messages

### Error Messages

#### "Permission Denied"
- **Cause**: Insufficient privileges
- **Solution**: Run as Administrator

#### "Controller Not Connected"
- **Cause**: No active connection
- **Solution**: Click "CONNECT" first

#### "Invalid Axis"
- **Cause**: Invalid axis selection
- **Solution**: Use A, B, C, or D only

## Network Configuration

### Target Settings
The application is configured for the following network settings:
- **IP Address**: 10.1.0.20
- **Subnet Mask**: 255.255.255.0
- **Gateway**: 10.1.0.1
- **Preferred DNS**: 10.1.0.10
- **Alternate DNS**: 10.1.0.11

### Configuration Process
1. Run as Administrator
2. Click "READ NETWORK SETTINGS"
3. Review current vs target settings
4. Click "APPLY TARGET SETTINGS"
5. Confirm the change
6. Test connectivity

## Logging System

### Log Levels
- **INFO**: General information
- **SUCCESS**: Successful operations
- **WARN**: Warning messages
- **ERROR**: Error messages
- **CMD**: Command executions
- **STATUS**: Status updates

### Log Controls
- **CLEAR LOG**: Clear all log entries
- **AUTO-SCROLL**: Toggle automatic scrolling
- **REFRESH DIAGNOSTICS**: Update controller diagnostics

## Security Notes

- **Administrator Rights**: Required for network configuration and DLL installation
- **Network Changes**: May temporarily disconnect from internet
- **DLL Installation**: Modifies system files (System32)
- **Antivirus**: May flag as suspicious due to DLL operations

## Support

### Built-in Diagnostics
- Use the diagnostics panel for real-time system information
- Check log entries for detailed operation history
- Use test buttons to verify functionality

### Version Information
- **Version**: 1.0
- **Build Date**: August 2025
- **Python Version**: 3.8 (embedded)
- **PyInstaller**: 6.15.0

## License

This software is provided as-is for use with Galil motion controllers. Ensure compliance with your organization's software policies.

---

**Note**: Always run as Administrator when performing network configuration or DLL installation operations.
