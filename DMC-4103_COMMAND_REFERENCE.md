# DMC-4103 Command Reference

This document provides a comprehensive list of all available commands for the Galil DMC-4103 controller.

## Table of Contents
- [Operators and Symbols](#operators-and-symbols)
- [Automatic Subroutines](#automatic-subroutines)
- [Motion Commands](#motion-commands)
- [Configuration Commands](#configuration-commands)
- [I/O Commands](#io-commands)
- [Program Control Commands](#program-control-commands)
- [Network Commands](#network-commands)
- [Utility Commands](#utility-commands)

---

## Operators and Symbols

### Basic Operators
| Command | Description |
|---------|-------------|
| `+` | Addition Operator |
| `-` | Subtraction Operator |
| `*` | Multiplication Operator |
| `/` | Division Operator |
| `%` | Modulo Operator |
| `&` | Bitwise AND Operator |
| `\|` | Bitwise OR Operator |
| `~` | Variable Axis Designator |

### Comparison Operators
| Command | Description |
|---------|-------------|
| `<` | Less than comparator |
| `<=` | Less than or Equal to comparator |
| `<>` | Not Equal to comparator |
| `=` | Equal to comparator |
| `>` | Greater than comparator |
| `>=` | Greater than or Equal to comparator |

### Special Characters
| Command | Description |
|---------|-------------|
| `;` | Semicolon (Command Delimiter) |
| `'` | Comment |
| `( , )` | Parentheses (order of operations) |
| `[,]` | Square Brackets (Array Index Operator) |
| `#` | Label Designator |
| `$` | Hexadecimal |
| `&` | JS subroutine pass variable by reference |
| `^` | JS subroutine stack variable |
| `^L^K` | Lock program |
| `^R^S` | Master Reset |
| `^R^V` | Revision Information |

---

## Mathematical Functions

| Command | Description |
|---------|-------------|
| `@ABS` | Absolute value |
| `@ACOS` | Inverse cosine |
| `@AN` | Analog Input Query |
| `@ASIN` | Inverse sine |
| `@ATAN` | Inverse tangent |
| `@COM` | Bitwise complement |
| `@COS` | Cosine |
| `@FLOT` | Convert Galil 4.2 to Floating Point |
| `@FRAC` | Fractional part |
| `@IN` | Read digital input |
| `@INT` | Integer part |
| `@OUT` | Read digital output |
| `@REAL` | Convert Floating Point to Galil 4.2 |
| `@RND` | Round |
| `@SIN` | Sine |
| `@SQR` | Square Root |
| `@TAN` | Tangent |

---

## Automatic Subroutines

| Command | Description |
|---------|-------------|
| `#AMPERR` | Amplifier error automatic subroutine |
| `#AUTO` | Subroutine to run automatically upon power up |
| `#AUTOERR` | Bootup Error Automatic Subroutine |
| `#CMDERR` | Command error automatic subroutine |
| `#COMINT` | Communication interrupt automatic subroutine |
| `#FWERR` | Firmware Error Automatic Subroutine |
| `#ININT` | Input interrupt automatic subroutine |
| `#LIMSWI` | Limit switch automatic subroutine |
| `#MCTIME` | MC command timeout automatic subroutine |
| `#POSERR` | Position error automatic subroutine |
| `#TCPERR` | Ethernet communication error automatic subroutine |

---

## Motion Commands

### Basic Motion
| Command | Description |
|---------|-------------|
| `AB` | Abort |
| `BG` | Begin |
| `BT` | Begin PVT Motion |
| `HM` | Home |
| `JG` | Jog |
| `MF` | Forward Motion to Position |
| `MR` | Reverse Motion to Position |
| `PA` | Position Absolute |
| `PR` | Position Relative |
| `ST` | Stop |

### Motion Parameters
| Command | Description |
|---------|-------------|
| `AC` | Acceleration |
| `DC` | Deceleration |
| `SP` | Speed |
| `HV` | Homing Velocity |
| `IT` | Independent Time Constant - Smoothing Function |
| `KS` | Step Motor Smoothing |

### Motion Control
| Command | Description |
|---------|-------------|
| `AD` | After Distance |
| `AI` | After Input |
| `AM` | After Move |
| `AP` | After Absolute Position |
| `AR` | After Relative Distance |
| `AS` | At Speed |
| `AT` | At Time |
| `AV` | After Vector Distance |
| `MC` | Motion Complete |
| `PT` | Position Tracking |

### Vector Motion
| Command | Description |
|---------|-------------|
| `VA` | Vector Acceleration |
| `VD` | Vector Deceleration |
| `VE` | Vector Sequence End |
| `VM` | Vector Mode |
| `VP` | Vector Position |
| `VR` | Vector Speed Ratio |
| `VS` | Vector Speed |
| `VV` | Vector Speed Variable |
| `PV` | PVT Data |

### Contour Motion
| Command | Description |
|---------|-------------|
| `CD` | Contour Distance |
| `CM` | Contour Mode |
| `CR` | Circle |
| `LE` | Linear Interpolation End |
| `LI` | Linear Interpolation Distance |
| `LM` | Linear Interpolation Mode |

### Gearing
| Command | Description |
|---------|-------------|
| `GA` | Master Axis for Gearing |
| `GD` | Gear Distance |
| `GR` | Gear Ratio |
| `GM` | Gantry mode |

### ECAM (Electronic Cam)
| Command | Description |
|---------|-------------|
| `EA` | Choose ECAM master |
| `EB` | Enable ECAM |
| `EC` | ECAM Counter |
| `EG` | ECAM go (engage) |
| `EM` | Ecam modulus |
| `EP` | Cam table master interval and phase shift |
| `EQ` | ECAM quit (disengage) |
| `ES` | Ellipse Scale |
| `ET` | Electronic cam table |
| `EW` | ECAM Widen Segment |
| `EY` | ECAM Cycle Count |

---

## Configuration Commands

### Motor Configuration
| Command | Description |
|---------|-------------|
| `MT` | Motor Type |
| `MO` | Motor Off |
| `SH` | Servo Here |
| `AG` | Amplifier Gain |
| `AU` | Set amplifier current loop |
| `BZ` | Brushless Zero |
| `BA` | Brushless Axis |
| `BC` | Brushless Calibration |
| `BD` | Brushless Degrees |
| `BI` | Brushless Inputs |
| `BM` | Brushless Modulo |
| `BR` | Brush Axis |
| `BX` | Sine Amp Initialization |

### PID Control
| Command | Description |
|---------|-------------|
| `KP` | Proportional Constant |
| `KI` | Integrator |
| `KD` | Derivative Constant |
| `IL` | Integrator Limit |
| `FA` | Acceleration Feedforward |
| `FV` | Velocity Feedforward |

### Limits and Safety
| Command | Description |
|---------|-------------|
| `BL` | Reverse Software Limit |
| `FL` | Forward Software Limit |
| `LD` | Limit Disable |
| `SD` | Limit Switch Deceleration |
| `ER` | Error Limit |
| `TK` | Peak Torque Limit |
| `TL` | Torque Limit |

### Encoder Configuration
| Command | Description |
|---------|-------------|
| `CE` | Configure Encoder |
| `DE` | Dual (Auxiliary) Encoder Position |
| `DV` | Dual Velocity (Dual Loop) |
| `OA` | Off on encoder failure |
| `OT` | Off on encoder failure time |
| `OV` | Off on encoder failure voltage |

### Stepper Motor
| Command | Description |
|---------|-------------|
| `LC` | Low Current Stepper Mode |
| `YA` | Step Drive Resolution |
| `YB` | Step Motor Resolution |
| `YS` | Stepper Position Maintenance Mode Enable, Status |

---

## I/O Commands

### Digital I/O
| Command | Description |
|---------|-------------|
| `OB` | Output Bit |
| `OP` | Output Port |
| `SB` | Set Bit |
| `CB` | Clear Bit |

### Analog I/O
| Command | Description |
|---------|-------------|
| `AO` | Analog Output |
| `AF` | Analog Feedback Select |
| `AQ` | Analog Input Configuration |

### Interrupts
| Command | Description |
|---------|-------------|
| `II` | Input Interrupt |
| `EI` | Event Interrupts |
| `UI` | User Interrupt |
| `CI` | Configure Communication Interrupt |

### Timing
| Command | Description |
|---------|-------------|
| `OC` | Output Compare |
| `DT` | Delta Time |
| `TM` | Update Time |
| `WT` | Wait |

---

## Program Control Commands

### Program Structure
| Command | Description |
|---------|-------------|
| `IF` | IF conditional statement |
| `ELSE` | Else function for use with IF conditional statement |
| `ENDIF` | End of IF conditional statement |
| `JP` | Jump to Program Location |
| `JS` | Jump to Subroutine |
| `EN` | End |
| `XQ` | Execute Program |

### Program Management
| Command | Description |
|---------|-------------|
| `ED` | Edit |
| `DL` | Download |
| `UL` | Upload |
| `BP` | Burn Program |
| `BV` | Burn Variables and Array |
| `BN` | Burn |
| `LS` | List |
| `LL` | List Labels |
| `LA` | List Arrays |
| `LV` | List Variables |

### Debugging
| Command | Description |
|---------|-------------|
| `BK` | Breakpoint |
| `SL` | Single Step |
| `TR` | Trace |
| `HX` | Halt Execution |

### Comments and Documentation
| Command | Description |
|---------|-------------|
| `REM` | Remark |
| `EO` | Echo |

---

## Network Commands

| Command | Description | Format | Notes |
|---------|-------------|--------|-------|
| `IA` | IP Address | `IA n0,n1,n2,n3` | Sets IP address in comma-separated format (bytes in standard order) |
| `SM` | Subnet Mask | `SM n0,n1,n2,n3` | Sets subnet mask in comma-separated format |
| `GW` | Gateway | `GW n0,n1,n2,n3` | Sets gateway address in comma-separated format |
| `DH` | DHCP Client Enable | `DH 0` or `DH 1` | 0=disable DHCP, 1=enable DHCP |
| `BN` | Burn Settings | `BN` | Saves network settings to non-volatile memory |
| `IH` | Open IP Handle | `IH` | Opens IP communication handle |
| `TH` | Tell Ethernet Handle | `TH` | Reports Ethernet handle information |
| `WH` | Which Handle | `WH` | Reports which handle is active |
| `MU` | Multicast Address | `MU n0,n1,n2,n3` | Sets multicast address |
| `IK` | Block Ethernet ports | `IK` | Blocks Ethernet ports |

### Network Command Examples

| Command | Example | Description |
|---------|---------|-------------|
| `IA` | `IA 192,168,1,100` | Set IP address to 192.168.1.100 |
| `SM` | `SM 255,255,255,0` | Set subnet mask to 255.255.255.0 |
| `GW` | `GW 192,168,1,1` | Set gateway to 192.168.1.1 |
| `DH` | `DH 0` | Disable DHCP (use static IP) |
| `DH` | `DH 1` | Enable DHCP |
| `BN` | `BN` | Burn all settings to flash memory |
| **Combined** | `DH 0;IA 192,168,1,100` | **Recommended**: Disable DHCP and set IP in one command |

### Network Query Commands

| Command | Description | Example Response |
|---------|-------------|------------------|
| `MG _IP` | Query current IP address | Returns IP in comma-separated format |
| `MG _SM` | Query current subnet mask | Returns subnet mask in comma-separated format |
| `MG _GW` | Query current gateway | Returns gateway in comma-separated format |

---

## Utility Commands

### Status and Information
| Command | Description |
|---------|-------------|
| `ID` | Identify |
| `TP` | Tell Position |
| `TV` | Tell Velocity |
| `TT` | Tell Torque |
| `TB` | Tell Status Byte |
| `TC` | Tell Error Code |
| `TE` | Tell Error |
| `TI` | Tell Inputs |
| `TS` | Tell Switches |
| `TZ` | Tell I O Configuration |
| `TD` | Tell Dual Encoder |
| `TA` | Tell amplifier error status |
| `MG` | Message |
| `CW` | Copyright information and Data Adjustment bit on/off |

### Data Management
| Command | Description |
|---------|-------------|
| `DM` | Dimension Array |
| `DA` | Deallocate Variables and Arrays |
| `RA` | Record Array |
| `RC` | Record |
| `RD` | Record Data |
| `QU` | Upload Array |
| `QD` | Download Array |
| `QR` | I O Data Record |
| `QZ` | Return Data Record information |
| `ZA` | User Data Record Variables |

### Variables and Arrays
| Command | Description |
|---------|-------------|
| `DP` | Define Position |
| `RP` | Reference Position |
| `OF` | Offset |
| `PF` | Position Format |
| `VF` | Variable Format |
| `LZ` | Omit leading zeros |

### Special Functions
| Command | Description |
|---------|-------------|
| `AL` | Arm Latch |
| `RL` | Report Latched Position |
| `FE` | Find Edge |
| `FI` | Find Index |
| `QH` | Query Hall State |
| `QQ` | Clear Sample Time Overflow |
| `QS` | Error Magnitude |
| `SC` | Stop Code |
| `HS` | Handle Assignment Switch |
| `BW` | Brake Wait |

### Error Handling
| Command | Description |
|---------|-------------|
| `RE` | Return from Error Routine |
| `RI` | Return from Interrupt Routine |
| `OE` | Off-on-Error |
| `AZ` | Clear Latched Amplifier Errors |
| `CS` | Clear Sequence |
| `ZS` | Zero Subroutine Stack |

### Communication
| Command | Description |
|---------|-------------|
| `CC` | Configure Communications Port 2 |
| `CF` | Configure Unsolicited Messages Handle |
| `DR` | Configures I O Data Record Update Rate |
| `US` | USB port configuration |
| `P2CD` | Serial port 2 code |
| `P2CH` | Serial port 2 character |
| `P2NM` | Serial port 2 number |
| `P2ST` | Serial port 2 string |

### Modbus
| Command | Description |
|---------|-------------|
| `MB` | Modbus |
| `ME` | Modbus array write enable |
| `MW` | Modbus Wait |

### Filtering and Control
| Command | Description |
|---------|-------------|
| `NB` | Notch Bandwidth |
| `NF` | Notch Frequency |
| `NZ` | Notch Zero |
| `PL` | Pole |
| `YR` | Error Correction |
| `YC` | Encoder Resolution |

### Special Operations
| Command | Description |
|---------|-------------|
| `NO` | Operation |
| `PW` | Password |
| `RS` | Reset |
| `CA` | Coordinate Axes |
| `CN` | Configure |
| `TN` | Vector Tangent |
| `TW` | Timeout for MC trippoint |
| `TIME` | Time Operand |

---

## Operand Overview

### System Operands
| Operand | Description |
|---------|-------------|
| `_` | Operand Overview |
| `_GP` | Gearing Phase Differential Operand |
| `_LF` | Forward Limit Switch Operand |
| `_LR` | Reverse Limit Switch Operand |

---

## Usage Notes

1. **Command Format**: Most commands can be followed by parameters. Use semicolons (`;`) to separate multiple commands on the same line.

2. **Case Sensitivity**: Commands are case-sensitive and should be entered in uppercase.

3. **Parameters**: Many commands require parameters. Refer to the specific command documentation for parameter requirements.

4. **Network Commands**: 
   - Use the `IA` command with comma-separated format (e.g., `IA 192,168,1,100`)
   - IP address bytes are in standard order: `IA n0,n1,n2,n3` where n0=byte0, n1=byte1, n2=byte2, n3=byte3
   - **Recommended**: Use combined command `DH 0;IA n0,n1,n2,n3` to avoid disconnection issues
   - Always disable DHCP (`DH 0`) before setting static IP address
   - Use `BN` command to burn network settings to non-volatile memory

5. **Save Configuration**: Use the `BN` command to burn settings to non-volatile memory. This command typically takes 1 second to execute and must not be interrupted.

6. **Error Handling**: Use automatic subroutines (starting with `#`) for error handling and system events.

---

*This reference covers all available commands for the Galil DMC-4103 controller. For detailed parameter information and usage examples, refer to the official Galil Motion Control documentation.*
