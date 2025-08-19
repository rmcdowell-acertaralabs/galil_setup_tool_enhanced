# IP Settings Save Troubleshooting Guide for DMC-4143

## Problem Description

IP settings are not being saved to the DMC-4143 controller, causing them to revert after power cycles.

## Root Causes and Solutions

### 1. DMC-4143 Specific Requirements

**Issue**: DMC-4143 controllers have specific requirements for saving network settings.

**Solutions**:
- Use `BN` command instead of `SAVE` command
- Power cycle is REQUIRED after network changes
- Some read commands (`MG _IP`, `MG _SM`) may not work
- Empty responses from commands usually indicate success

### 2. Command Format Issues

**Issue**: Wrong command format being used.

**Solutions**:
- Use `IP=192.168.1.100` format (with equals sign)
- Use `SM=255.255.255.0` format (with equals sign)
- Use `GW=192.168.1.1` format (with equals sign)

### 3. Save Command Not Working

**Issue**: The `BN` command may not be working properly.

**Solutions**:
- Try multiple `BN` command formats: `BN`, `BN;`, `BN\r`, `BN\n`
- Check if controller responds to save commands
- Use the "TEST SAVE COMMANDS" button in the application

### 4. Timing Issues

**Issue**: Settings may need time to be processed.

**Solutions**:
- Wait 2-3 seconds after setting IP before saving
- Wait 2-3 seconds after `BN` command before verification
- Power cycle the controller after saving

## Diagnostic Steps

### Step 1: Test Save Commands

1. Connect to the controller
2. Click "TEST SAVE COMMANDS" button
3. Check which save commands work
4. Note any error responses

### Step 2: Test IP Setting

1. Use "SET IP (SIMPLE)" or "SET IP (ADVANCED)"
2. Check the debug information in the log
3. Look for successful IP setting confirmation
4. Check if `saved_to_flash` is True

### Step 3: Manual Verification

1. After setting IP, try reading it back:
   ```
   IP
   MG _IP
   ```
2. If `MG _IP` doesn't work, use `IP` command
3. Power cycle the controller
4. Check if IP persists after power cycle

### Step 4: Use Diagnostic Script

Run the `test_save_issue.py` script:
```bash
python test_save_issue.py
```

This script will:
- Test all save commands
- Try to set a test IP
- Provide detailed debug information
- Give specific recommendations

## Common Error Messages and Solutions

### "BN command failed"
- Try different `BN` command formats
- Check controller connection
- Ensure controller supports `BN` command

### "IP verification failed"
- DMC-4143 may not support `MG _IP` command
- Use `IP` command instead
- Check if IP was actually set

### "Settings not saved to flash"
- Try multiple `BN` command attempts
- Power cycle and check if settings persist
- Check controller firmware version

## Working Command Sequence

For DMC-4143, use this sequence:

```
IP=192.168.1.100
SM=255.255.255.0
GW=192.168.1.1
BN
```

Then power cycle the controller.

## Verification Steps

1. **Immediate verification**: Try `IP` command to read back IP
2. **Power cycle verification**: Power cycle and check if IP persists
3. **Network verification**: Try to connect to the new IP address

## Application Features

The enhanced application now includes:

1. **Improved save logic**: Better detection of successful saves
2. **TEST SAVE COMMANDS button**: Tests all save command formats
3. **Enhanced debug information**: Detailed logging of all steps
4. **Better error handling**: More specific error messages
5. **Power cycle reminders**: Always reminds to power cycle

## When to Contact Support

Contact Galil support if:
- No save commands work at all
- Controller doesn't respond to network commands
- Settings don't persist after power cycle
- Firmware version is very old

## Additional Notes

- DMC-4143 controllers may behave differently than other Galil models
- Some commands that work on other models may not work on DMC-4143
- Always power cycle after network changes
- Keep firmware updated if possible
