# Galil Setup Tool - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage Guide](#usage-guide)
5. [Network Configuration](#network-configuration)
6. [Motor Setup & Control](#motor-setup--control)
7. [Brushless Motor Configuration](#brushless-motor-configuration)
8. [Diagnostics & Monitoring](#diagnostics--monitoring)
9. [File Structure](#file-structure)
10. [Troubleshooting](#troubleshooting)
11. [Changelog](#changelog)
12. [Technical Details](#technical-details)

---

## Overview

The Galil Setup Tool is a comprehensive GUI application for configuring, testing, and controlling Galil DMC-4143 motion controllers. This tool provides an intuitive interface for network configuration, motor setup, motion control, diagnostics, and real-time monitoring.

### Key Capabilities
- **Network Configuration**: Set IP, subnet mask, gateway, and hostname
- **Motor Control**: Smooth jogging, absolute/relative positioning, speed control
- **PID Tuning**: Real-time servo loop tuning with live feedback
- **Diagnostics**: Comprehensive motor testing and position accuracy verification
- **Real-time Monitoring**: Live encoder position display for all axes
- **Brushless Motor Setup**: Complete brushless motor configuration process
- **Auto-Connection**: Automatic controller detection and connection
- **Configuration Management**: Save/load settings with external config file support

---

## Features

### Core Functionality
- **Network Configuration**: Set IP, subnet mask, gateway, and hostname
- **Motor Control**: Smooth jogging, absolute/relative positioning, speed control
- **PID Tuning**: Real-time servo loop tuning with live feedback
- **Diagnostics**: Comprehensive motor testing and position accuracy verification
- **Real-time Monitoring**: Live encoder position display for all axes with automatic updates
- **Configuration Management**: Save/load settings with external config file support
- **Auto-Servo Management**: Continuous servo status monitoring and automatic recovery

### Advanced Features
- **Auto-Connection**: Automatic controller detection and connection
- **Motor Detection**: Intelligent detection of connected motors with movement testing
- **Position Accuracy**: High-precision positioning with automatic corrections (0-3 counts error)
- **Multi-Axis Support**: Full support for 4-axis controllers (A, B, C, D)
- **Error Handling**: Robust error detection and recovery with thread-safe operations
- **Logging**: Comprehensive status logging with clipboard export
- **Servo Maintenance**: Automatic servo status monitoring and re-enablement
- **Movement Monitoring**: Real-time motion tracking and completion verification
- **GDK Integration**: Direct launch of Galil Development Kit
- **Diagnostic Reports**: Save, load, and compare diagnostic results

---

## Installation

### System Requirements
- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.7 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Network**: Ethernet connection for controller communication

### Dependencies
```
tkinter (included with Python)
gclib (Galil Communications Library)
```

### Option 1: Python Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/rmcdowell-acertaralabs/galil-setup-tool.git
   cd galil-setup-tool
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

### Option 2: Executable Installation

1. **Download the latest release** from the [Releases](https://github.com/rmcdowell-acertaralabs/galil-setup-tool/releases) page
2. **Extract the ZIP file** to your desired location
3. **Run `Galil_Setup_Tool.exe`**

---

## Usage Guide

### 1. Network Configuration Tab

#### Setting Controller IP Address
1. Enter the desired IP address (e.g., `10.1.0.21`)
2. Click **"Configure Network"**
3. Wait for configuration to complete
4. Verify with **"Test Network Connection"**

#### Network Settings
- **IP Address**: Controller's network address
- **Subnet Mask**: Network subnet (typically `255.255.255.0`)
- **Gateway**: Network gateway address
- **Hostname**: Controller hostname (optional)

#### GDK Launch Feature
- **Location**: Network Configuration tab
- **Button**: "🚀 Launch GDK" (green button with rocket emoji)
- **Functionality**: 
  - Automatically detects GDK installation
  - Launches GDK with controller IP for automatic connection
  - Checks for running instances and asks user preference

### 2. Controller Testing Tab

#### Connection
- **Auto-Connection**: Automatically connects on startup
- **Manual Connection**: Enter IP address and click "Connect"
- **Status**: Shows connection status and controller serial number

#### Motor Control
- **Jogging**: Use arrow buttons for manual movement
- **Speed Control**: Adjust jog speed in real-time
- **Position Control**: Enter target position and click "Move"

#### PID Tuning
1. **Select Axis**: Choose axis to tune (A, B, C, D)
2. **Set Parameters**: Adjust KP, KI, KD values
3. **Apply Tuning**: Click "Apply Tuning"
4. **Test**: Use jog controls to test response

#### Diagnostics
1. **Run Diagnostics**: Click "Run Automatic Diagnostics"
2. **Monitor Progress**: Watch real-time test results
3. **Review Results**: Check position accuracy and motor performance

### 3. Motor Setup Tab

#### Real-time Encoder Position Display
- **Location**: Top of Motor Setup page
- **Features**: 
  - Real-time position display for all axes (A, B, C, D)
  - Manual update button
  - Auto-update toggle (every 500ms)
  - Clear visual indicators for connection status

#### PID Configuration (Collapsible)
- **Axis Selection**: Choose target axis
- **PID Parameters**: Set KP, KI, KD values
- **Tune Button**: Apply PID settings to selected axis

#### Motion Parameters (Collapsible)
- **Speed**: Set motor speed in counts/sec
- **Acceleration**: Set acceleration rate
- **Deceleration**: Set deceleration rate
- **Apply Button**: Apply motion parameters

#### Brushless Motor Configuration (Collapsible)
- **4-Step Process**: Complete brushless motor setup
- **Real-time Monitoring**: Position tracking during setup
- **Error Handling**: Graceful degradation for unsupported controllers

### 4. Settings Tab

#### Configuration Management
- **Save Settings**: Save current configuration to file
- **Load Settings**: Load configuration from file
- **Reset to Defaults**: Restore default settings

#### General Settings
- **IP Address**: Default controller IP
- **Jog Speed**: Default jog speed
- **Axis Presets**: Per-axis default settings

---

## Network Configuration

### DMC-4143 Specific Requirements

#### Important Notes
1. **Power Cycle Required**: After setting network parameters, you MUST power cycle the controller
2. **BN Command**: Uses `BN` command instead of `SAVE` to burn settings to non-volatile memory
3. **Command Format**: Prefers `IP=`, `SM=`, `GW=` format with equals sign
4. **Limited Read Commands**: `MG _IP` and other network read commands may not be supported

#### Working Commands for DMC-4143
```bash
# Set IP address
IP=192.168.1.100

# Set subnet mask  
SM=255.255.255.0

# Set gateway
GW=192.168.1.1

# Save settings to non-volatile memory
BN
```

#### Non-Working Commands for DMC-4143
```bash
# These commands return "question mark" (not supported)
SAVE
MG _IP
MG _GW
MG _MAC
MG _HN
MG _DHCP
```

### Enhanced Features

#### Proper Galil DMC-4143 Network Commands
- **IP Address**: `IP{address}`, `IP {address}`, `IP={address}`
- **Subnet Mask**: `SM{mask}`, `SM {mask}`, `SM={mask}`
- **Gateway**: `GW{gateway}`, `GW {gateway}`, `GW={gateway}`
- **Hostname**: `HN{hostname}`, `HN {hostname}`, `HN={hostname}`
- **Save Settings**: `BN` (burns settings to non-volatile memory)

#### Network Settings Persistence
All network settings are saved to the controller's non-volatile memory using the `BN` command, ensuring they persist after power cycles.

#### Comprehensive Network Status Reporting
The system can read and display:
- Current IP address
- Subnet mask
- Gateway address
- MAC address
- Hostname
- DHCP status

### Usage Instructions

#### Setting IP Address (Simple)
1. Connect to the controller
2. Click "SET IP (SIMPLE)"
3. Enter the new IP address
4. The system will validate, set, and save the IP

#### Setting Advanced Network Configuration
1. Connect to the controller
2. Click "SET IP (ADVANCED)"
3. Enter IP address, subnet mask, and gateway
4. The system will apply all settings and save them

#### Reading Controller Network Settings
1. Connect to the controller
2. Click "READ CONTROLLER NETWORK"
3. View current network configuration
4. Compare with local configuration

#### Resetting to DHCP
1. Connect to the controller
2. Click "RESET CONTROLLER TO DHCP"
3. Confirm the action
4. The controller will be configured to use DHCP

---

## Motor Setup & Control

### Real-time Encoder Position Display

#### Display Components
- **4 Axis Labels**: Axis A, Axis B, Axis C, Axis D
- **Position Values**: Large, bold numbers showing current encoder counts
- **Visual Style**: White background with black text, sunken relief
- **Width**: Fixed width (12 characters) for consistent layout

#### Control Buttons
- **🔄 Update Positions**: Manual refresh button
- **Auto-update checkbox**: Toggle automatic updates every 500ms

#### Real-time Updates
- **Automatic Updates**: Every 500ms when enabled
- **Default State**: Enabled by default
- **User Control**: Can be toggled on/off with checkbox
- **Manual Updates**: Immediate refresh of all axis positions

#### Status Indicators
- **Normal Operation**: Black text showing actual encoder counts
- **Error States**: Red text showing "No Connection" or "Error"
- **Visual Feedback**: Clear indication of connection status

### Compact Layout Design

#### Two-Column Layout
- **Left Column**: Configuration sections with scrolling
- **Right Column**: Status log (always visible)
- **Better Space Utilization**: More room for both configuration and logging

#### Collapsible Sections
- **PID Configuration**: Expandable/collapsible with click
- **Motion Parameters**: Expandable/collapsible with click
- **Brushless Motor Configuration**: Expandable/collapsible with click
- **Visual Indicators**: ▼ for expanded, ▶ for collapsed

#### Scrollable Interface
- **Canvas-based scrolling**: Smooth scrolling experience
- **Dynamic content**: Adapts to content size
- **Performance optimized**: Efficient rendering

### Motor Control Features

#### Jogging Operations
- **Positive/Negative Jogging**: Use arrow buttons for manual movement
- **Adjustable Speeds**: Real-time speed control
- **Emergency Stop**: Immediate stop functionality

#### Position Control
- **Absolute Positioning**: Move to specific encoder position
- **Relative Positioning**: Move by specified distance
- **Speed Control**: Adjustable movement speed
- **Acceleration Control**: Configurable acceleration rates

#### PID Tuning
- **Real-time Tuning**: Live feedback during tuning
- **Parameter Adjustment**: KP, KI, KD value setting
- **Axis-specific**: Individual tuning for each axis
- **Verification**: Test tuning with movement commands

---

## Brushless Motor Configuration

### Overview
Comprehensive brushless motor configuration functionality that guides users through the complete process of setting up brushless motors for sinusoidal commutation on Galil controllers.

### Complete Setup Process

#### Step 1: Define Motor Direction
- **Purpose**: Establish the positive direction of encoder counts
- **Process**: 
  - Set encoder polarity (Normal/Reversed)
  - Enable servo for manual movement
  - Monitor encoder counts during manual movement
  - Verify direction is correct
- **Duration**: 10 seconds monitoring period
- **Safety**: Motor disabled after test completion

#### Step 2: Estimate Brushless Modulo & Correct Hall Sensors
- **Purpose**: Calculate the brushless modulo (BM) and correct hall sensor wiring
- **Process**:
  - Orient motor to find magnetic cycle
  - Measure hall sensor signals
  - Calculate brushless modulo
  - Correct any hall sensor wiring issues
- **Duration**: Maximum 30 seconds
- **Output**: Estimated BM value

#### Step 3: Latch Indexes (Optional)
- **Purpose**: Improve BM accuracy using encoder index signals
- **Process**:
  - Move motor through two index pulses
  - Calculate precise index distance
  - Determine pole pairs
  - Calculate improved BM
- **Duration**: Maximum 10 seconds
- **Requirements**: Encoder must have index signal

#### Step 4: Save Configuration
- **Purpose**: Save all settings to controller memory
- **Process**:
  - Save brushless modulo (BM)
  - Enable brushless mode
  - Save to non-volatile memory
  - Verify configuration

### Technical Implementation

#### UI Components
- **Instructions Panel**: Safety and setup requirements
- **Step 1 Controls**: Motor direction definition with polarity selection
- **Step 2 Controls**: Brushless modulo estimation
- **Step 3 Controls**: Index latching with skip option
- **Step 4 Controls**: Configuration saving

#### Core Methods
- **define_motor_direction()**: Monitor manual movement for direction
- **estimate_brushless_modulo()**: Calculate BM from motor movement
- **latch_indexes()**: Improve BM accuracy with index signals
- **save_brushless_settings()**: Save configuration to controller

### Error Handling Strategy

#### Command-Level Error Handling
```python
try:
    self.controller.send_command(f"SH{axis}")
    self.motor_status_text.insert(tk.END, f"✓ Servo enabled for axis {axis}\n")
except Exception as servo_error:
    self.motor_status_text.insert(tk.END, f"⚠ Warning: Could not enable servo: {servo_error}\n")
    self.motor_status_text.insert(tk.END, "Continuing with simulation mode...\n")
```

#### Process Continuation
- **Success Path**: Commands work → Real brushless configuration
- **Failure Path**: Commands fail → Simulation mode with educational output
- **Mixed Path**: Some commands work, others fail → Hybrid operation

#### User Communication
- **✓ Success**: Commands executed successfully
- **⚠ Warning**: Commands failed but process continues
- **ERROR**: Critical failure with explanation

### Safety Features

#### Automatic Servo Management
- **Enable**: Servo enabled only during active tests
- **Disable**: Servo automatically disabled after each test
- **Safety**: MO jumper ensures motor ends in disabled state

#### Error Handling
- **Connection Check**: Verifies controller connection before each step
- **Exception Handling**: Graceful error handling with user feedback
- **Timeout Protection**: Tests have maximum duration limits

#### User Feedback
- **Real-time Status**: Live updates during test execution
- **Progress Indicators**: Clear step-by-step progress
- **Error Messages**: Detailed error information and suggestions

### Technical Parameters

#### Brushless Modulo (BM)
- **Definition**: Encoder counts per magnetic cycle
- **Calculation**: Based on hall sensor measurements
- **Improvement**: Enhanced by index latching if available
- **Storage**: Saved to controller memory

#### Encoder Polarity
- **Normal**: Standard encoder count direction
- **Reversed**: Inverted encoder count direction
- **Setting**: EP command (EP=0 for Normal, EP=1 for Reversed)

#### Brushless Mode
- **Enable**: BL=1 command
- **Purpose**: Activates sinusoidal commutation
- **Requirement**: Valid BM value must be set

---

## Diagnostics & Monitoring

### Enhanced Diagnostic Features

#### Comprehensive Performance Analysis
- **Performance Ratings**: EXCELLENT, GOOD, ACCEPTABLE, NEEDS ATTENTION
- **Axis-by-Axis Summary**: Shows PID settings, position accuracy, and performance metrics
- **System Assessment**: Overall system health evaluation with error/warning counts
- **Actionable Recommendations**: Specific suggestions for improvement

#### Diagnostic Report Management
- **Save Reports**: Export diagnostic results to JSON files with metadata
- **Load Reports**: Import and display previously saved diagnostic reports
- **Report Metadata**: Includes version info, timestamps, and generation details

#### Data Export Capabilities
- **CSV Export**: Export diagnostic data for external analysis
- **Structured Data**: Includes axis, speed, position errors, PID settings, and timestamps
- **Analysis Ready**: Formatted for statistical analysis and trend tracking

#### Report Comparison Tool
- **Multi-Report Analysis**: Compare performance across multiple diagnostic sessions
- **Trend Analysis**: Identify improving, declining, or stable performance patterns
- **Performance Tracking**: Track system health over time with scoring metrics
- **Best/Worst Identification**: Highlight best and worst performing sessions

### Automatic Diagnostics

#### Motor Detection
- **Intelligent Detection**: Identifies connected motors on each axis
- **Movement Testing**: Tests motor responsiveness with small movements
- **Connection Verification**: Confirms motor and encoder connections

#### Position Accuracy Testing
- **Test Positions**: 0, 250000, 500000, 250000, 0 counts
- **Speed Testing**: Tests at multiple speeds (50,000 and 100,000 counts/sec)
- **Motion Completion**: Verifies motion completes successfully
- **Position Corrections**: Automatic correction of positioning errors

#### Performance Metrics
- **Position Accuracy**: Reports final position error in encoder counts
- **Motion Time**: Measures time to complete each move
- **Motor Status**: Confirms motor responsiveness and tuning
- **Error Detection**: Identifies mechanical constraints or servo issues

### Real-time Monitoring

#### Encoder Position Display
- **4-Axis Display**: Shows position for all axes simultaneously
- **Live Updates**: Real-time position updates every 500ms
- **Connection Status**: Visual indicators for each axis
- **Position Accuracy**: Displays current position with target comparison

#### Status Logging
- **Comprehensive Logs**: All operations and test results
- **Timestamped Entries**: Chronological operation history
- **Error Reporting**: Detailed error messages and diagnostics
- **Clipboard Export**: Copy logs to clipboard for analysis

### Performance Rating System
- **EXCELLENT**: Max error ≤ 5 counts
- **GOOD**: Max error ≤ 20 counts  
- **ACCEPTABLE**: Max error ≤ 100 counts
- **NEEDS ATTENTION**: Max error > 100 counts

### System Health Scoring
- **Errors**: 10 points each
- **Warnings**: 2 points each
- **Lower score**: Better system health

---

## File Structure

### Current Structure
```
galil-setup-tool/
├── main.py                 # Main GUI application
├── galil_combined.py       # Combined Galil controller interface and functions
├── network_combined.py     # Combined network configuration and utilities
├── config.json            # Default configuration
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── CHANGELOG.md           # Version history
├── LICENSE                # Project license
└── assets/                # Static assets
    └── config.json        # Asset configuration
```

### File Consolidation Benefits
- **Reduced File Count**: 50% fewer files to manage
- **Improved Organization**: Related functionality grouped together
- **Simplified Imports**: Fewer import statements needed
- **Better Maintainability**: Related code co-located

### Configuration Files

#### config.json
```json
{
    "ip_address": "10.1.0.21",
    "jog_speed": 5000,
    "axis_presets": {
        "A": {
            "jog_speed": 128000,
            "kp": 10.0,
            "ki": 0.1,
            "kd": 50.0,
            "sp": 1024000,
            "ac": 2560000,
            "dc": 2560000,
            "tl": 8.2,
            "clicks_per_turn": 64000,
            "turns_per_mm": 0.2
        }
    }
}
```

#### External Config File
The tool can read motor settings from `C:\AMS\config.txt`:
```
motor_speed = [1024000, 1024000, 1024000, 1024000]
motor_accel = [2560000, 2560000, 2560000, 2560000]
motor_decel = [2560000, 2560000, 2560000, 2560000]
jog_speed = [128000, 128000, 128000, 128000]
motor_clicksPerTurn = [64000, 64000, 64000, 64000]
motor_turnsPerMM = [0.2, 0.2, 0.2, 0.2]
```

---

## Troubleshooting

### Common Issues

#### Connection Problems
- **Check Network**: Verify controller is on same network
- **Ping Test**: Use "Test Network Connection" to verify reachability
- **IP Address**: Confirm correct IP address in settings
- **Firewall**: Ensure firewall allows communication on controller port

#### Motor Not Responding
- **Servo Status**: Check if servo is enabled (SH command) - use "Enable All Servos" button
- **Motor Detection**: Run diagnostics to verify motor presence
- **PID Tuning**: Adjust PID parameters for better response
- **Following Error**: Check following error limits
- **Auto-Recovery**: Application automatically monitors and re-enables servos

#### Position Accuracy Issues
- **Position Reference**: Ensure axis is properly homed (DP command)
- **PID Tuning**: Fine-tune PID parameters for better accuracy
- **Speed Settings**: Reduce speed for more precise positioning
- **Mechanical Issues**: Check for mechanical constraints or backlash
- **Auto-Correction**: Application automatically corrects positioning errors
- **High Accuracy**: Typical position errors are 0-3 encoder counts

### Error Messages

#### "Controller not connected"
- Verify network connection
- Check IP address settings
- Ensure controller is powered on

#### "Motion timeout"
- Check for mechanical obstructions
- Verify motor is properly connected
- Adjust PID parameters

#### "Position error: X counts"
- Normal for high-speed moves
- Consider reducing speed for precision
- Check mechanical backlash

### IP Settings Save Troubleshooting

#### DMC-4143 Specific Requirements
- **Use BN command**: Instead of SAVE command
- **Power cycle required**: After network changes
- **Command format**: Use `IP=`, `SM=`, `GW=` format
- **Empty responses**: Usually indicate success

#### Diagnostic Steps
1. **Test Save Commands**: Use "TEST SAVE COMMANDS" button
2. **Test IP Setting**: Use "SET IP (SIMPLE)" or "SET IP (ADVANCED)"
3. **Manual Verification**: Try reading IP back with `IP` command
4. **Power Cycle**: Always power cycle after network changes

#### Working Command Sequence
```
IP=192.168.1.100
SM=255.255.255.0
GW=192.168.1.1
BN
```
Then power cycle the controller.

### Brushless Motor Configuration Issues

#### Motor Not Moving During Direction Test
- **Check**: Servo enable status
- **Solution**: Verify motor connections and power
- **Alternative**: Use encoder polarity setting

#### Hall Sensor Detection Fails
- **Check**: Hall sensor wiring and connections
- **Solution**: Verify hall sensor power and signal connections
- **Alternative**: Manual BM calculation

#### Index Latching Fails
- **Check**: Encoder index signal
- **Solution**: Verify index signal wiring
- **Alternative**: Skip index latching step

#### Settings Save Fails
- **Check**: Controller memory and permissions
- **Solution**: Verify controller status and try again
- **Alternative**: Manual command entry

---

## Changelog

### [1.1.0] - Latest Version

#### Added
- **Enhanced Diagnostic Reporting**: Comprehensive performance analysis and recommendations
- **Report Management**: Save, load, and compare diagnostic reports
- **Data Export**: CSV export for external analysis
- **GDK Integration**: Direct launch of Galil Development Kit
- **Real-time Encoder Display**: Live position updates for all axes
- **Brushless Motor Configuration**: Complete 4-step setup process
- **Compact Layout**: Scrollable interface with collapsible sections
- **Auto-Servo Management**: Continuous servo status monitoring

#### Fixed
- **Jerky Motor Movement**: Enhanced servo enablement and continuous monitoring
- **Encoder Updates**: Real-time position updates with automatic start
- **Error Handling**: Robust widget destruction handling and thread management
- **Tkinter Crashes**: Proper widget existence checks and thread cleanup
- **Motion Status Parsing**: Fixed float parsing errors in motion monitoring
- **Position Reference**: Implemented proper axis homing for absolute positioning
- **Motor Detection**: Improved detection logic for motors with limited movement

#### Changed
- **Code Architecture**: Consolidated multiple modules into combined files
- **Motion Control**: Improved move_to_position and jog_distance functions
- **Diagnostics**: Enhanced automatic diagnostics with position accuracy testing
- **Configuration**: Updated default settings and external config file support
- **Documentation**: Comprehensive documentation with installation and usage guides

### [1.0.0] - Initial Release

#### Added
- **Comprehensive GUI Application**: Complete rewrite with modern Tkinter interface
- **Network Configuration**: Full IP, subnet mask, gateway, and hostname configuration
- **Motor Control**: Jogging, absolute/relative positioning, speed control
- **PID Tuning**: Real-time servo loop tuning with live feedback
- **Diagnostics System**: Comprehensive motor testing and position accuracy verification
- **Real-time Monitoring**: Live encoder position display for all 4 axes
- **Auto-Connection**: Automatic controller detection and connection
- **Motor Detection**: Intelligent detection of connected motors with movement testing
- **Position Accuracy**: High-precision positioning with automatic corrections
- **Configuration Management**: Save/load settings with external config file support

#### Technical Improvements
- **Motion Monitoring**: Real-time position tracking with progress reporting
- **Error Recovery**: Graceful handling of connection and motion errors
- **Performance**: Optimized motion completion detection and position corrections
- **Reliability**: Robust error handling and recovery mechanisms
- **User Experience**: Intuitive GUI with clear status indicators and logging

---

## Technical Details

### Galil Commands Used
The tool uses standard Galil commands:
- `IP`, `SM`, `GW`: Network configuration
- `SH`, `MO`: Servo enable/disable
- `KP`, `KI`, `KD`: PID parameters
- `SP`, `AC`, `DC`: Speed, acceleration, deceleration
- `PA`, `PR`: Absolute/relative positioning
- `TP`: Tell position
- `MG _BG`: Motion status
- `BM`, `BL`: Brushless motor configuration
- `BN`: Save to non-volatile memory

### Thread Safety
- **Background Operations**: All long-running operations use threads
- **UI Updates**: Thread-safe UI updates using `root.after()`
- **Error Handling**: Graceful handling of thread exceptions
- **Resource Cleanup**: Proper cleanup when switching pages

### Error Handling Strategy
- **Command-Level**: Individual try-catch blocks for each command
- **Process Continuation**: Graceful degradation when commands fail
- **User Communication**: Clear status messages with success/warning indicators
- **Recovery Mechanisms**: Automatic retry and fallback options

### Performance Optimizations
- **Real-time Updates**: 500ms update intervals for responsive display
- **Efficient Rendering**: Canvas-based scrolling and optimized UI updates
- **Memory Management**: Proper cleanup of resources and threads
- **Connection Pooling**: Efficient controller communication

### Security Considerations
- **Network Configuration**: Requires administrator privileges
- **DLL Installation**: Modifies system files (System32)
- **Controller Access**: Direct hardware control capabilities
- **Error Logging**: Comprehensive logging for troubleshooting

---

## Support

### Built-in Diagnostics
- Use the diagnostics panel for real-time system information
- Check log entries for detailed operation history
- Use test buttons to verify functionality

### Version Information
- **Version**: 1.1.0
- **Build Date**: August 2025
- **Python Version**: 3.8+
- **Compatibility**: Windows 10/11 (64-bit)

### Contact Information
For support and questions:
- Create an issue on GitHub
- Contact: [rmcdowell-acertaralabs](https://github.com/rmcdowell-acertaralabs)

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This tool is designed for use with Galil DMC-4143 motion controllers. Ensure proper safety measures when working with industrial motion control systems.
