# Galil Setup Tool

A GUI application for configuring and controlling Galil DMC-4143 motion controllers. Provides motor tuning and network configuration.

**Controller**: Galil DMC-4143 / DMC-4103  
**Supported Axes**: A and B (C and D not fitted on this hardware)

---

## Quick Start

### Installation
```bash
pip install -r requirements.txt
python main.py
```

### System Requirements
- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.8+
- **Hardware**: Galil DMC-4143 or DMC-4103 controller
- **Connections**: USB cable (COM port) and/or Ethernet cable

---

## Usage

### Network Configuration
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

### Motor Tuning
1. **Connect to controller** (Network Config page)
2. **Go to Motor Tuning** page
3. **Select axis** (A, B, or C)
4. **Load preset** - Choose "axis_a_verified" for Axis A
5. **Run Complete Setup** - Applies all motor configuration
6. **Use Quick Commands** - Test and diagnose motor
7. **Save with BN** - Burn settings to flash memory

---

## Key Features

### Network Configuration Page
- **IP/Ethernet Connection** - Fast, reliable network connection
- **COM Port Connection** - USB serial connection (auto-queries IP)
- **Auto-Discovery** - Find controllers on network and COM ports
- **Manual Command Interface** - Send any Galil command directly to controller

### Motor Tuning Page
- **Axis Selection** - Configure axes A, B, or C
- **Motor Presets** - Load verified configurations
- **Complete Setup** - Applies all motor configuration automatically
- **Quick Command Buttons** - Pre-configured commands organized by phase
- **Terminal Interface** - Send custom commands with real-time output

---

## Critical Network Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `IA ?` | Query current IP | `192,168,1,100` |
| `DH 0` | Disable DHCP | `DH 0` |
| `IA n0,n1,n2,n3` | Set IP (comma format!) | `IA 192,168,1,100` |
| `BN` | Save to flash | `BN` |

**Important Notes**:
- ⚠️ Use **commas**, not periods: `IA 192,168,1,100` ✅ not `IA 192.168.1.100` ❌
- ⚠️ Send `DH 0` before `IA` command (or you get Error 163)
- ⚠️ Always send `BN` to save (or settings lost on reboot)
- ⚠️ Power cycle required after `BN` for changes to take effect

---

## Motor Configuration (Cymatix E017 - Verified Working)

### Complete Setup Sequence
```
STEP 1: APPLY VERIFIED CONFIGURATION
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
BIA=-1                  Initialize with hall sensors
BCA                     Enable hall-based calibration
SHA                     Enable servo
JGA=500                 Set slow jog speed
BGA                     Begin motion (user controlled)
STA                     Stop motion (user controlled)

STEP 3: ZERO POSITION
DPA=0                   Zero position

STEP 4: SET MOTION PROFILE
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

**Results**:
- ✅ Motor stays cool (no overheating)
- ✅ 94-99% position accuracy
- ✅ No oscillation or vibration

---

## Troubleshooting

### IP Shows "N/A"
**Fix**: Set IP manually via COM port
```
DH 0                    (Disable DHCP)
IA 192,168,1,100        (Set IP - use your IP)
SM 255,255,255,0        (Subnet mask)
BN                      (Save - wait 5 sec)
(Power cycle controller)
```

### Error 163: "IA command not valid when DHCP mode enabled"
**Fix**: Disable DHCP first
```
DH 0            (Disable DHCP)
IA 192,168,1,100        (Then set IP)
BN              (Save)
```

### Motor Overheating
**Fix**: Use verified Axis A configuration (see above)

### Command Returns "?"
**Common Causes**:
- Wrong command syntax (check spacing: `SHA` not `SH A`)
- Status variables without MG (`MG _MOA` not `_MOA`)
- DHCP enabled when setting IP
- Wrong comma/period format for IP addresses

---

## Important Notes

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