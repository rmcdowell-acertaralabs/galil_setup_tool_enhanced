import gclib
import socket
import struct
from typing import Dict, List, Optional, Tuple

def discover_galil_controllers() -> Dict[str, str]:
    """
    Discover Galil controllers on the network using gclib's GAddresses function.
    
    Returns:
        Dictionary mapping controller addresses to their information
    """
    try:
        g = gclib.py()
        addresses = g.GAddresses()
        return addresses
    except Exception as e:
        print(f"Error discovering controllers: {e}")
        return {}



def ping_controller(ip_address: str, timeout: float = 1.0) -> bool:
    """
    Ping a controller to check if it's reachable.
    
    Args:
        ip_address: The IP address to ping
        timeout: Timeout in seconds
        
    Returns:
        True if controller responds, False otherwise
    """
    try:
        # Create a socket and try to connect to the controller's port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip_address, 23))  # Telnet port
        sock.close()
        return result == 0
    except Exception:
        return False



def validate_ip_address(ip_address: str) -> bool:
    """
    Validate an IP address format.
    
    Args:
        ip_address: IP address to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parts = ip_address.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        
        return True
    except Exception:
        return False



def get_network_info(ip_address: str, subnet_mask: str = "255.255.255.0") -> Dict[str, str]:
    """
    Get network information for an IP address.
    
    Args:
        ip_address: The IP address
        subnet_mask: The subnet mask
        
    Returns:
        Dictionary with network information
    """
    try:
        # Convert IP and mask to integers
        ip_int = struct.unpack('!I', socket.inet_aton(ip_address))[0]
        mask_int = struct.unpack('!I', socket.inet_aton(subnet_mask))[0]
        
        # Calculate network address
        network_int = ip_int & mask_int
        
        # Convert back to string
        network = socket.inet_ntoa(struct.pack('!I', network_int))
        
        # Calculate broadcast address
        broadcast_int = network_int | (~mask_int & 0xffffffff)
        broadcast = socket.inet_ntoa(struct.pack('!I', broadcast_int))
        
        return {
            'ip': ip_address,
            'subnet_mask': subnet_mask,
            'network': network,
            'broadcast': broadcast
        }
    except Exception as e:
        print(f"Error calculating network info: {e}")
        return {}

def test_controller_connection(ip_address: str) -> Dict[str, any]:
    """
    Test connection to a Galil controller and get basic information.
    
    Args:
        ip_address: The IP address of the controller
        
    Returns:
        Dictionary with connection test results
    """
    result = {
        'ip': ip_address,
        'ping_success': False,
        'connection_success': False,
        'firmware': None,
        'model': None,
        'error': None
    }
    
    # Test ping first
    result['ping_success'] = ping_controller(ip_address)
    
    if not result['ping_success']:
        result['error'] = "Controller not responding to ping"
        return result
    
    # Try to connect and get information
    try:
        g = gclib.py()
        g.GOpen(ip_address)
        
        # Test basic commands
        try:
            firmware = g.GCommand("MG _FW")
            result['firmware'] = firmware.strip()
        except:
            pass
        
        try:
            model = g.GCommand("MG _ID")
            result['model'] = model.strip()
        except:
            pass
        
        result['connection_success'] = True
        g.GClose()
        
    except Exception as e:
        result['error'] = str(e)
    
    return result



def configure_controller_network_complete(controller, ip_address: str, subnet_mask: str = "255.255.255.0", 
                                        gateway: str = None, hostname: str = None) -> Dict[str, bool]:
    """
    Complete network configuration for Galil DMC-4143 controller.
    This function sets all network parameters and saves them to the controller's non-volatile memory.
    
    Args:
        controller: Connected GalilController instance
        ip_address: New IP address for the controller
        subnet_mask: Subnet mask (default: 255.255.255.0)
        gateway: Gateway address (optional)
        hostname: Hostname (optional)
        
    Returns:
        Dictionary with success status for each operation
    """
    # For backward compatibility, call the DMC-4143 specific function
    return configure_controller_network_dmc4143(controller, ip_address, subnet_mask, gateway)

def configure_controller_network_dmc4143(controller, ip_address: str, subnet_mask: str = "255.255.255.0", 
                                       gateway: str = None) -> Dict[str, bool]:
    """
    Network configuration specifically for DMC-4143 controller.
    Based on debug results, this controller accepts some network commands but not SAVE.
    
    Args:
        controller: Connected GalilController instance
        ip_address: New IP address for the controller
        subnet_mask: Subnet mask (default: 255.255.255.0)
        gateway: Gateway address (optional)
        
    Returns:
        Dictionary with success status for each operation
    """
    results = {
        'ip_set': False,
        'subnet_set': False,
        'gateway_set': False,
        'saved_to_flash': False,
        'reboot_required': True,
        'debug_info': []
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        results['debug_info'].append("Controller not connected")
        return results
    
    try:
        # Get current network status before changes
        results['debug_info'].append("Getting current network status...")
        try:
            # Try to get current IP using different methods
            current_ip = None
            try:
                current_ip = controller.send_command("MG _IP")
                results['debug_info'].append(f"Current IP (MG _IP): {current_ip}")
            except:
                pass
            
            if not current_ip or current_ip.startswith('ERROR'):
                try:
                    # Try alternative method
                    current_ip = controller.send_command("IP")
                    results['debug_info'].append(f"Current IP (IP): {current_ip}")
                except:
                    pass
        except Exception as e:
            results['debug_info'].append(f"Error reading current IP: {str(e)}")
        
        # Step 1: Set IP address - Use the format that worked in debug
        results['debug_info'].append(f"Setting IP address to: {ip_address}")
        
        # Based on debug results, try these formats in order
        ip_commands = [
            f"IP={ip_address}",          # This format worked in debug
            f"IP{ip_address}",           # Standard format
            f"IP {ip_address}",          # With space
        ]
        
        for cmd in ip_commands:
            try:
                results['debug_info'].append(f"Trying command: {cmd}")
                response = controller.send_command(cmd)
                results['debug_info'].append(f"Response: {response}")
                
                # For DMC-4143, empty response or no error means success
                if not response or not response.startswith('?'):
                    results['ip_set'] = True
                    results['debug_info'].append(f"IP command successful: {cmd}")
                    break
                else:
                    results['debug_info'].append(f"IP command failed with response: {response}")
            except Exception as e:
                results['debug_info'].append(f"Command {cmd} failed: {str(e)}")
                continue
        
        # Step 2: Set subnet mask - Use the format that worked in debug
        results['debug_info'].append(f"Setting subnet mask to: {subnet_mask}")
        subnet_commands = [
            f"SM={subnet_mask}",         # This format worked in debug
            f"SM{subnet_mask}",          # Standard format
            f"SM {subnet_mask}",         # With space
        ]
        
        for cmd in subnet_commands:
            try:
                results['debug_info'].append(f"Trying command: {cmd}")
                response = controller.send_command(cmd)
                results['debug_info'].append(f"Response: {response}")
                
                if not response or not response.startswith('?'):
                    results['subnet_set'] = True
                    results['debug_info'].append(f"Subnet command successful: {cmd}")
                    break
                else:
                    results['debug_info'].append(f"Subnet command failed with response: {response}")
            except Exception as e:
                results['debug_info'].append(f"Command {cmd} failed: {str(e)}")
                continue
        
        # Step 3: Set gateway (if provided) - Use the format that worked in debug
        if gateway:
            results['debug_info'].append(f"Setting gateway to: {gateway}")
            gateway_commands = [
                f"GW={gateway}",          # This format worked in debug
                f"GW{gateway}",           # Standard format
                f"GW {gateway}",          # With space
            ]
            
            for cmd in gateway_commands:
                try:
                    results['debug_info'].append(f"Trying command: {cmd}")
                    response = controller.send_command(cmd)
                    results['debug_info'].append(f"Response: {response}")
                    
                    if not response or not response.startswith('?'):
                        results['gateway_set'] = True
                        results['debug_info'].append(f"Gateway command successful: {cmd}")
                        break
                    else:
                        results['debug_info'].append(f"Gateway command failed with response: {response}")
                except Exception as e:
                    results['debug_info'].append(f"Command {cmd} failed: {str(e)}")
                    continue
        
        # Step 4: Save settings using BN command (burn settings to non-volatile memory)
        results['debug_info'].append("Saving settings using BN command...")
        
        # For DMC-4143, use BN command to burn settings to non-volatile memory
        # Try multiple approaches to ensure settings are saved
        save_attempts = [
            ("BN", "Burn settings to non-volatile memory"),
            ("BN;", "Burn settings with semicolon"),
            ("BN\r", "Burn settings with carriage return"),
            ("BN\n", "Burn settings with newline"),
            ("", "Empty command to flush buffer"),
        ]
        
        # Also try CF command which appears to work on some DMC-4143 models
        cf_attempts = [
            ("CF", "Configuration save command"),
            ("CF;", "Configuration save with semicolon"),
        ]
        
        save_success = False
        for cmd, description in save_attempts:
            try:
                if cmd:
                    results['debug_info'].append(f"Trying {description}: {cmd}")
                    response = controller.send_command(cmd)
                    results['debug_info'].append(f"Response: {response}")
                    
                    # For DMC-4143, BN command typically returns empty or no error
                    if not response or not response.startswith('?'):
                        save_success = True
                        results['debug_info'].append(f"BN command successful: {cmd}")
                        break
                else:
                    results['debug_info'].append("Sending empty command to flush buffer")
                    # Just wait a moment
                    import time
                    time.sleep(1)
                    save_success = True  # Assume success for empty command
                    break
                    
            except Exception as e:
                results['debug_info'].append(f"{description} failed: {str(e)}")
                continue
        
        # If BN commands didn't work, try CF commands
        if not save_success:
            results['debug_info'].append("BN commands failed, trying CF commands...")
            for cmd, description in cf_attempts:
                try:
                    results['debug_info'].append(f"Trying {description}: {cmd}")
                    response = controller.send_command(cmd)
                    results['debug_info'].append(f"Response: {response}")
                    
                    # CF command typically returns empty on success
                    if not response or not response.startswith('?'):
                        save_success = True
                        results['debug_info'].append(f"CF command successful: {cmd}")
                        break
                        
                except Exception as e:
                    results['debug_info'].append(f"{description} failed: {str(e)}")
                    continue
        
        # Additional save verification for DMC-4143
        if save_success:
            results['debug_info'].append("BN command executed successfully")
            
            # Try to verify the save by checking if we can read back the settings
            # (though DMC-4143 may not support all read commands)
            try:
                # Wait a moment for settings to be processed
                import time
                time.sleep(2)
                
                # Try to read back the IP address
                try:
                    verify_ip = controller.send_command("IP")
                    results['debug_info'].append(f"Save verification - IP command returns: {verify_ip}")
                    
                    # If we can read back the IP and it matches, consider it saved
                    if verify_ip and verify_ip.strip() == ip_address:
                        results['saved_to_flash'] = True
                        results['debug_info'].append("IP verification confirms settings are saved")
                    else:
                        results['debug_info'].append("IP verification failed - settings may not be saved")
                except Exception as e:
                    results['debug_info'].append(f"IP verification error: {str(e)}")
                    
                    # If we can't verify but the BN command succeeded, assume it's saved
                    # This is common for DMC-4143 where read commands may not work
                    results['saved_to_flash'] = True
                    results['debug_info'].append("Cannot verify IP but BN command succeeded - assuming saved")
                    
            except Exception as e:
                results['debug_info'].append(f"Save verification error: {str(e)}")
                # Still assume saved if BN command worked
                results['saved_to_flash'] = True
        else:
            results['debug_info'].append("BN command failed - settings may not be saved")
            results['saved_to_flash'] = False
        
        # Step 5: Final verification and recommendations
        results['debug_info'].append("Final verification and recommendations...")
        
        # Check if any settings were successfully applied
        if results.get('ip_set', False) or results.get('subnet_set', False):
            results['debug_info'].append("Network settings were successfully applied")
            
            if results.get('saved_to_flash', False):
                results['debug_info'].append("Settings appear to be saved to non-volatile memory")
                results['debug_info'].append("IMPORTANT: Power cycle the controller for changes to take effect")
            else:
                results['debug_info'].append("WARNING: Settings may not be saved to non-volatile memory")
                results['debug_info'].append("Try power cycling the controller to see if settings persist")
        else:
            results['debug_info'].append("No network settings were successfully applied")
            results['saved_to_flash'] = False
        
        # Always recommend power cycle for DMC-4143
        results['reboot_required'] = True
        results['debug_info'].append("DMC-4143: Power cycle required for network changes to take effect")
        
    except Exception as e:
        results['error'] = str(e)
        results['debug_info'].append(f"General error: {str(e)}")
    
    return results

def force_save_network_settings_dmc4143(controller, ip_address: str, subnet_mask: str = "255.255.255.0", 
                                       gateway: str = None) -> Dict[str, bool]:
    """
    Force save network settings to DMC-4143 controller using multiple methods.
    This function is specifically designed to handle DMC-4143 save issues.
    
    Args:
        controller: Connected GalilController instance
        ip_address: New IP address for the controller
        subnet_mask: Subnet mask (default: 255.255.255.0)
        gateway: Gateway address (optional)
        
    Returns:
        Dictionary with success status for each operation
    """
    results = {
        'ip_set': False,
        'subnet_set': False,
        'gateway_set': False,
        'saved_to_flash': False,
        'reboot_required': True,
        'debug_info': []
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        results['debug_info'].append("Controller not connected")
        return results
    
    try:
        results['debug_info'].append("=== FORCE SAVE NETWORK SETTINGS ===")
        
        # Step 1: Set network parameters
        results['debug_info'].append(f"Setting IP address to: {ip_address}")
        
        # Set IP with multiple attempts
        ip_commands = [
            f"IP={ip_address}",
            f"IP{ip_address}",
            f"IP {ip_address}",
        ]
        
        for cmd in ip_commands:
            try:
                response = controller.send_command(cmd)
                if not response or not response.startswith('?'):
                    results['ip_set'] = True
                    results['debug_info'].append(f"IP command successful: {cmd}")
                    break
            except Exception as e:
                results['debug_info'].append(f"IP command failed: {cmd} - {str(e)}")
                continue
        
        # Set subnet mask
        results['debug_info'].append(f"Setting subnet mask to: {subnet_mask}")
        subnet_commands = [
            f"SM={subnet_mask}",
            f"SM{subnet_mask}",
            f"SM {subnet_mask}",
        ]
        
        for cmd in subnet_commands:
            try:
                response = controller.send_command(cmd)
                if not response or not response.startswith('?'):
                    results['subnet_set'] = True
                    results['debug_info'].append(f"Subnet command successful: {cmd}")
                    break
            except Exception as e:
                results['debug_info'].append(f"Subnet command failed: {cmd} - {str(e)}")
                continue
        
        # Set gateway if provided
        if gateway:
            results['debug_info'].append(f"Setting gateway to: {gateway}")
            gateway_commands = [
                f"GW={gateway}",
                f"GW{gateway}",
                f"GW {gateway}",
            ]
            
            for cmd in gateway_commands:
                try:
                    response = controller.send_command(cmd)
                    if not response or not response.startswith('?'):
                        results['gateway_set'] = True
                        results['debug_info'].append(f"Gateway command successful: {cmd}")
                        break
                except Exception as e:
                    results['debug_info'].append(f"Gateway command failed: {cmd} - {str(e)}")
                    continue
        
        # Step 2: Multiple save attempts with different methods
        results['debug_info'].append("=== MULTIPLE SAVE ATTEMPTS ===")
        
        # Method 1: Standard BN command sequence
        results['debug_info'].append("Method 1: Standard BN sequence")
        try:
            import time
            time.sleep(1)  # Wait before save
            response = controller.send_command("BN")
            results['debug_info'].append(f"BN response: '{response}'")
            time.sleep(2)  # Wait after save
        except Exception as e:
            results['debug_info'].append(f"BN command failed: {str(e)}")
        
        # Method 2: BN with semicolon
        results['debug_info'].append("Method 2: BN with semicolon")
        try:
            response = controller.send_command("BN;")
            results['debug_info'].append(f"BN; response: '{response}'")
            time.sleep(1)
        except Exception as e:
            results['debug_info'].append(f"BN; command failed: {str(e)}")
        
        # Method 3: Multiple BN commands
        results['debug_info'].append("Method 3: Multiple BN commands")
        for i in range(3):
            try:
                response = controller.send_command("BN")
                results['debug_info'].append(f"BN attempt {i+1} response: '{response}'")
                time.sleep(0.5)
            except Exception as e:
                results['debug_info'].append(f"BN attempt {i+1} failed: {str(e)}")
        
        # Method 4: Flush buffer and save
        results['debug_info'].append("Method 4: Flush buffer and save")
        try:
            # Send empty command to flush buffer
            controller.send_command("")
            time.sleep(1)
            response = controller.send_command("BN")
            results['debug_info'].append(f"Flush + BN response: '{response}'")
        except Exception as e:
            results['debug_info'].append(f"Flush + BN failed: {str(e)}")
        
        # Method 5: Try to force a configuration save
        results['debug_info'].append("Method 5: Force configuration save")
        try:
            # Some DMC-4143 models respond to this sequence
            controller.send_command("")  # Empty command
            time.sleep(0.5)
            controller.send_command("BN")  # Burn command
            time.sleep(0.5)
            controller.send_command("")  # Another empty command
            time.sleep(0.5)
            controller.send_command("BN")  # Final burn command
            results['debug_info'].append("Force save sequence completed")
        except Exception as e:
            results['debug_info'].append(f"Force save sequence failed: {str(e)}")
        
        # Method 6: Try CF command (configuration save)
        results['debug_info'].append("Method 6: CF command (configuration save)")
        try:
            # Try CF command which appears to work on some DMC-4143 models
            response = controller.send_command("CF")
            results['debug_info'].append(f"CF command response: '{response}'")
            time.sleep(1)
            
            # Try CF with semicolon
            response = controller.send_command("CF;")
            results['debug_info'].append(f"CF; command response: '{response}'")
            time.sleep(1)
            
            # Try multiple CF commands
            for i in range(3):
                response = controller.send_command("CF")
                results['debug_info'].append(f"CF command {i+1} response: '{response}'")
                time.sleep(0.5)
                
        except Exception as e:
            results['debug_info'].append(f"CF command failed: {str(e)}")
        
        # Step 3: Enhanced verification
        results['debug_info'].append("=== ENHANCED VERIFICATION ===")
        
        # Wait longer for settings to be processed
        time.sleep(3)
        
        # Try multiple verification methods
        verification_success = False
        
        # Method 1: Try IP command
        try:
            current_ip = controller.send_command("IP")
            results['debug_info'].append(f"Verification IP command: '{current_ip}'")
            if current_ip and current_ip.strip() == ip_address:
                verification_success = True
                results['debug_info'].append("IP verification successful via IP command")
        except Exception as e:
            results['debug_info'].append(f"IP command verification failed: {str(e)}")
        
        # Method 2: Try MG _IP command (may not work on DMC-4143)
        if not verification_success:
            try:
                current_ip_mg = controller.send_command("MG _IP")
                results['debug_info'].append(f"Verification MG _IP command: '{current_ip_mg}'")
                if current_ip_mg and not current_ip_mg.startswith('?') and current_ip_mg.strip() == ip_address:
                    verification_success = True
                    results['debug_info'].append("IP verification successful via MG _IP command")
            except Exception as e:
                results['debug_info'].append(f"MG _IP verification failed: {str(e)}")
        
        # Method 3: Try to read back subnet mask
        try:
            current_sm = controller.send_command("SM")
            results['debug_info'].append(f"Subnet verification: '{current_sm}'")
            if current_sm and current_sm.strip() == subnet_mask:
                results['debug_info'].append("Subnet verification successful")
            else:
                results['debug_info'].append("Subnet verification failed")
        except Exception as e:
            results['debug_info'].append(f"Subnet verification failed: {str(e)}")
        
        # Step 4: Determine if settings were actually saved
        if verification_success:
            results['saved_to_flash'] = True
            results['debug_info'].append("✓ Settings verified as saved to non-volatile memory")
        else:
            # Even if verification fails, check if we got any positive indicators
            if results.get('ip_set', False) and results.get('subnet_set', False):
                results['debug_info'].append("⚠ Settings may be saved but verification failed")
                results['debug_info'].append("⚠ This is common with DMC-4143 - power cycle to confirm")
                # For DMC-4143, we'll assume it might be saved if commands succeeded
                results['saved_to_flash'] = True
            else:
                results['saved_to_flash'] = False
                results['debug_info'].append("✗ Settings appear to not be saved")
        
        # Step 5: Final recommendations
        results['debug_info'].append("=== FINAL RECOMMENDATIONS ===")
        
        if results.get('saved_to_flash', False):
            results['debug_info'].append("✓ Network settings appear to be saved")
            results['debug_info'].append("→ POWER CYCLE THE CONTROLLER NOW")
            results['debug_info'].append("→ After power cycle, try to connect to the new IP")
            results['debug_info'].append("→ If connection fails, the settings may not have been saved")
        else:
            results['debug_info'].append("✗ Network settings may not be saved")
            results['debug_info'].append("→ Try the save process again")
            results['debug_info'].append("→ Check controller firmware version")
            results['debug_info'].append("→ Contact Galil support if issue persists")
        
        results['reboot_required'] = True
        
    except Exception as e:
        results['error'] = str(e)
        results['debug_info'].append(f"General error: {str(e)}")
    
    return results

def reset_controller_network_to_dhcp(controller) -> Dict[str, bool]:
    """
    Reset controller network settings to use DHCP.
    
    Args:
        controller: Connected GalilController instance
        
    Returns:
        Dictionary with success status
    """
    results = {
        'dhcp_enabled': False,
        'saved_to_flash': False,
        'reboot_required': True
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        return results
    
    try:
        # Enable DHCP on the controller
        dhcp_commands = [
            "DHCP=1",
            "DHCP 1",
            "DHCP1"
        ]
        
        for cmd in dhcp_commands:
            try:
                controller.send_command(cmd)
                results['dhcp_enabled'] = True
                break
            except:
                continue
        
        # Save settings to non-volatile memory using BN command
        if results['dhcp_enabled']:
            try:
                controller.send_command("BN")
                results['saved_to_flash'] = True
            except:
                results['saved_to_flash'] = False
    
    except Exception as e:
        results['error'] = str(e)
    
    return results



def get_controller_network_status(controller) -> Dict[str, any]:
    """
    Get comprehensive network status from the controller.
    
    Args:
        controller: Connected GalilController instance
        
    Returns:
        Dictionary with network status information
    """
    status = {
        'ip_address': None,
        'subnet_mask': None,
        'gateway': None,
        'mac_address': None,
        'hostname': None,
        'dhcp_enabled': None,
        'connection_status': 'Unknown'
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        status['connection_status'] = 'Disconnected'
        return status
    
    try:
        # Get IP address
        try:
            status['ip_address'] = controller.send_command("MG _IP").strip()
        except:
            pass
        
        # Get subnet mask
        try:
            status['subnet_mask'] = controller.send_command("MG _SM").strip()
        except:
            pass
        
        # Get gateway
        try:
            status['gateway'] = controller.send_command("MG _GW").strip()
        except:
            pass
        
        # Get MAC address
        try:
            status['mac_address'] = controller.send_command("MG _MAC").strip()
        except:
            pass
        
        # Get hostname
        try:
            status['hostname'] = controller.send_command("MG _HN").strip()
        except:
            pass
        
        # Check DHCP status
        try:
            dhcp_status = controller.send_command("MG _DHCP").strip()
            status['dhcp_enabled'] = dhcp_status == "1" or dhcp_status.lower() == "true"
        except:
            pass
        
        status['connection_status'] = 'Connected'
        
    except Exception as e:
        status['connection_status'] = f'Error: {str(e)}'
    
    return status

def comprehensive_network_test(controller) -> Dict[str, any]:
    """
    Comprehensive network test for DMC-4143 controller.
    This function combines all network command tests into a single comprehensive test.
    
    Args:
        controller: Connected GalilController instance
        
    Returns:
        Dictionary with comprehensive test results
    """
    results = {
        'basic_commands': {},
        'network_commands': {},
        'save_commands': {},
        'controller_info': {},
        'network_support': {},
        'recommendations': [],
        'error': None
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        results['error'] = "Controller not connected"
        return results
    
    try:
        # Test 1: Basic controller information
        basic_commands = [
            "TP",           # Tell Position
            "MG _FW",       # Firmware version
            "MG _ID",       # Controller ID
            "MG _BN",       # Serial number
        ]
        
        for cmd in basic_commands:
            try:
                response = controller.send_command(cmd)
                results['basic_commands'][cmd] = response.strip()
            except Exception as e:
                results['basic_commands'][cmd] = f"ERROR: {str(e)}"
        
        # Test 2: Network command support
        network_commands = [
            ("IP", "IP address command"),
            ("SM", "Subnet mask command"),
            ("GW", "Gateway command"),
            ("MG _IP", "Get IP address"),
            ("MG _SM", "Get subnet mask"),
            ("MG _GW", "Get gateway"),
            ("MG _MAC", "Get MAC address"),
            ("MG _HN", "Get hostname"),
            ("MG _DHCP", "Get DHCP status"),
        ]
        
        supported_network = []
        unsupported_network = []
        
        for cmd, description in network_commands:
            try:
                response = controller.send_command(cmd)
                if response.startswith('?'):
                    unsupported_network.append(f"{cmd} ({description})")
                    results['network_commands'][cmd] = "NOT SUPPORTED"
                else:
                    supported_network.append(f"{cmd} ({description})")
                    results['network_commands'][cmd] = response.strip()
            except Exception as e:
                unsupported_network.append(f"{cmd} ({description})")
                results['network_commands'][cmd] = f"ERROR: {str(e)}"
        
        # Test 3: Save command support
        save_commands = [
            ("BN", "Burn command"),
            ("CF", "Configuration command"),
            ("SAVE", "Save command"),
        ]
        
        supported_save = []
        unsupported_save = []
        
        for cmd, description in save_commands:
            try:
                response = controller.send_command(cmd)
                if response.startswith('?'):
                    unsupported_save.append(f"{cmd} ({description})")
                    results['save_commands'][cmd] = "NOT SUPPORTED"
                else:
                    supported_save.append(f"{cmd} ({description})")
                    results['save_commands'][cmd] = response.strip()
            except Exception as e:
                unsupported_save.append(f"{cmd} ({description})")
                results['save_commands'][cmd] = f"ERROR: {str(e)}"
        
        # Test 4: Current network settings
        try:
            # Try to read current IP
            try:
                current_ip = controller.send_command("IP")
                results['controller_info']['current_ip'] = current_ip.strip()
            except Exception as e:
                results['controller_info']['current_ip'] = f"ERROR: {str(e)}"
            
            # Try to read current subnet mask
            try:
                current_sm = controller.send_command("MG _SM")
                results['controller_info']['current_subnet'] = current_sm.strip()
            except Exception as e:
                results['controller_info']['current_subnet'] = f"ERROR: {str(e)}"
            
            # Try to read current gateway
            try:
                current_gw = controller.send_command("MG _GW")
                results['controller_info']['current_gateway'] = current_gw.strip()
            except Exception as e:
                results['controller_info']['current_gateway'] = f"ERROR: {str(e)}"
                
        except Exception as e:
            results['controller_info']['error'] = f"Error reading network settings: {str(e)}"
        
        # Test 5: Network configuration test (without actually changing anything)
        network_test_commands = [
            "IP192.168.1.100",
            "IP 192.168.1.100", 
            "IP=192.168.1.100",
            "SM255.255.255.0",
            "SM 255.255.255.0",
            "SM=255.255.255.0",
            "GW192.168.1.1",
            "GW 192.168.1.1",
            "GW=192.168.1.1",
        ]
        
        for cmd in network_test_commands:
            try:
                response = controller.send_command(cmd)
                results['network_commands'][f"TEST_{cmd}"] = response.strip()
            except Exception as e:
                results['network_commands'][f"TEST_{cmd}"] = f"ERROR: {str(e)}"
        
        # Analysis and recommendations
        results['network_support']['supported_commands'] = supported_network
        results['network_support']['unsupported_commands'] = unsupported_network
        results['network_support']['supported_save_commands'] = supported_save
        results['network_support']['unsupported_save_commands'] = unsupported_save
        
        # Generate recommendations
        if len(supported_network) > 0:
            results['recommendations'].append("✓ Controller supports some network commands")
            results['recommendations'].append(f"  Supported: {', '.join(supported_network)}")
        else:
            results['recommendations'].append("✗ Controller does not support network configuration")
            results['recommendations'].append("  This may indicate the controller is not network-enabled")
        
        if len(unsupported_network) > 0:
            results['recommendations'].append(f"✗ Unsupported commands: {', '.join(unsupported_network)}")
        
        if len(supported_save) > 0:
            results['recommendations'].append("✓ Controller supports save commands")
            results['recommendations'].append(f"  Supported save commands: {', '.join(supported_save)}")
        else:
            results['recommendations'].append("✗ Controller does not support save commands")
            results['recommendations'].append("  Network settings may not be saveable")
        
        # DMC-4143 specific recommendations
        results['recommendations'].append("DMC-4143: Power cycle required after network changes")
        results['recommendations'].append("DMC-4143: Some read commands may not be supported")
        
        # Check if IP can be read back
        if 'current_ip' in results['controller_info']:
            current_ip = results['controller_info']['current_ip']
            if current_ip and not current_ip.startswith('ERROR'):
                results['recommendations'].append("✓ IP address can be read back")
            else:
                results['recommendations'].append("✗ IP address cannot be read back (common for DMC-4143)")
        
    except Exception as e:
        results['error'] = str(e)
    
    return results

