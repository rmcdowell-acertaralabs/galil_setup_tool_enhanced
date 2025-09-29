# Galil Setup Tool

A comprehensive GUI application for configuring, testing, and controlling Galil DMC-4143 motion controllers. This tool provides an intuitive interface for network configuration, motor setup, motion control, diagnostics, and real-time monitoring.

## 🚀 Quick Start

### Installation

#### Option 1: Python Installation

```bash
git clone https://github.com/rmcdowell-acertaralabs/galil-setup-tool.git
cd galil-setup-tool
pip install -r requirements.txt
python main.py
```

#### Option 2: Executable Installation

1. Download the latest release from [Releases](https://github.com/rmcdowell-acertaralabs/galil-setup-tool/releases)
2. Extract and run `Galil_Setup_Tool.exe`

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.7 or higher (for Python installation)
- **Network**: Ethernet connection for controller communication

## ✨ Key Features

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

## 📖 Usage Guide

### 1. Network Configuration

- Set controller IP address, subnet mask, gateway, and hostname
- Test network connectivity
- Launch GDK with automatic controller connection
- Save network settings to controller memory

### 2. Controller Testing

- Auto-connect to controller
- Manual motor control with jogging and positioning
- Real-time PID tuning with live feedback
- Comprehensive diagnostics and performance analysis

### 3. Motor Setup

- Real-time encoder position display for all axes
- Collapsible configuration sections (PID, Motion Parameters, Brushless)
- Complete brushless motor configuration process
- Two-column layout with status logging

### 4. Visual Testing Interface

- **Real-time Progress Tracking**: Visual progress bars with step-by-step monitoring
- **Interactive Controls**: Start, stop, and reset test functionality
- **Comprehensive Testing**: 5-phase testing process (Setup, Discovery, Motion, Status, Teardown)
- **Visual Status Icons**: ⏳ Pending, 🔄 Running, ✅ Passed, ❌ Failed, ⏭️ Skipped
- **Real-time Details**: Live log of test operations and results
- **ETA Calculation**: Estimated time remaining for test completion
- **Professional Interface**: Engaging, modern testing experience

## 🔧 Network Configuration

### DMC-4143 Specific Requirements

1. **Power Cycle Required**: After setting network parameters, you MUST power cycle the controller
2. **BN Command**: Uses `BN` command instead of `SAVE` to burn settings to non-volatile memory
3. **Command Format**: Prefers `IP=`, `SM=`, `GW=` format with equals sign

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

## 🎯 Motor Setup & Control

### Real-time Encoder Position Display

- **Always-Visible Encoders**: Encoder displays now always visible with no toggle required
- **Auto-Start Updates**: Encoder polling automatically starts when entering controller testing or motor setup views
- **4 Axis Labels**: Axis A, B, C, D with real-time position updates every 500ms
- **Resilient Updates**: Encoder loops continue running even when controller is disconnected
- **Visual Indicators**: Clear connection status and error states
- **Compact Layout**: Two-column design with collapsible sections
- **Thread-Safe Operations**: Enhanced thread safety for concurrent encoder updates and motion commands

### Motor Control Features

- **Enhanced Move Button**: Resolved move button functionality issues with improved error handling
- **Jogging Operations**: Positive/negative movement with adjustable speeds
- **Position Control**: Absolute and relative positioning with speed control
- **PID Tuning**: Real-time parameter adjustment with live feedback
- **Emergency Stop**: Immediate stop functionality
- **Thread-Safe Motion**: Enhanced thread safety for motion commands and encoder updates

## 🔄 Brushless Motor Configuration

Complete 4-step brushless motor setup process:

1. **Define Motor Direction**: Establish positive direction of encoder counts
2. **Estimate Brushless Modulo**: Calculate BM and correct hall sensor wiring
3. **Latch Indexes**: Improve BM accuracy using encoder index signals (optional)
4. **Save Configuration**: Save all settings to controller memory

### Safety Features

- Automatic servo management (enable only during tests)
- Comprehensive error handling with graceful degradation
- Real-time status updates and progress indicators
- Automatic motor disable after test completion

## 📊 Diagnostics & Monitoring

### Enhanced Diagnostic Features

- **Performance Ratings**: EXCELLENT, GOOD, ACCEPTABLE, NEEDS ATTENTION
- **Axis-by-Axis Summary**: PID settings, position accuracy, and performance metrics
- **System Assessment**: Overall system health evaluation
- **Report Management**: Save, load, and compare diagnostic results
- **Data Export**: CSV export for external analysis

### Real-time Monitoring

- **Encoder Position Display**: Live updates for all axes
- **Status Logging**: Comprehensive operation history
- **Error Reporting**: Detailed diagnostics and suggestions
- **Performance Tracking**: System health scoring over time

## 🛠️ Troubleshooting

### Common Issues

#### Connection Problems

- Check network connectivity and IP address
- Use "Test Network Connection" to verify reachability
- Ensure firewall allows communication on controller port

#### Motor Not Responding

- Check servo status (use "Enable All Servos" button)
- Run diagnostics to verify motor presence
- Adjust PID parameters for better response
- Application automatically monitors and re-enables servos

#### Position Accuracy Issues

- Ensure axis is properly homed
- Fine-tune PID parameters
- Reduce speed for more precise positioning
- Check for mechanical constraints or backlash
- Typical position errors are 0-3 encoder counts

### DMC-4143 Specific Troubleshooting

- **Use BN command**: Instead of SAVE command for network settings
- **Power cycle required**: After network changes
- **Command format**: Use `IP=`, `SM=`, `GW=` format
- **Empty responses**: Usually indicate success

## 📋 Dependencies

```text
tkinter (included with Python)
gclib (Galil Communications Library)
```

## 🔒 Command Reference Protection

The `command_validator.py` file contains the complete DMC-4103 command reference and should be protected from accidental modification.

### Protection Methods

```bash
# Check if protected lines were modified
python protect_command_ref.py check

# Restore protected lines from Git if they were modified
python protect_command_ref.py restore
```

## 📝 Changelog

### [2.3] - Latest Improvements (December 2024)

- **Always-Visible Encoders**: Encoder displays now always visible with no toggle required across all interfaces
- **Auto-Start Encoder Updates**: Encoder polling automatically starts in both controller testing and motor setup views
- **Enhanced Move Button Functionality**: Resolved move button issues with improved error handling and thread safety
- **Resilient Update Loops**: Encoder loops continue running even when controller is disconnected
- **Improved Cleanup**: Proper cleanup stops both encoder loops and prevents memory leaks
- **Thread-Safe Operations**: Enhanced thread safety for encoder updates and motion commands
- **Enhanced Command Validation**: Improved command validator with comprehensive DMC-4103 command support
- **Motor Setup Optimization**: Streamlined motor setup process with better error handling

### [2.2] - Enhanced DMC-4103 Support

- **Manual Command Interface**: Added direct command input box for sending DMC-4103 commands
- **Enhanced Motor Detection**: Improved motor detection algorithm with better error handling
- **Command Reference**: Added comprehensive DMC-4103 command documentation
- **Network Configuration**: Simplified to focus on IP address setting and burning

### [2.1] - Encoder & Visual Testing Enhancements

- **Always-Visible Encoders**: Encoder displays now always visible with no toggle required
- **Auto-Start Encoder Updates**: Encoder polling automatically starts in both controller testing and overlay views
- **Move Button Fixes**: Resolved move button functionality issues with improved error handling
- **Enhanced Visual Testing**: Comprehensive motor testing with real-time progress bars and status monitoring

### [2.0] - Enhanced DMC-4103 Support

- **Manual Command Interface**: Added direct command input box for sending DMC-4103 commands
- **Enhanced Motor Detection**: Improved motor detection algorithm with better error handling
- **Command Reference**: Added comprehensive DMC-4103 command documentation
- **Network Configuration**: Simplified to focus on IP address setting and burning
- **Mouse Wheel Support**: Added scroll wheel navigation for all pages
- **Improved Diagnostics**: Enhanced motor detection with proper timing and verification
- **Quick Command Buttons**: Pre-configured buttons for common DMC-4103 commands

## 🛡️ Safety Considerations

- **Network Configuration**: Requires administrator privileges
- **DLL Installation**: Modifies system files (System32)
- **Controller Access**: Direct hardware control capabilities
- **Error Logging**: Comprehensive logging for troubleshooting

## 📞 Support

### Built-in Diagnostics

- Use the diagnostics panel for real-time system information
- Check log entries for detailed operation history
- Use test buttons to verify functionality

### Version Information

- **Version**: 2.3
- **Build Date**: December 2024
- **Python Version**: 3.8+
- **Compatibility**: Windows 10/11 (64-bit)

### Contact Information

For support and questions:

- Create an issue on GitHub
- Contact: [rmcdowell-acertaralabs](https://github.com/rmcdowell-acertaralabs)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This tool is designed for use with Galil DMC-4143 motion controllers. Ensure proper safety measures when working with industrial motion control systems.
