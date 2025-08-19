# Galil Setup Tool

A comprehensive GUI application for configuring, testing, and controlling Galil motion controllers. This tool provides an intuitive interface for network configuration, motor setup, motion control, diagnostics, and real-time monitoring of Galil DMC-4143 controllers.

## 🚀 Features

### Core Functionality
- **Network Configuration**: Set IP, subnet mask, gateway, and hostname
- **Motor Control**: Jogging, absolute/relative positioning, speed control
- **PID Tuning**: Real-time servo loop tuning with live feedback
- **Diagnostics**: Comprehensive motor testing and position accuracy verification
- **Real-time Monitoring**: Live encoder position display for all axes
- **Configuration Management**: Save/load settings with external config file support

### Advanced Features
- **Auto-Connection**: Automatic controller detection and connection
- **Motor Detection**: Intelligent detection of connected motors
- **Position Accuracy**: High-precision positioning with automatic corrections
- **Multi-Axis Support**: Full support for 4-axis controllers (A, B, C, D)
- **Error Handling**: Robust error detection and recovery
- **Logging**: Comprehensive status logging with clipboard export

## 📋 Requirements

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

## 🛠️ Installation

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

## 🔧 Configuration

### Default Settings
The application uses `config.json` for default settings:

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

### External Configuration
The tool can also read from external `config.txt` files located at `C:\AMS\config.txt` for motor settings arrays.

## 🎮 Usage Guide

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

### 3. Settings Tab

#### Configuration Management
- **Save Settings**: Save current configuration to file
- **Load Settings**: Load configuration from file
- **Reset to Defaults**: Restore default settings

#### General Settings
- **IP Address**: Default controller IP
- **Jog Speed**: Default jog speed
- **Axis Presets**: Per-axis default settings

## 🔍 Diagnostics Features

### Automatic Diagnostics
The diagnostics system performs comprehensive testing:

1. **Motor Detection**: Identifies connected motors on each axis
2. **Position Accuracy**: Tests positioning to 0, 250000, 500000, 250000, 0 counts
3. **Speed Testing**: Tests at multiple speeds (50,000 and 100,000 counts/sec)
4. **Motion Completion**: Verifies motion completes successfully
5. **Position Corrections**: Automatic correction of positioning errors

### Test Results
- **Position Accuracy**: Reports final position error in encoder counts
- **Motion Time**: Measures time to complete each move
- **Motor Status**: Confirms motor responsiveness and tuning
- **Error Detection**: Identifies mechanical constraints or servo issues

## 📊 Real-time Monitoring

### Encoder Position Display
- **4-Axis Display**: Shows position for all axes simultaneously
- **Live Updates**: Real-time position updates
- **Connection Status**: Visual indicators for each axis
- **Position Accuracy**: Displays current position with target comparison

### Status Logging
- **Comprehensive Logs**: All operations and test results
- **Timestamped Entries**: Chronological operation history
- **Error Reporting**: Detailed error messages and diagnostics
- **Clipboard Export**: Copy logs to clipboard for analysis

## 🛠️ Troubleshooting

### Common Issues

#### Connection Problems
- **Check Network**: Verify controller is on same network
- **Ping Test**: Use "Test Network Connection" to verify reachability
- **IP Address**: Confirm correct IP address in settings
- **Firewall**: Ensure firewall allows communication on controller port

#### Motor Not Responding
- **Servo Status**: Check if servo is enabled (SH command)
- **Motor Detection**: Run diagnostics to verify motor presence
- **PID Tuning**: Adjust PID parameters for better response
- **Following Error**: Check following error limits

#### Position Accuracy Issues
- **Position Reference**: Ensure axis is properly homed (DP command)
- **PID Tuning**: Fine-tune PID parameters for better accuracy
- **Speed Settings**: Reduce speed for more precise positioning
- **Mechanical Issues**: Check for mechanical constraints or backlash

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

## 🔧 Advanced Configuration

### External Config File
The tool can read motor settings from `C:\AMS\config.txt`:

```
motor_speed = [1024000, 1024000, 1024000, 1024000]
motor_accel = [2560000, 2560000, 2560000, 2560000]
motor_decel = [2560000, 2560000, 2560000, 2560000]
jog_speed = [128000, 128000, 128000, 128000]
motor_clicksPerTurn = [64000, 64000, 64000, 64000]
motor_turnsPerMM = [0.2, 0.2, 0.2, 0.2]
```

### Galil Commands
The tool uses standard Galil commands:
- `IP`, `SM`, `GW`: Network configuration
- `SH`, `MO`: Servo enable/disable
- `KP`, `KI`, `KD`: PID parameters
- `SP`, `AC`, `DC`: Speed, acceleration, deceleration
- `PA`, `PR`: Absolute/relative positioning
- `TP`: Tell position
- `MG _BG`: Motion status

## 📁 File Structure

```
galil-setup-tool/
├── main.py                 # Main GUI application
├── galil_functions.py      # Core motor control functions
├── galil_interface.py      # Galil controller interface
├── network_utils.py        # Network configuration utilities
├── config.json            # Default configuration
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── assets/               # Application assets
└── Galil_Setup_Tool_Distribution/  # Executable distribution
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Ryan McDowell** - *Initial work* - [rmcdowell-acertaralabs](https://github.com/rmcdowell-acertaralabs)

## 🙏 Acknowledgments

- Galil Motion Control for the DMC-4143 controller
- Acertara Labs for project support and testing
- Python community for excellent libraries and tools

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact: [rmcdowell-acertaralabs](https://github.com/rmcdowell-acertaralabs)

## 🔄 Version History

### v1.0.0 (Current)
- Initial release with full GUI functionality
- Network configuration and motor control
- PID tuning and diagnostics
- Real-time monitoring and logging
- Position accuracy improvements
- Auto-connection and motor detection

---

**Note**: This tool is designed for use with Galil DMC-4143 motion controllers. Ensure proper safety measures when working with industrial motion control systems.
