# Galil Setup Tool

A comprehensive GUI application for configuring, testing, and controlling Galil motion controllers. This tool provides an intuitive interface for network configuration, motor setup, motion control, diagnostics, and real-time monitoring of Galil DMC-4103 and DMC-4143 controllers.

## 🚀 Quick Start

### Installation

**Option 1: Python Installation**
```bash
git clone https://github.com/rmcdowell-acertaralabs/galil-setup-tool.git
cd galil-setup-tool
pip install -r requirements.txt
python main.py
```

**Option 2: Executable Installation**
1. Download the latest release from [Releases](https://github.com/rmcdowell-acertaralabs/galil-setup-tool/releases)
2. Extract and run `Galil_Setup_Tool.exe`

### System Requirements
- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.7 or higher (for Python installation)
- **Network**: Ethernet connection for controller communication

## 📋 Key Features

- **Network Configuration**: Set IP, subnet mask, gateway, and hostname with precise DMC-4103 command support
- **Motor Control**: Smooth jogging, absolute/relative positioning, speed control
- **PID Tuning**: Real-time servo loop tuning with live feedback
- **Diagnostics**: Comprehensive motor testing and position accuracy verification with enhanced motor detection
- **Real-time Monitoring**: Live encoder position display for all axes (A, B, C, D)
- **Manual Command Interface**: Direct DMC-4103 command input with real-time response display
- **Brushless Motor Setup**: Complete 4-step brushless motor configuration process
- **Auto-Connection**: Automatic controller detection and connection
- **Configuration Management**: Save/load settings with external config file support
- **Mouse Wheel Support**: Scroll wheel navigation for all pages
- **Command Reference**: Comprehensive DMC-4103 command documentation

## 🆕 Recent Updates

### Version 2.0 - Enhanced DMC-4103 Support
- **Manual Command Interface**: Added direct command input box for sending DMC-4103 commands
- **Enhanced Motor Detection**: Improved motor detection algorithm with better error handling
- **Command Reference**: Added comprehensive DMC-4103 command documentation
- **Network Configuration**: Simplified to focus on IP address setting and burning
- **Mouse Wheel Support**: Added scroll wheel navigation for all pages
- **Improved Diagnostics**: Enhanced motor detection with proper timing and verification
- **Quick Command Buttons**: Pre-configured buttons for common DMC-4103 commands

### Key Improvements
- Fixed motor detection issues with proper motor type setting and timing
- Enhanced error handling and logging for better troubleshooting
- Improved user interface with better layout and navigation
- Added real-time command response display with timestamps

## 📚 Documentation

For complete documentation including:
- Detailed usage guides
- Network configuration instructions
- Motor setup procedures
- Troubleshooting guides
- Technical specifications
- DMC-4103 command reference
- Changelog

**See: [COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)**  
**Command Reference: [DMC-4103_COMMAND_REFERENCE.md](DMC-4103_COMMAND_REFERENCE.md)**

## 🔧 Configuration

The application uses `config.json` for default settings and can read external motor settings from `C:\AMS\config.txt`.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For support and questions:
- Create an issue on GitHub
- Contact: [rmcdowell-acertaralabs](https://github.com/rmcdowell-acertaralabs)

---

**Note**: This tool is designed for use with Galil DMC-4143 motion controllers. Ensure proper safety measures when working with industrial motion control systems.
