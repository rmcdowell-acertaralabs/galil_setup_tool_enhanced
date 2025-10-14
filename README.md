# Galil Setup Tool

A streamlined GUI application for configuring and controlling Galil DMC-4143 motion controllers. Provides motor tuning and network configuration with automatic IP discovery via COM port.

**Current Version**: 2.5  
**Controller**: Galil DMC-4143 / DMC-4103  
**Supported Axes**: A and B (C and D not fitted on this hardware)

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/rmcdowell-acertaralabs/galil-setup-tool.git
cd galil-setup-tool
pip install -r requirements.txt
python main.py
```

### First-Time Setup

1. **Connect via COM Port** (USB cable)
   - Go to "Network Config" tab
   - Click "Refresh COM Ports" → Select your COM port → Click "Connect via COM Port"
   - Software automatically queries and displays the controller's IP address

2. **Set IP Address** (if showing "N/A")
   - Use the manual command box to send:
     ```
     DH 0
     IA 192,168,1,100
     BN
     ```
   - Power cycle the controller
   
3. **Connect via Ethernet** (faster than COM)
   - Connect Ethernet cable
   - Use discovered IP to connect

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.8+
- **Hardware**: Galil DMC-4143 or DMC-4103 controller
- **Connections**: USB cable (COM port) and/or Ethernet cable

---

## ✨ GUI Features

The application provides two main pages accessible via the left sidebar navigation:

### 🌐 Network Configuration Page

**Connection Methods**:
- **IP/Ethernet Connection** - Fast, reliable network connection
- **COM Port Connection** - USB serial connection (auto-queries IP)
- **Auto-Discovery** - Find controllers on network and COM ports

**Network Management**:
- Query controller's current IP address (automatic via COM)
- Set new IP address with manual commands
- DHCP enable/disable
- Subnet mask and gateway configuration
- Controller information display (model, firmware, status)

**Manual Command Interface**:
- Send any Galil command directly to controller
- All network commands validated (IA, DH, SM, GW, TH, etc.)
- Real-time command responses
- Error detection and feedback

### 🔧 Motor Tuning & Setup Page

**Motor Setup Section**:
- **Axis Selection** - Configure axes A, B, or C
- **Motor Presets** - Load verified configurations (axis_a_verified, axis_b_template, etc.)
- **Motor Specifications** - Encoder counts, pole pairs, index/hall sensors
- **Commutation Method** - BI/BC (Hall Sensor-based) - VERIFIED WORKING ✓

**Setup Buttons**:
- **🚀 Run Complete Setup** - Applies all motor configuration automatically
- **📋 Step-by-Step Setup** - Guided setup process with manual input dialogs
- **⏹️ Stop Setup** - Stop current setup process

**Motor Testing Terminal**:
- **Step-by-Step Testing Guide** - Visual guide for complete motor setup process
- **Quick Command Buttons** - Pre-configured commands organized by phase:
  - **Quick Commands (Step 1-3)**: Basic configuration (MOA, MTA=1, CEA=0, BAA, BMA=5000, KPA=6, KDA=64, KIA=0.1, TLA=5, TKA=9.99, AGA=1, AUA=0, DPA=0)
  - **BI/BC Initialization (Step 2)**: Manual hall sensor initialization (BIA=-1, BCA, SHA, JGA=500, BGA, STA)
  - **Motion Profile (Step 4)**: Motion parameters (ERA=500000, SPA=1024000, ACA=2560000, DCA=2560000, JGA=128000, PRA=2500000, BGA)
  - **Motion Testing (Step 5-7)**: Testing commands (DPA=0, MG _TAA, SHA, PRA=10000, BGA, MG _BGA, MG _TPA, MG _TEA)
  - **Diagnostics**: Status monitoring (MG _TPA, MG _TEA, MG _BGA, MG _MOA, etc.)
  - **Emergency**: Safety commands (STA, AB 1, MOA, BN)
- **Terminal Interface** - Send custom commands with real-time output
- **Command History** - Track all commands sent with timestamps

**Motor Control**:
- Verified settings for Cymatix E017 brushless motor
- PID configuration (KP=6.0, KD=64.0, KI=0.0)
- BI/BC initialization (prevents motor overheating)
- Position accuracy: 94-99%

### 🛡️ Built-in Protection

- **Command Validation** - All commands validated against DMC-4103 reference
- **Thread-Safe Operation** - Prevents connection corruption
- **Automatic Servo Management** - Monitors and re-enables servos as needed
- **Error Recovery** - Graceful handling of command errors
- **Settings Protection** - Prevents accidental changes to verified motor settings

---

## 📖 Usage

### Motor Tuning Workflow

1. **Connect to controller** (Network Config page)
2. **Go to Motor Tuning** page
3. **Select axis** (A, B, or C)
4. **Load preset** - Choose "axis_a_verified" for Axis A (or template for others)
5. **Run Complete Setup** - Applies all motor configuration
6. **Use Quick Commands** - Test and diagnose motor
7. **Save with BN** - Burn settings to flash memory

### Network Configuration Workflow

1. **Connect via COM port** first (USB)
2. **Software queries IP** automatically (using `IA ?` command)
3. **If no IP**, set manually:
   - Send: `DH 0` (disable DHCP)
   - Send: `IA 192,168,1,100` (your desired IP)
   - Send: `SM 255,255,255,0` (subnet mask)
   - Send: `BN` (save to flash)
   - Power cycle controller
4. **Connect via Ethernet** using the IP address

---

## 🔧 Network Commands Reference

### Query Commands

| Command | Purpose | Example Response |
|---------|---------|------------------|
| `IA ?` | Query current IP | `192,168,1,100` |
| `DH ?` | Query DHCP status | `0` or `1` |
| `TH` | Network info | `CONTROLLER IP ADDRESS...` |
| `ID` | Controller identity | `DMC-4143 Rev 1.2a...` |

### Configuration Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `DH 0` | Disable DHCP | `DH 0` |
| `IA n0,n1,n2,n3` | Set IP (comma format!) | `IA 192,168,1,100` |
| `SM n0,n1,n2,n3` | Set subnet mask | `SM 255,255,255,0` |
| `GW n0,n1,n2,n3` | Set gateway | `GW 192,168,1,1` |
| `BN` | Save to flash | `BN` |

**Critical Notes**:
- ⚠️ Use **commas**, not periods: `IA 192,168,1,100` ✅ not `IA 192.168.1.100` ❌
- ⚠️ Send `DH 0` before `IA` command (or you get Error 163)
- ⚠️ Always send `BN` to save (or settings lost on reboot)
- ⚠️ Power cycle required after `BN` for changes to take effect

---

## 🔥 Motor Configuration (Cymatix E017 - Verified Working)

### Complete Setup Sequence

```
STEP 1: APPLY VERIFIED CONFIGURATION
═══════════════════════════════════════
MOA                     Motor off
MTA=1                   Standard servo motor
CEA=0                   Normal quadrature encoder
BAA                     Enable brushless
BMA=5000                Brushless modulo (4 pole pairs)
KPA=6                   Proportional gain
KDA=64                  Derivative gain
KIA=0.1                 Integral gain
TLA=5                   Torque limit
TKA=9.99                Peak torque limit
AGA=1                   Amplifier gain
AUA=0                   Current loop gain

STEP 2: INITIALIZE BRUSHLESS (BI/BC METHOD)
═══════════════════════════════════════
BIA=-1                  Initialize with hall sensors
BCA                     Enable hall-based calibration
SHA                     Enable servo
JGA=500                 Set slow jog speed

MANUAL STEPS:
1. Click 'BGA' button to begin jog motion
2. Watch for hall sensor transition (motor moves slowly)
3. Click 'STA' button to stop motion when ready
4. Controller automatically calibrates commutation

STEP 3: ZERO POSITION
═══════════════════════════════════════
DPA=0                   Zero position

STEP 4: SET MOTION PROFILE
═══════════════════════════════════════
ERA=500000              Error limit
SPA=1024000             Speed
ACA=2560000             Acceleration
DCA=2560000             Deceleration
JGA=128000              Jog speed
PRA=2500000             Position relative move
BGA                     Begin motion
```

### Critical Settings for Axis A

| Parameter | Value | Why Critical |
|-----------|-------|--------------|
| MT | 1 | Standard servo motor |
| CE | 0 | Normal quadrature encoder |
| BM | 5000 | Brushless modulo (4 pole pairs × 1250) |
| KP | 6.0 | Higher causes oscillation |
| KD | 64.0 | Provides damping |
| KI | 0.1 | Small integral gain |
| TL | 5.0 | Torque limit (max for AG=1) |
| BI/BC | Required | Hall sensor-based commutation |

**How BI/BC Method Works**:
The BI/BC initialization process is **manual and controlled** by the user:

1. **BIA=-1**: Configures the controller to use dedicated hall sensor inputs
2. **BCA**: Enables hall-based commutation calibration
3. **SHA**: Enables the servo motor
4. **JGA=500**: Sets a slow jog speed (500 counts/sec)
5. **BGA**: User clicks button to begin jog motion
6. **Hall Transition**: User watches for hall sensor transition during the jog
7. **STA**: User clicks button to stop motion when ready

**Manual Control Required**: The user controls when to start and stop the jog motion. This gives you full control over the initialization process and allows you to observe the hall sensor transition.

**Results**:
- ✅ Motor stays cool (no overheating)
- ✅ 94-99% position accuracy
- ✅ No oscillation or vibration
- ✅ Fully automated hall sensor-based commutation

---

## 🛠️ Troubleshooting

### IP Shows "N/A"

**Meaning**: Controller has no IP configured (DHCP mode, no DHCP server)

**Fix**: Set IP manually via COM port
```
DH 0                    (Disable DHCP)
IA 192,168,1,100        (Set IP - use your IP)
SM 255,255,255,0        (Subnet mask)
BN                      (Save - wait 5 sec)
(Power cycle controller)
```

### "Invalid numeric value" Error

**For IP commands** - Fixed in v2.5, validator now accepts comma-separated IP format

**For motor commands (AU, AG, etc.)** - These are axis-specific commands and require correct format:

**✅ WORKING AU Command Formats**:
```
AUA=9       (Axis inline with equals)
AU A=9      (Space with axis=value)
AUA 9       (Axis inline with space)
```

**❌ NOT WORKING**:
```
AU 9        (Missing axis - returns error)
AU A 9      (Wrong separator)
```

**Same applies to AG, KP, KD, KI, TL, TK, etc.** - All axis-specific commands need the axis letter.

**Exception**: Some commands like OE, ER, and MO can also be used globally (no axis) to apply to all axes:
```
OE 0        (Applies to all axes)
OEA=0       (Applies to Axis A only)
ER 200000   (Applies to all axes)
ERA=200000  (Applies to Axis A only)
```

### Error 163: "IA command not valid when DHCP mode enabled"

**Fix**: Disable DHCP first
```
DH 0            (Disable DHCP)
IA 192,168,1,100        (Then set IP)
BN              (Save)
```

### Firmware Version Not Showing Correctly

**Fixed in v2.5** - Simplified ID command parsing

The controller information now correctly displays:
- Model (e.g., "DMC4143")  
- Firmware (e.g., "DMC4143 Rev 1.2a")
- Serial number
- IP address

**How it works**: Uses the `ID` command and parses the first line starting with "FW"

### AU Command Returns "?" (Question Mark)

**Cause**: AU command requires motor to be OFF first (MO command)

**Fix**: Use correct AU value for your amplifier type
- ✅ **AUA=0** (Valid for AMP-43540 - Inverter mode, Normal current loop gain)
- ❌ **AUA=9** (Not supported on AMP-43540 amplifier)

**Fixed in v2.5**: 
- Changed AU value from 9 to 0 for AMP-43540 compatibility
- MOA is part of normal setup sequence (send MOA first, then AUA=0)

### Motor Overheating

**Cause**: Wrong settings (MT, BM, or PID gains)

**Fix**: Use verified Axis A configuration (see above)

### Command Returns "?"

**Common Causes**:
- Wrong command syntax (check spacing: `SHA` not `SH A`)
- Status variables without MG (`MG _MOA` not `_MOA`)
- DHCP enabled when setting IP
- Wrong comma/period format for IP addresses

---

## 📋 DMC-4103 Command Compliance

### Correct Command Formats

| Type | Correct | Wrong |
|------|---------|-------|
| Servo Enable | `SHA`, `SHB` | `SH A`, `SH B` |
| Tell Position | `TPA`, `TPB` | `TP A`, `TP B` |
| Begin Motion | `BGA`, `BGB` | `BG A`, `BG B` |
| Motor Status | `MG _MOA` | `_MOA` |
| IP Address | `IA 192,168,1,100` | `IA 192.168.1.100` |

### Helper Functions

```python
def gnum(cmd: str) -> float:
    """Robust numeric parser"""
    s = g.GCommand(cmd).strip()
    return float(s.splitlines()[0].split()[0])

# Check servo status
mo = gnum(f"MG _MOA")     # 0 = ON, 1 = OFF

# Enable servo
g.GCommand("SHA")
time.sleep(0.05)

# Check if motion complete
busy = gnum(f"MG _BGA")   # 1 = busy, 0 = idle
```

---

## 🎯 Common Tasks

### Set Controller IP Address

1. Connect via COM port
2. Send commands:
   ```
   DH 0
   IA 192,168,1,100
   BN
   ```
3. Power cycle
4. Connect via Ethernet

### Configure a New Motor

1. Go to Motor Tuning page
2. Select axis (A, B, or C)
3. Load preset or enter specifications
4. Run Complete Setup
5. Test with quick command buttons
6. Save with `BN` command

### Query Network Settings

1. Connect via COM port
2. Send: `IA ?` (shows current IP)
3. Send: `DH ?` (shows DHCP status)
4. Send: `TH` (shows full network info)
5. Send: `ID` (shows controller model/firmware)

---

## 📝 Changelog

### [2.5] - BI/BC Commutation Method & Complete GUI Integration (October 2025)

**Major Updates**:
- ✅ **BI/BC Commutation Method** - Switched from BZ to hall sensor-based initialization
- ✅ **Complete GUI Integration** - All motor setup functions integrated into GUI
- ✅ **Step-by-Step Setup** - Guided setup process with manual input dialogs
- ✅ **Quick Command Buttons** - Pre-configured commands organized by setup phase
- ✅ **Command Validation** - All 59 commands validated against DMC-4103 reference

**Problems Fixed**:
- "Invalid numeric value" error when entering IP commands
- "AU command no longer works" - Fixed axis requirement  
- "IP shows as N/A" - Fixed IP query command
- "Firmware version not showing correctly" - Simplified ID command parsing
- CN command missing from validator
- OE and ER requiring axis when used globally

**Changes**:
- ✅ Fixed IP query from invalid `IP` to correct `IA ?` command
- ✅ Added 10 commands to validator (IA, DH, SM, GW, TH, IH, WH, CF, ID, CN)
- ✅ Added proper validation for comma-separated IP format
- ✅ Fixed AU, AG, and other axis commands - now validate correctly
- ✅ Fixed OE and ER to work both globally and per-axis
- ✅ Added CN (Configure) for limit switch polarity
- ✅ Automatic IP query when connecting via COM port
- ✅ **Simplified firmware parsing** - Now correctly extracts from ID response
- ✅ **All 59 commands now fully validated** - Complete DMC-4103 coverage

**Validation Test Results**: 44/44 critical commands pass ✅

**Files Modified**:
- `command_validator.py` - Added 10 commands + proper validation for all formats
- `galil_combined.py` - Fixed IP query using `IA ?` and `TH` commands
- `main.py` - Automatic IP query on COM connection + simplified firmware parsing
- `gui_framework.py` - Complete GUI integration with BI/BC method
- `controller_servo_maintenance.py` - Updated to BI/BC commutation
- `motor_setup.py` - Updated default method to BI/BC

### [2.4] - Critical Command Compliance Fixes (October 2025)

- Fixed all status variable reads to use `MG _VAR` format
- Thread-safe connection with serialized command pipe
- Limited to axes A and B only (hardware limitation)
- Replaced WT/AM with host-side equivalents
- Fixed command syntax (removed spaces)

### [2.3] - Motor Overheating Solution (October 2025)

- Verified motor configuration for Cymatix E017 motor
- BI/BC commutation method (hall sensor-based, stable)
- Optimized PID gains (KP=6, KD=64, KI=0)
- Motor stays cool with 94-99% position accuracy

---

## 🔒 Hardware Configuration

**Galil DMC-4143 Specifications**:
- **Axes**: A and B only (C and D not fitted)
- **Digital I/O**: 8 inputs, 8 outputs (not 16)
- **Encoder**: 20,000 counts/rev (Axis A verified)
- **Motor**: Cymatix E017 brushless (4 pole pairs)
- **Connection**: Ethernet or USB (COM port)

---

## 📞 Support

### Documentation

- **Complete Guide**: This README (all documentation consolidated here)
- **Command Reference**: `command_validator.py` (lines 1-11,378)
- **Quick Reference**: `QUICK_REFERENCE_MOTOR_A.txt`

### Getting Help

1. Check the persistent log in the software
2. Review troubleshooting sections above
3. Verify controller firmware with `ID` command
4. Contact: [rmcdowell-acertaralabs](https://github.com/rmcdowell-acertaralabs)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## ✅ Command Validator Status

**Total Commands**: 59 validated Galil DMC-4103 commands  
**Test Results**: 44/44 critical commands pass ✅  
**Coverage**: Complete command set for motor control and network configuration

**Command Categories**:
- **Motion/Servo** (11): MO, SH, ST, BG, AM, TP, DP, PA, PR, JG, FI
- **Brushless** (7): BA, BM, BX, BZ, BC, BI, QH
- **Encoder/Latch** (3): CE, AL, RL
- **Safety/Limits** (5): OE, ER, FL, BL, CN
- **PID/Tuning** (13): KP, KI, KD, TL, TK, OF, AG, AU, SP, AC, DC, SD, MT
- **Digital I/O** (2): SB, CB
- **System** (8): BN, RS, AB, AZ, TC, TE, MG, WT, SL, ID
- **Network** (8): IA, DH, SM, GW, TH, IH, WH, CF

**Special Validation Features**:
- ✅ Comma-separated IP format (IA, SM, GW)
- ✅ Bracket syntax for BX/BZ (<1000>1500)
- ✅ Multi-axis parameters (AC A=1000,B=2000)
- ✅ Global vs per-axis (MO, OE, ER)
- ✅ Status variable reads (MG _VAR)

---

## 📊 Files and Modules

**Core Application**:
- `main.py` - Main application entry point
- `gui_framework.py` - GUI components (2 pages: Motor Tuning, Network Config)
- `galil_combined.py` - Controller communication
- `network_combined.py` - Network utilities and discovery
- `command_validator.py` - 59 validated DMC-4103 commands (11,408 lines)

**Motor Configuration**:
- `controller_servo_maintenance.py` - Motor setup helpers
- `motor_setup.py` - Motor setup and tuning system
- `motor_presets.py` - Motor preset configurations
- `config.json` - Verified motor settings

**Testing**:
- `comprehensive_testing.py` - Complete motor testing suite
- `discovery.py` - Axis discovery and probing

**Utilities**:
- `gclib.py` - Galil communications library (Python wrapper)
- `utils.py` - Helper functions
- `galil_connection.py` - Thread-safe connection management

---

## ⚠️ Important Notes

1. **Thread Safety**: Only one command at a time - gclib is NOT thread-safe
2. **Axes**: Only A and B are fitted on this DMC-4143 hardware
3. **Digital I/O**: Maximum 8 outputs (not 16)
4. **Network Changes**: Always require power cycle to take effect
5. **BN Command**: Required to save settings to flash memory
6. **Motor Settings**: Use verified configuration for Axis A to prevent overheating

---

**Built for**: Galil DMC-4143 motion controllers  
**Optimized for**: Cymatix E017 brushless motors  
**Status**: Production ready with verified motor configuration  
**Safety**: All commands validated against DMC-4103 reference manual