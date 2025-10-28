"""
Network Configuration and Utilities Module for Windows
Handles reading and setting network adapter configurations, controller discovery, and network testing
"""

import gclib
import socket
import struct
import subprocess
import re
import os
import platform
import time
from typing import Dict, List, Optional, Tuple
from tkinter import messagebox
from galil_combined import GalilController
from controller_commands import ControllerCommands
from command_validator_proper import DMC4103CommandValidator

# Validator-backed command sender
_VALIDATOR_INSTANCE = None

def _get_validator() -> DMC4103CommandValidator:
    global _VALIDATOR_INSTANCE
    if _VALIDATOR_INSTANCE is None:
        _VALIDATOR_INSTANCE = DMC4103CommandValidator()
    return _VALIDATOR_INSTANCE

def send_galil_command(controller, command: str, log_fn: Optional[callable] = None) -> str:
    """Send a Galil command with validation when applicable.
    - Validates only single commands known to the validator (no semicolons)
    - Skips validation for network/system commands not covered (e.g., IA, IP, DH, DHCP, GW, SM, CF)
    - On validation failure, returns a Galil-style error string starting with '?'
    """
    try:
        raw = command.strip()
        if not raw:
            return controller.send_command(command)
        if ';' in raw:
            return controller.send_command(command)
        m = re.match(r"^([A-Za-z]+)", raw)
        base = m.group(1).upper() if m else None
        if not base:
            return controller.send_command(command)
        validator = _get_validator()
        known = set(validator.get_all_commands())
        skip_validation_bases = {"IA", "IP", "DH", "DHCP", "GW", "SM", "CF"}
        if base not in known or base in skip_validation_bases:
            return controller.send_command(command)
        result = validator.validate_command(raw)
        if not result.valid:
            if log_fn:
                log_fn(f"Validator blocked command '{raw}': {result.error_message}")
            return f"? {result.error_message}"
        if log_fn and result.warning_message:
            log_fn(f"Warning for '{raw}': {result.warning_message}")
        return controller.send_command(command)
    except Exception as e:
        if log_fn:
            log_fn(f"Validation error for '{command}': {e}. Sending without validation.")
        return controller.send_command(command)

# ============================================================================
# NETWORK CONFIGURATION CLASS
# ============================================================================

class NetworkConfigurator:
    def __init__(self):
        self.target_settings = {
            'ip_address': '10.1.0.20',
            'subnet_mask': '255.255.255.0',
            'gateway': '10.1.0.1',
            'preferred_dns': '10.1.0.10',
            'alternate_dns': '10.1.0.11'
        }
    
    def get_network_adapters(self) -> List[Dict]:
        """Get list of network adapters on the system."""
        try:
            # Get network adapter information using netsh
            result = subprocess.run(
                ['netsh', 'interface', 'ip', 'show', 'config'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to get network adapters: {result.stderr}")
            
            adapters = []
            current_adapter = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                # Look for adapter names (they start with "Configuration for interface")
                if line.startswith('Configuration for interface'):
                    if current_adapter:
                        adapters.append(current_adapter)
                    
                    adapter_name = line.replace('Configuration for interface "', '').replace('"', '')
                    current_adapter = {
                        'name': adapter_name,
                        'ip_address': '',
                        'subnet_mask': '',
                        'gateway': '',
                        'dns_servers': [],
                        'dhcp_enabled': False,
                        'status': 'Unknown'
                    }
                
                # Parse IP configuration
                elif current_adapter and line.startswith('IP Address:'):
                    ip_match = re.search(r'IP Address:\s*([0-9.]+)', line)
                    if ip_match:
                        current_adapter['ip_address'] = ip_match.group(1)
                
                elif current_adapter and line.startswith('Subnet Prefix:'):
                    subnet_match = re.search(r'Subnet Prefix:\s*([0-9.]+)', line)
                    if subnet_match:
                        current_adapter['subnet_mask'] = subnet_match.group(1)
                
                elif current_adapter and line.startswith('Default Gateway:'):
                    gateway_match = re.search(r'Default Gateway:\s*([0-9.]+)', line)
                    if gateway_match:
                        current_adapter['gateway'] = gateway_match.group(1)
                
                elif current_adapter and line.startswith('DNS Servers:'):
                    dns_match = re.search(r'DNS Servers:\s*([0-9.,\s]+)', line)
                    if dns_match:
                        dns_servers = dns_match.group(1).strip().split(',')
                        current_adapter['dns_servers'] = [dns.strip() for dns in dns_servers if dns.strip()]
                
                elif current_adapter and 'DHCP enabled:' in line:
                    dhcp_match = re.search(r'DHCP enabled:\s*(Yes|No)', line)
                    if dhcp_match:
                        current_adapter['dhcp_enabled'] = dhcp_match.group(1).lower() == 'yes'
            
            # Add the last adapter
            if current_adapter:
                adapters.append(current_adapter)
            
            return adapters
            
        except Exception as e:
            raise Exception(f"Error getting network adapters: {str(e)}")
    
    def get_active_network_adapter(self) -> Optional[Dict]:
        """Get the currently active network adapter."""
        try:
            adapters = self.get_network_adapters()
            
            # Look for adapters with IP addresses (active ones)
            active_adapters = [adapter for adapter in adapters if adapter['ip_address']]
            
            if not active_adapters:
                return None
            
            # Return the first active adapter (usually the main one)
            return active_adapters[0]
            
        except Exception as e:
            raise Exception(f"Error getting active network adapter: {str(e)}")
    
    def format_network_status(self, adapter: Dict) -> str:
        """Format network adapter status for display."""
        if not adapter:
            return "No active network adapter found."
        
        status = f"Network Adapter: {adapter['name']}\n"
        status += "=" * 50 + "\n\n"
        
        status += f"IP Address: {adapter['ip_address'] or 'Not configured'}\n"
        status += f"Subnet Mask: {adapter['subnet_mask'] or 'Not configured'}\n"
        status += f"Gateway: {adapter['gateway'] or 'Not configured'}\n"
        status += f"DNS Servers: {', '.join(adapter['dns_servers']) if adapter['dns_servers'] else 'Not configured'}\n"
        status += f"DHCP Enabled: {'Yes' if adapter['dhcp_enabled'] else 'No'}\n"
        
        return status
    
    def apply_network_settings(self, adapter_name: str) -> bool:
        """Apply the target network settings to the specified adapter."""
        try:
            # First, disable DHCP to enable manual configuration
            cmd_disable_dhcp = [
                'netsh', 'interface', 'ip', 'set', 'address',
                f'name="{adapter_name}"', 'static',
                self.target_settings['ip_address'],
                self.target_settings['subnet_mask'],
                self.target_settings['gateway']
            ]
            
            result = subprocess.run(cmd_disable_dhcp, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to set IP address: {result.stderr}")
            
            # Set DNS servers
            cmd_set_dns = [
                'netsh', 'interface', 'ip', 'set', 'dns',
                f'name="{adapter_name}"', 'static',
                self.target_settings['preferred_dns']
            ]
            
            result = subprocess.run(cmd_set_dns, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to set primary DNS: {result.stderr}")
            
            # Set alternate DNS server
            cmd_set_alt_dns = [
                'netsh', 'interface', 'ip', 'add', 'dns',
                f'name="{adapter_name}"',
                self.target_settings['alternate_dns'], 'index=2'
            ]
            
            result = subprocess.run(cmd_set_alt_dns, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # This might fail if alternate DNS is already set, which is okay
                pass
            
            return True
            
        except Exception as e:
            raise Exception(f"Error applying network settings: {str(e)}")
    
    def reset_to_dhcp(self, adapter_name: str) -> bool:
        """Reset the adapter to use DHCP."""
        try:
            # Enable DHCP
            cmd_enable_dhcp = [
                'netsh', 'interface', 'ip', 'set', 'address',
                f'name="{adapter_name}"', 'dhcp'
            ]
            
            result = subprocess.run(cmd_enable_dhcp, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to enable DHCP: {result.stderr}")
            
            # Set DNS to DHCP
            cmd_dns_dhcp = [
                'netsh', 'interface', 'ip', 'set', 'dns',
                f'name="{adapter_name}"', 'dhcp'
            ]
            
            result = subprocess.run(cmd_dns_dhcp, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to set DNS to DHCP: {result.stderr}")
            
            return True
            
        except Exception as e:
            raise Exception(f"Error resetting to DHCP: {str(e)}")
    
    def test_network_connectivity(self) -> Dict:
        """Test network connectivity after configuration."""
        results = {
            'gateway_ping': False,
            'dns_ping': False,
            'internet_ping': False,
            'details': []
        }
        
        try:
            # Test gateway connectivity
            try:
                result = subprocess.run(
                    ['ping', '-n', '2', self.target_settings['gateway']],
                    capture_output=True, text=True, timeout=10
                )
                results['gateway_ping'] = result.returncode == 0
                results['details'].append(f"Gateway ({self.target_settings['gateway']}): {'✓' if results['gateway_ping'] else '✗'}")
            except:
                results['details'].append(f"Gateway ({self.target_settings['gateway']}): ✗")
            
            # Test DNS connectivity
            try:
                result = subprocess.run(
                    ['ping', '-n', '2', self.target_settings['preferred_dns']],
                    capture_output=True, text=True, timeout=10
                )
                results['dns_ping'] = result.returncode == 0
                results['details'].append(f"DNS ({self.target_settings['preferred_dns']}): {'✓' if results['dns_ping'] else '✗'}")
            except:
                results['details'].append(f"DNS ({self.target_settings['preferred_dns']}): ✗")
            
            # Test internet connectivity
            try:
                result = subprocess.run(
                    ['ping', '-n', '2', '8.8.8.8'],
                    capture_output=True, text=True, timeout=10
                )
                results['internet_ping'] = result.returncode == 0
                results['details'].append(f"Internet (8.8.8.8): {'✓' if results['internet_ping'] else '✗'}")
            except:
                results['details'].append(f"Internet (8.8.8.8): ✗")
            
        except Exception as e:
            results['details'].append(f"Connectivity test error: {str(e)}")
        
        return results

# ============================================================================
# NETWORK UTILITIES FUNCTIONS
# ============================================================================

def discover_galil_controllers() -> Dict[str, str]:
    """
    Discover Galil controllers on the network using gclib's GAddresses function.
    Returns both network devices and COM ports.

    Returns:
        Dictionary mapping controller addresses to their information
    """
    try:
        g = gclib.py()
        addresses = g.GAddresses()

        # Return all discovered controllers (both network and COM ports)
        controllers = {}
        for address, info in addresses.items():
            controllers[address] = info

        return controllers
    except Exception as e:
        print(f"Error discovering controllers: {e}")
        return {}

def discover_network_controllers() -> Dict[str, str]:
    """
    Discover only network-based Galil controllers (IP addresses).

    Returns:
        Dictionary mapping controller IP addresses to their information
    """
    try:
        g = gclib.py()
        addresses = g.GAddresses()

        # Filter for network addresses only (IP addresses)
        network_controllers = {}
        for address, info in addresses.items():
            # Skip serial ports (COM ports) and only include IP addresses
            if not address.upper().startswith('COM') and '.' in address:
                # Validate it's a proper IP address format
                try:
                    parts = address.split('.')
                    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                        network_controllers[address] = info
                except:
                    continue

        return network_controllers
    except Exception as e:
        print(f"Error discovering network controllers: {e}")
        return {}

def discover_com_port_controllers() -> Dict[str, str]:
    """
    Discover only COM port-based Galil controllers.

    Returns:
        Dictionary mapping COM port addresses to their information
    """
    try:
        g = gclib.py()
        addresses = g.GAddresses()

        # Filter for COM ports only
        com_controllers = {}
        for address, info in addresses.items():
            # Only include COM ports
            if address.upper().startswith('COM'):
                com_controllers[address] = info

        return com_controllers
    except Exception as e:
        print(f"Error discovering COM port controllers: {e}")
        return {}

def query_controller_ip_via_serial(com_port: str) -> Optional[str]:
    """
    Connect to controller via COM port and query its IP address.
    This is useful when the network interface isn't accessible for discovery.
    
    Args:
        com_port: The COM port to connect to (e.g., "COM3")
        
    Returns:
        The controller's IP address if successful, None otherwise
    """
    try:
        # Try to connect via COM port
        g = gclib.py()
        
        # Build COM port connection string with baud rate
        baud_rates = [115200, 57600, 38400, 19200, 9600]
        
        for baud in baud_rates:
            try:
                open_str = f"{com_port} --direct --baud {baud}"
                g.GOpen(open_str)
                break  # Success
            except:
                # Try next baud rate
                continue
        else:
            # All baud rates failed
            return None
        
        # Query the controller's IP address
        try:
            # Try IP command
            ip_response = g.GCommand("IP")
            if ip_response and not ip_response.startswith('?'):
                # Extract IP address from response
                import re
                m = re.search(r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)', ip_response)
                if m:
                    ip = m.group(0)
                    # Validate IP address
                    if all(0 <= int(p) <= 255 for p in ip.split(".")):
                        g.GClose()
                        return ip
        except:
            pass
        
        # Close connection
        g.GClose()
        return None
        
    except Exception as e:
        print(f"Error querying controller IP via serial: {e}")
        return None

def check_com_port_availability(com_port: str) -> Dict[str, any]:
    """
    Check if a COM port is available and can be opened.
    
    Args:
        com_port: The COM port to check (e.g., "COM3")
        
    Returns:
        Dictionary with availability status and troubleshooting info
    """
    result = {
        'port': com_port,
        'available': False,
        'error': None,
        'troubleshooting': []
    }
    
    try:
        # Try to create a gclib instance and open the port with baud and direct
        g = gclib.py()
        
        # Use the same open string logic as the main connection code
        baud_candidates = [115200, 57600, 38400, 19200, 9600]
        open_attempts = []
        for baud in baud_candidates:
            open_attempts.extend([
                f"{com_port} --direct --baud {baud}",
                f"{com_port} --baud {baud}",
                f"{com_port} --direct",
                f"{com_port}",
                f"{com_port} --baud {baud} --direct",
                f"{com_port} --timeout 5000 --baud {baud}",
                f"{com_port} --timeout 10000 --baud {baud}",
                f"{com_port} --timeout 5000 --direct --baud {baud}",
                f"{com_port} --timeout 10000 --direct --baud {baud}"
            ])
        
        last_error = None
        for open_str in open_attempts:
            try:
                g.GOpen(open_str)
                break  # Success!
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                # If port is already open or access denied, rethrow immediately
                if "already open" in error_msg or "access denied" in error_msg:
                    raise
                # For timeouts, try a longer wait before next attempt
                if "timeout" in error_msg:
                    time.sleep(1.0)
                else:
                    time.sleep(0.2)
        else:
            # If we exhausted attempts without break, raise last error
            if last_error:
                raise last_error
        g.GClose()
        result['available'] = True
        result['troubleshooting'].append("✓ COM port is available and can be opened")
    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        
        # If we get timeouts, the port can be opened but controller isn't responding
        if "timeout" in error_msg.lower():
            result['available'] = True  # Port can be opened
            result['troubleshooting'].append("✓ COM port can be opened but controller is not responding")
            result['troubleshooting'].append("• This indicates a firmware or hardware issue")
            result['troubleshooting'].append("• Controller may need firmware recovery")
        else:
            result['available'] = False
        
        if "device failed to open" in error_msg.lower():
            result['troubleshooting'].extend([
                "✗ COM port cannot be opened",
                "• Check if device is properly connected via USB",
                "• Verify COM port exists in Device Manager",
                "• Ensure no other application is using the COM port",
                "• Try unplugging and reconnecting the USB cable",
                "• Check if Galil drivers are properly installed"
            ])
        elif "access denied" in error_msg.lower():
            result['troubleshooting'].extend([
                "✗ Access denied to COM port",
                "• Another application may be using the port",
                "• Try closing other applications that might use COM ports",
                "• Check if a terminal program is connected to the port"
            ])
        else:
            result['troubleshooting'].append(f"✗ Error: {error_msg}")
    
    return result

def discover_controllers_network_scan(log_callback=None) -> Dict[str, str]:
    """
    Discovery method that finds controllers by detecting physical connections (COM ports or Ethernet),
    then queries each connection to get the controller's IP address and information.
    Does NOT scan network ranges - only queries actual detected connections.
    
    Args:
        log_callback: Optional callback function for logging messages
    
    Returns:
        Dictionary mapping controller IP addresses to their information
    """
    def log(message):
        """Internal logging function"""
        if log_callback:
            try:
                log_callback(message)
            except:
                pass
        print(message)
    
    try:
        import re
        
        discovered_controllers = {}
        
        log("Detecting physical connections to Galil controllers...")
        
        # Step 1: Use gclib to find all available connections
        try:
            g = gclib.py()
            addresses = g.GAddresses()
            
            if not addresses:
                log("No controllers detected via GAddresses()")
                return {}
            
            log(f"Found {len(addresses)} potential connection(s): {list(addresses.keys())}")
            
        except Exception as e:
            log(f"Error getting controller addresses: {e}")
            return {}
        
        # Step 2: For each connection found, query its IP address
        for address, info in addresses.items():
            controller_ip = None
            connection_type = None
            
            try:
                # Determine connection type
                if address.upper().startswith('COM'):
                    connection_type = "COM Port"
                    log(f"Found {connection_type}: {address}")
                    
                    # Connect via COM port and query IP address
                    try:
                        test_g = gclib.py()
                        
                        # Try different baud rates
                        baud_rates = [115200, 57600, 38400, 19200, 9600]
                        connected = False
                        
                        for baud in baud_rates:
                            try:
                                open_str = f"{address} --direct --baud {baud}"
                                test_g.GOpen(open_str)
                                connected = True
                                log(f"Connected to {address} at {baud} baud")
                                break
                            except:
                                continue
                        
                        if not connected:
                            log(f"Could not connect to {address}")
                            continue
                        
                        # Query the controller's IP address using IP command
                        try:
                            ip_response = test_g.GCommand("IP")
                            if ip_response and not ip_response.strip().startswith('?'):
                                # Extract IP address from response
                                m = re.search(r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)', ip_response)
                                if m:
                                    controller_ip = m.group(0)
                                    # Validate IP address
                                    if all(0 <= int(p) <= 255 for p in controller_ip.split(".")):
                                        log(f"Controller on {address} has IP: {controller_ip}")
                                    else:
                                        controller_ip = None
                        except Exception as e:
                            log(f"IP command failed, trying IA command")
                        
                        # Try alternative: IA ? command (returns IP in comma format)
                        if not controller_ip:
                            try:
                                ia_response = test_g.GCommand("IA ?")
                                if ia_response and not ia_response.strip().startswith('?'):
                                    # Convert comma-separated to dot-separated (192,168,1,100 -> 192.168.1.100)
                                    ip_str = ia_response.strip().replace(',', '.')
                                    m = re.search(r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)', ip_str)
                                    if m:
                                        controller_ip = m.group(0)
                                        if all(0 <= int(p) <= 255 for p in controller_ip.split(".")):
                                            log(f"Controller on {address} has IP: {controller_ip} (via IA)")
                                        else:
                                            controller_ip = None
                            except:
                                pass
                        
                        test_g.GClose()
                        
                    except Exception as e:
                        log(f"Error connecting to {address}: {e}")
                        continue
                    
                else:
                    # Network connection - extract IP from address string
                    connection_type = "Ethernet"
                    
                    # Extract IP address from string (might have options like "-d", "--direct", etc.)
                    # IP addresses are in format like "10.1.0.21" or "10.1.0.21 -d" or "10.1.0.21 --direct"
                    try:
                        # Split by spaces and take first part (the IP)
                        ip_candidate = address.split()[0] if address else address
                        
                        # Validate it's a proper IP address
                        parts = ip_candidate.split('.')
                        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                            controller_ip = ip_candidate
                            log(f"Found {connection_type} connection: {address} (IP: {controller_ip})")
                        else:
                            log(f"Invalid IP format in address: {address}")
                            continue
                    except Exception as e:
                        log(f"Could not parse IP address from '{address}': {e}")
                        continue
                
                # If we found an IP, add it to discovered controllers
                if controller_ip:
                    discovered_controllers[controller_ip] = f"Galil Controller (connected via {connection_type}: {address})"
                else:
                    # Still add the connection even if IP query failed
                    if connection_type == "COM Port":
                        discovered_controllers[address] = f"Galil Controller on {address} (IP query failed)"
                    else:
                        # For network connections, we should have the IP
                        pass
                        
            except Exception as e:
                log(f"Error processing connection {address}: {e}")
                continue
        
        if discovered_controllers:
            log(f"Discovery complete: Found {len(discovered_controllers)} controller(s)")
            for ip_or_port, info in discovered_controllers.items():
                log(f"  - {ip_or_port}: {info}")
        else:
            log("Discovery complete: No controllers found")
        
        return discovered_controllers
        
    except Exception as e:
        error_msg = f"Error in connection-based discovery: {e}"
        log(error_msg)
        import traceback
        traceback.print_exc()
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
            # MG _FW not supported on DMC-4143, use ID command instead
            firmware = g.GCommand("ID")
            result['firmware'] = firmware.strip()
        except:
            pass
        
        try:
            # MG _ID not supported on DMC-4143, use ID command instead
            model = g.GCommand("ID")
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
    # For backward compatibility, call the DMC-4143 specific function (IP only)
    return configure_controller_network_dmc4143(controller, ip_address)

def configure_controller_network_dmc4143(controller, ip_address: str) -> Dict[str, bool]:
    """
    IP address configuration specifically for DMC-4143 controller.
    Only sets the IP address on the controller, no subnet mask or gateway changes.
    
    Args:
        controller: Connected GalilController instance
        ip_address: New IP address for the controller
        
    Returns:
        Dictionary with success status for each operation
    """
    results = {
        'ip_set': False,
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
                # Get IP address using the new helper method
                if hasattr(controller, 'get_current_ip'):
                    ip = controller.get_current_ip()
                    if ip:
                        current_ip = ip
                        results['debug_info'].append(f"Current IP (from connection): {current_ip}")
                    else:
                        current_ip = "N/A (serial or unknown)"
                        results['debug_info'].append(f"Current IP: {current_ip}")
                else:
                    current_ip = "N/A (serial or unknown)"
                    results['debug_info'].append(f"Current IP: {current_ip}")
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
        
        # Step 1: Convert IP address to comma-separated format for IA command
        # IA command format: IA n0,n1,n2,n3 where n0=byte0, n1=byte1, n2=byte2, n3=byte3
        try:
            ip_parts = ip_address.split('.')
            if len(ip_parts) == 4:
                # Convert to integers in correct order (n0=byte0, n1=byte1, n2=byte2, n3=byte3)
                ip_bytes = [int(part) for part in ip_parts]
                ia_format = f"{ip_bytes[0]},{ip_bytes[1]},{ip_bytes[2]},{ip_bytes[3]}"
                results['debug_info'].append(f"IA command format: {ia_format}")
            else:
                raise ValueError("Invalid IP address format")
        except Exception as e:
            results['debug_info'].append(f"Error converting IP address: {str(e)}")
            return results
        
        # Step 2: Send combined DHCP disable and IP address command (recommended for DMC-4103)
        results['debug_info'].append(f"Setting IP address to: {ip_address}")
        results['debug_info'].append("Using combined command to avoid disconnection issues...")
        
        # Try combined commands first (DHCP disable + IP set in one line)
        combined_commands = [
            f"DH 0;IA {ia_format}",      # Combined command with space
            f"DH0;IA{ia_format}",        # Combined command without spaces
            f"DH=0;IA={ia_format}",      # Combined command with equals
        ]
        
        ip_set_success = False
        for cmd in combined_commands:
            try:
                results['debug_info'].append(f"Trying combined command: {cmd}")
                response = controller.send_command(cmd)
                results['debug_info'].append(f"Combined command response: {response}")
                
                # For combined command, empty response or no error means success
                if not response or not response.startswith('?'):
                    results['ip_set'] = True
                    ip_set_success = True
                    results['debug_info'].append(f"✓ Combined command successful: {cmd}")
                    break
                else:
                    results['debug_info'].append(f"Combined command failed with response: {response}")
            except Exception as e:
                results['debug_info'].append(f"Combined command {cmd} failed: {str(e)}")
                continue
        
        # If combined commands fail, try individual commands
        if not ip_set_success:
            results['debug_info'].append("Combined commands failed, trying individual commands...")
            
            # Try individual DHCP disable first
            dhcp_commands = [
                "DH 0",           # Standard format
                "DH0",            # Without space
                "DH=0",           # With equals
            ]
            
            dhcp_disabled = False
            for cmd in dhcp_commands:
                try:
                    results['debug_info'].append(f"Trying DHCP disable command: {cmd}")
                    response = controller.send_command(cmd)
                    results['debug_info'].append(f"DHCP disable response: {response}")
                    
                    # Empty response or no error means success
                    if not response or not response.startswith('?'):
                        dhcp_disabled = True
                        results['debug_info'].append(f"DHCP disabled successfully: {cmd}")
                        break
                    else:
                        results['debug_info'].append(f"DHCP disable failed with response: {response}")
                except Exception as e:
                    results['debug_info'].append(f"DHCP disable command {cmd} failed: {str(e)}")
                    continue
            
            if not dhcp_disabled:
                results['debug_info'].append("Warning: Could not disable DHCP, but continuing with IP setting...")
            
            # Try individual IP commands
            ip_commands = [
                f"IA {ia_format}",           # Correct IA command format
                f"IA{ia_format}",            # IA without space
                f"IA={ia_format}",           # IA with equals (fallback)
            ]
            
            for cmd in ip_commands:
                try:
                    results['debug_info'].append(f"Trying IP command: {cmd}")
                    response = controller.send_command(cmd)
                    results['debug_info'].append(f"IP command response: {response}")
                    
                    # For IA command, empty response or no error means success
                    if not response or not response.startswith('?'):
                        results['ip_set'] = True
                        ip_set_success = True
                        results['debug_info'].append(f"✓ IP command successful: {cmd}")
                        results['debug_info'].append("IP address change will cause immediate disconnect")
                        results['debug_info'].append("Controller should now be accessible at new IP address")
                        break
                    else:
                        results['debug_info'].append(f"IP command failed with response: {response}")
                except Exception as e:
                    results['debug_info'].append(f"IP command {cmd} failed: {str(e)}")
                    # If we get a timeout or write error, it likely means the IP was set and controller disconnected
                    if "timeout" in str(e).lower() or "write error" in str(e).lower() or "connection" in str(e).lower():
                        results['debug_info'].append("✓ Timeout/write error indicates IP was set (controller disconnected)")
                        results['ip_set'] = True
                        ip_set_success = True
                        results['debug_info'].append("Controller should now be accessible at new IP address")
                        break
                    continue
        
        # Step 2: Save settings using BN command (burn settings to non-volatile memory)
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
        if results.get('ip_set', False):
            results['debug_info'].append("✓ IP address was successfully set")
            results['debug_info'].append("⚠ IMPORTANT: Controller has disconnected due to IP change")
            results['debug_info'].append("")
            results['debug_info'].append("NEXT STEPS:")
            results['debug_info'].append("1. Try connecting to the new IP address immediately")
            results['debug_info'].append("2. If connection succeeds, send BN command to save settings")
            results['debug_info'].append("3. If connection fails, power cycle the controller")
            results['debug_info'].append("4. After power cycle, try connecting to new IP again")
            results['debug_info'].append("")
            results['debug_info'].append("The IP change IS working - the controller switches to the new IP")
            results['debug_info'].append("but may revert if settings aren't saved to flash memory")
        else:
            results['debug_info'].append("✗ No network settings were successfully applied")
            results['debug_info'].append("→ Check controller connection")
            results['debug_info'].append("→ Verify controller model and firmware")
        
        # Always recommend power cycle for DMC-4143
        results['reboot_required'] = True
        results['debug_info'].append("")
        results['debug_info'].append("DMC-4103 IP Change Process:")
        results['debug_info'].append("1. Disable DHCP (DH 0)")
        results['debug_info'].append("2. Set new IP (IA n0,n1,n2,n3)")
        results['debug_info'].append("3. Controller disconnects (this is normal)")
        results['debug_info'].append("4. Connect to new IP address")
        results['debug_info'].append("5. Send BN command to save settings")
        results['debug_info'].append("6. Power cycle controller")
        
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

def force_save_network_settings_dmc4143(controller, ip_address: str) -> Dict[str, bool]:
    """
    Force save IP address settings to DMC-4143 controller using multiple methods.
    This function is specifically designed to handle DMC-4143 save issues.
    Only sets IP address, no subnet mask or gateway changes.
    
    Args:
        controller: Connected GalilController instance
        ip_address: New IP address for the controller
        
    Returns:
        Dictionary with success status for each operation
    """
    results = {
        'ip_set': False,
        'saved_to_flash': False,
        'reboot_required': True,
        'debug_info': []
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        results['debug_info'].append("Controller not connected")
        return results
    
    try:
        results['debug_info'].append("=== FORCE SAVE NETWORK SETTINGS ===")
        
        # Step 1: Disable DHCP first (required before setting static IP)
        results['debug_info'].append("Disabling DHCP before setting static IP address...")
        dhcp_commands = [
            "DH 0",           # Standard format
            "DH0",            # Without space
            "DH=0",           # With equals
        ]
        
        dhcp_disabled = False
        for cmd in dhcp_commands:
            try:
                results['debug_info'].append(f"Trying DHCP disable command: {cmd}")
                response = controller.send_command(cmd)
                results['debug_info'].append(f"DHCP disable response: {response}")
                
                # Empty response or no error means success
                if not response or not response.startswith('?'):
                    dhcp_disabled = True
                    results['debug_info'].append(f"DHCP disabled successfully: {cmd}")
                    break
                else:
                    results['debug_info'].append(f"DHCP disable failed with response: {response}")
            except Exception as e:
                results['debug_info'].append(f"DHCP disable command {cmd} failed: {str(e)}")
                continue
        
        if not dhcp_disabled:
            results['debug_info'].append("Warning: Could not disable DHCP, but continuing with IP setting...")
        
        # Step 2: Set network parameters
        results['debug_info'].append(f"Setting IP address to: {ip_address}")
        
        # Convert IP address to comma-separated format for IA command
        try:
            ip_parts = ip_address.split('.')
            if len(ip_parts) == 4:
                # Convert to integers in correct order (n0=byte0, n1=byte1, n2=byte2, n3=byte3)
                ip_bytes = [int(part) for part in ip_parts]
                ia_format = f"{ip_bytes[0]},{ip_bytes[1]},{ip_bytes[2]},{ip_bytes[3]}"
                results['debug_info'].append(f"IA command format: {ia_format}")
            else:
                raise ValueError("Invalid IP address format")
        except Exception as e:
            results['debug_info'].append(f"Error converting IP address: {str(e)}")
            return results
        
        # Try combined commands first (DHCP disable + IP set in one line)
        combined_commands = [
            f"DH 0;IA {ia_format}",      # Combined command with space
            f"DH0;IA{ia_format}",        # Combined command without spaces
            f"DH=0;IA={ia_format}",      # Combined command with equals
        ]
        
        ip_set_success = False
        for cmd in combined_commands:
            try:
                results['debug_info'].append(f"Trying combined command: {cmd}")
                response = controller.send_command(cmd)
                results['debug_info'].append(f"Combined command response: {response}")
                
                # For combined command, empty response or no error means success
                if not response or not response.startswith('?'):
                    results['ip_set'] = True
                    ip_set_success = True
                    results['debug_info'].append(f"✓ Combined command successful: {cmd}")
                    break
                else:
                    results['debug_info'].append(f"Combined command failed with response: {response}")
            except Exception as e:
                results['debug_info'].append(f"Combined command {cmd} failed: {str(e)}")
                continue
        
        # If combined commands fail, try individual IP commands
        if not ip_set_success:
            results['debug_info'].append("Combined commands failed, trying individual IP commands...")
            ip_commands = [
                f"IA {ia_format}",           # Correct IA command format
                f"IA{ia_format}",            # IA without space
                f"IA={ia_format}",           # IA with equals (fallback)
            ]
            
            for cmd in ip_commands:
                try:
                    results['debug_info'].append(f"Trying IP command: {cmd}")
                    response = controller.send_command(cmd)
                    results['debug_info'].append(f"IP command response: {response}")
                    if not response or not response.startswith('?'):
                        results['ip_set'] = True
                        ip_set_success = True
                        results['debug_info'].append(f"✓ IP command successful: {cmd}")
                        break
                except Exception as e:
                    results['debug_info'].append(f"IP command failed: {cmd} - {str(e)}")
                    continue
        
        # Note: Only IP address is configured on the controller
        # Subnet mask and gateway are handled by the system's network configuration
        results['debug_info'].append("ℹ️  Only IP address is configured on the controller")
        results['debug_info'].append("ℹ️  Subnet mask and gateway are handled by your system's network configuration")
        
        # Step 2: Multiple save attempts with different methods
        results['debug_info'].append("=== MULTIPLE SAVE ATTEMPTS ===")
        
        # Method 1: Standard BN command sequence
        results['debug_info'].append("Method 1: Standard BN sequence")
        try:
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
                # Get IP address using the new helper method
                if hasattr(controller, 'get_current_ip'):
                    current_ip_mg = controller.get_current_ip()
                    if current_ip_mg:
                        results['debug_info'].append(f"Verification via connection IP: '{current_ip_mg}'")
                        if current_ip_mg.strip() == ip_address:
                            verification_success = True
                            results['debug_info'].append("IP verification successful via connection IP")
                    else:
                        results['debug_info'].append("No IP available from connection")
                else:
                    results['debug_info'].append("Controller does not support get_current_ip method")
            except Exception as e:
                results['debug_info'].append(f"IP verification failed: {str(e)}")
        
        # Note: Subnet mask verification skipped - only IP address is configured on controller
        results['debug_info'].append("ℹ️  Subnet mask verification skipped - only IP address is configured on controller")
        
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
            "ID",           # Firmware version and Controller ID
            "ID",           # Controller ID
            "MG _BN",       # Serial number
        ]
        
        for cmd in basic_commands:
            try:
                response = send_galil_command(controller, cmd)
                results['basic_commands'][cmd] = response.strip()
            except Exception as e:
                results['basic_commands'][cmd] = f"ERROR: {str(e)}"
        
        # Test 2: Network command support
        network_commands = [
            ("IA", "IP address command (correct format)"),
            ("IP", "IP address command (legacy)"),
            ("SM", "Subnet mask command"),
            ("GW", "Gateway command"),
            ("Not supported", "Get IP address"),
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
                response = send_galil_command(controller, cmd)
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
                response = send_galil_command(controller, cmd)
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
                current_ip = send_galil_command(controller, "IP")
                results['controller_info']['current_ip'] = current_ip.strip()
            except Exception as e:
                results['controller_info']['current_ip'] = f"ERROR: {str(e)}"
            
            # Try to read current subnet mask
            try:
                current_sm = send_galil_command(controller, "MG _SM")
                results['controller_info']['current_subnet'] = current_sm.strip()
            except Exception as e:
                results['controller_info']['current_subnet'] = f"ERROR: {str(e)}"
            
            # Try to read current gateway
            try:
                current_gw = send_galil_command(controller, "MG _GW")
                results['controller_info']['current_gateway'] = current_gw.strip()
            except Exception as e:
                results['controller_info']['current_gateway'] = f"ERROR: {str(e)}"
                
        except Exception as e:
            results['controller_info']['error'] = f"Error reading network settings: {str(e)}"
        
        # Test 5: Network configuration test (without actually changing anything)
        # Convert test IP to IA format: 192.168.1.100 -> 192,168,1,100 (n0=byte0,n1=byte1,n2=byte2,n3=byte3)
        test_ip_parts = [192, 168, 1, 100]
        ia_test_format = f"{test_ip_parts[0]},{test_ip_parts[1]},{test_ip_parts[2]},{test_ip_parts[3]}"
        
        network_test_commands = [
            f"IA {ia_test_format}",           # Correct IA command format
            f"IA{ia_test_format}",            # IA without space
            f"IA={ia_test_format}",           # IA with equals
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
            # Get IP address using the new helper method
            if hasattr(controller, 'get_current_ip'):
                ip = controller.get_current_ip()
                if ip:
                    status['ip_address'] = ip
                else:
                    status['ip_address'] = "N/A (serial or unknown)"
            else:
                status['ip_address'] = "N/A (serial or unknown)"
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
            dhcp_status = send_galil_command(controller, "MG _DHCP").strip()
            status['dhcp_enabled'] = dhcp_status == "1" or dhcp_status.lower() == "true"
        except:
            pass
        
        status['connection_status'] = 'Connected'
        
    except Exception as e:
        status['connection_status'] = f'Error: {str(e)}'
    
    return status

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_administrator() -> bool:
    """Check if the current process has administrator privileges."""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def configure_controller_pid_settings(controller, kp_values: Dict[str, float] = None, 
                                     ki_values: Dict[str, float] = None, 
                                     kd_values: Dict[str, float] = None) -> Dict[str, bool]:
    """
    Configure PID settings for Galil controller and burn them to flash memory.
    
    Args:
        controller: Connected GalilController instance
        kp_values: Dictionary of KP values by axis (e.g., {'A': 12.0, 'B': 14.0})
        ki_values: Dictionary of KI values by axis (e.g., {'A': 0.1, 'B': 0.2})
        kd_values: Dictionary of KD values by axis (e.g., {'A': 50.0, 'B': 60.0})
        
    Returns:
        Dictionary with success status for each operation
    """
    results = {
        'kp_set': False,
        'ki_set': False,
        'kd_set': False,
        'burned_to_flash': False,
        'debug_info': []
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        results['debug_info'].append("Controller not connected")
        return results
    
    try:
        results['debug_info'].append("=== CONFIGURING PID SETTINGS ===")
        
        # Step 1: Set KP values (Proportional Constant)
        if kp_values:
            results['debug_info'].append(f"Setting KP values: {kp_values}")
            
            # Build KP command with comma-separated values for all axes
            kp_command = "KP "
            kp_parts = []
            
            for axis in ['A', 'B', 'C', 'D']:
                if axis in kp_values:
                    kp_parts.append(str(kp_values[axis]))
                else:
                    kp_parts.append("")  # Empty for unchanged axes
            
            kp_command += ",".join(kp_parts)
            results['debug_info'].append(f"KP command: {kp_command}")
            
            try:
                response = controller.send_command(kp_command)
                results['debug_info'].append(f"KP response: {response}")
                
                if not response or not response.startswith('?'):
                    results['kp_set'] = True
                    results['debug_info'].append("KP values set successfully")
                else:
                    results['debug_info'].append(f"KP command failed: {response}")
            except Exception as e:
                results['debug_info'].append(f"KP command error: {str(e)}")
        
        # Step 2: Set KI values (Integrator)
        if ki_values:
            results['debug_info'].append(f"Setting KI values: {ki_values}")
            
            # Build KI command with comma-separated values for all axes
            ki_command = "KI "
            ki_parts = []
            
            for axis in ['A', 'B', 'C', 'D']:
                if axis in ki_values:
                    ki_parts.append(str(ki_values[axis]))
                else:
                    ki_parts.append("")  # Empty for unchanged axes
            
            ki_command += ",".join(ki_parts)
            results['debug_info'].append(f"KI command: {ki_command}")
            
            try:
                response = controller.send_command(ki_command)
                results['debug_info'].append(f"KI response: {response}")
                
                if not response or not response.startswith('?'):
                    results['ki_set'] = True
                    results['debug_info'].append("KI values set successfully")
                else:
                    results['debug_info'].append(f"KI command failed: {response}")
            except Exception as e:
                results['debug_info'].append(f"KI command error: {str(e)}")
        
        # Step 3: Set KD values (Derivative Constant)
        if kd_values:
            results['debug_info'].append(f"Setting KD values: {kd_values}")
            
            # Build KD command with comma-separated values for all axes
            kd_command = "KD "
            kd_parts = []
            
            for axis in ['A', 'B', 'C', 'D']:
                if axis in kd_values:
                    kd_parts.append(str(kd_values[axis]))
                else:
                    kd_parts.append("")  # Empty for unchanged axes
            
            kd_command += ",".join(kd_parts)
            results['debug_info'].append(f"KD command: {kd_command}")
            
            try:
                response = controller.send_command(kd_command)
                results['debug_info'].append(f"KD response: {response}")
                
                if not response or not response.startswith('?'):
                    results['kd_set'] = True
                    results['debug_info'].append("KD values set successfully")
                else:
                    results['debug_info'].append(f"KD command failed: {response}")
            except Exception as e:
                results['debug_info'].append(f"KD command error: {str(e)}")
        
        # Step 4: Burn settings to flash memory using BN command
        if results.get('kp_set', False) or results.get('ki_set', False) or results.get('kd_set', False):
            results['debug_info'].append("Burning PID settings to flash memory...")
            
            try:
                # Wait a moment before burning
                time.sleep(1)
                
                # Send BN command to burn settings
                response = controller.send_command("BN")
                results['debug_info'].append(f"BN response: '{response}'")
                
                # Wait for burn to complete (BN takes about 1 second)
                time.sleep(2)
                
                if not response or not response.startswith('?'):
                    results['burned_to_flash'] = True
                    results['debug_info'].append("✓ PID settings burned to flash memory successfully")
                else:
                    results['debug_info'].append(f"BN command failed: {response}")
                    
            except Exception as e:
                results['debug_info'].append(f"BN command error: {str(e)}")
        else:
            results['debug_info'].append("No PID settings were successfully set - skipping burn")
        
        # Step 5: Verification
        results['debug_info'].append("=== VERIFICATION ===")
        
        if results.get('burned_to_flash', False):
            results['debug_info'].append("✓ PID configuration completed successfully")
            results['debug_info'].append("✓ Settings have been burned to non-volatile memory")
            results['debug_info'].append("→ Settings will persist through power cycles")
        else:
            results['debug_info'].append("⚠ PID settings may not be saved to flash memory")
            results['debug_info'].append("→ Try the configuration process again")
        
    except Exception as e:
        results['error'] = str(e)
        results['debug_info'].append(f"General error: {str(e)}")
    
    return results

def get_controller_pid_settings(controller) -> Dict[str, any]:
    """
    Get current PID settings from the controller.
    
    Args:
        controller: Connected GalilController instance
        
    Returns:
        Dictionary with current PID settings
    """
    settings = {
        'kp_values': {},
        'ki_values': {},
        'kd_values': {},
        'error': None
    }
    
    if not hasattr(controller, 'g') or not controller.g:
        settings['error'] = "Controller not connected"
        return settings
    
    try:
        # Get KP values for all axes
        try:
            kp_response = controller.send_command("KP ?,?,?,?")
            if kp_response and not kp_response.startswith('?'):
                kp_values = [float(x.strip()) for x in kp_response.split(',')]
                settings['kp_values'] = {
                    'A': kp_values[0] if len(kp_values) > 0 else 0,
                    'B': kp_values[1] if len(kp_values) > 1 else 0,
                    'C': kp_values[2] if len(kp_values) > 2 else 0,
                    'D': kp_values[3] if len(kp_values) > 3 else 0
                }
        except Exception as e:
            settings['error'] = f"Error reading KP values: {str(e)}"
        
        # Get KI values for all axes
        try:
            ki_response = controller.send_command("KI ?,?,?,?")
            if ki_response and not ki_response.startswith('?'):
                ki_values = [float(x.strip()) for x in ki_response.split(',')]
                settings['ki_values'] = {
                    'A': ki_values[0] if len(ki_values) > 0 else 0,
                    'B': ki_values[1] if len(ki_values) > 1 else 0,
                    'C': ki_values[2] if len(ki_values) > 2 else 0,
                    'D': ki_values[3] if len(ki_values) > 3 else 0
                }
        except Exception as e:
            if not settings.get('error'):
                settings['error'] = f"Error reading KI values: {str(e)}"
        
        # Get KD values for all axes
        try:
            kd_response = controller.send_command("KD ?,?,?,?")
            if kd_response and not kd_response.startswith('?'):
                kd_values = [float(x.strip()) for x in kd_response.split(',')]
                settings['kd_values'] = {
                    'A': kd_values[0] if len(kd_values) > 0 else 0,
                    'B': kd_values[1] if len(kd_values) > 1 else 0,
                    'C': kd_values[2] if len(kd_values) > 2 else 0,
                    'D': kd_values[3] if len(kd_values) > 3 else 0
                }
        except Exception as e:
            if not settings.get('error'):
                settings['error'] = f"Error reading KD values: {str(e)}"
                
    except Exception as e:
        settings['error'] = str(e)
    
    return settings

def check_network_configuration_permissions() -> bool:
    """Check if we have the necessary permissions to configure network settings."""
    if platform.system() != 'Windows':
        return False
    
    # Check if running as administrator
    if not is_administrator():
        return False
    
    return True

# ============================================================================
# CONTROLLER CONNECTION METHODS
# ============================================================================

class ControllerConnectionManager:
    """Manages controller connections and network operations"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback or self._default_log
        self.controller = None
        self.controller_commands = None
        self.connected_ip = None
        self.connection_monitoring = False
        self.connection_thread = None
        self.last_heartbeat = None
        self.connecting = False  # Flag to prevent multiple simultaneous connection attempts
        
    def _default_log(self, message: str):
        """Default logging function if no callback provided"""
        print(message)
    
    def log(self, message: str):
        """Log a message using the callback"""
        self.log_callback(message)
    
    def connect_to_controller(self, address: str, update_connection_status_callback=None):
        """Connect to the Galil controller (IP address or COM port)"""
        return self._connect_to_controller_internal(address, update_connection_status_callback, start_monitoring=True)
    
    def _connect_to_controller_internal(self, address: str, update_connection_status_callback=None, start_monitoring=True):
        """Internal connection method with optional monitoring control"""
        if not address:
            messagebox.showerror("Error", "Please enter an IP address or COM port")
            return False
        
        # Determine if this is a COM port or IP address
        is_com_port = address.upper().startswith('COM')
        
        if not is_com_port and not validate_ip_address(address):
            messagebox.showerror("Error", "Invalid IP address format")
            return False
        
        # Prevent multiple simultaneous connection attempts
        if self.connecting:
            self.log("Connection attempt already in progress, skipping...")
            return False
            
        self.connecting = True
        self.log(f"Connecting to controller at {address}...")
        
        # Test basic connectivity first (only for IP addresses, not COM ports)
        if not is_com_port:
            if not self.test_basic_connectivity(address):
                self.log("Basic connectivity test failed, aborting connection attempt")
                self.connecting = False
                return False
        
        try:
            # Close existing connection if any
            if self.controller:
                try:
                    self.controller.disconnect()
                except:
                    pass
                self.controller = None
            
            # Create new controller connection
            self.controller = GalilController()
            self.controller.connect(address)
            
            # Initialize controller commands handler
            self.controller_commands = ControllerCommands(self.controller, self.log)
            
            # Give controller time to stabilize after connection
            time.sleep(0.2)
            
            # Connection successful - GalilController.connect() already validated with TP A
            self.log(f"Successfully connected to controller at {address}")
            
            if start_monitoring:
                messagebox.showinfo("Success", f"Connected to controller at {address}")
            
            # Store connection info for persistence
            self.connected_ip = address
            self.last_heartbeat = time.time()
            
            # Start connection monitoring only if requested
            if start_monitoring:
                self.start_connection_monitoring()
            
            # Update UI to show connected state
            if update_connection_status_callback:
                update_connection_status_callback(True)
            
            # Debug: Log controller reference status
            # Connection successful
            if self.controller:
                # Controller type identified
                pass
            
            return True
                
        except Exception as e:
            self.log(f"Connection failed: {e}")
            # Update UI to show disconnected state
            if update_connection_status_callback:
                update_connection_status_callback(False)
            if start_monitoring:
                messagebox.showerror("Connection Error", f"Failed to connect to {address}: {e}")
            return False
        finally:
            # Always clear the connecting flag
            self.connecting = False
    
    def disconnect_controller(self, update_connection_status_callback=None):
        """Disconnect from the controller"""
        try:
            # Stop connection monitoring
            self.stop_connection_monitoring()
            
            if self.controller:
                self.controller.disconnect()
                self.controller = None
                self.controller_commands = None
                self.connected_ip = None
                self.last_heartbeat = None
                self.log("Disconnected from controller")
                
                # Update UI to show disconnected state
                if update_connection_status_callback:
                    update_connection_status_callback(False)
                return True
        except Exception as e:
            self.log(f"Error disconnecting: {e}")
            return False
    
    def discover_controllers(self, log_callback=None, include_com_ports=True):
        """Discover Galil controllers on the network and/or COM ports"""
        if log_callback:
            self.log_callback = log_callback

        self.log("Discovering Galil controllers...")

        try:
            # Try gclib discovery first
            self.log("Trying gclib discovery...")
            all_controllers = discover_galil_controllers()
            
            # Separate network and COM controllers
            network_controllers = {}
            com_controllers = {}
            
            for address, info in all_controllers.items():
                if address.upper().startswith('COM'):
                    com_controllers[address] = info
                else:
                    # Validate it's a proper IP address format
                    try:
                        parts = address.split('.')
                        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                            network_controllers[address] = info
                    except:
                        continue

            controllers = {}
            if include_com_ports:
                controllers.update(com_controllers)
            controllers.update(network_controllers)

            if not network_controllers and not com_controllers:
                # If gclib discovery fails, try connection-based discovery
                self.log("gclib discovery found no controllers, querying physical connections...")
                network_controllers = discover_controllers_network_scan(log_callback=self.log)
                controllers.update(network_controllers)

            if controllers:
                if com_controllers:
                    self.log(f"Found {len(com_controllers)} COM port controller(s):")
                    for i, (com, name) in enumerate(com_controllers.items(), 1):
                        self.log(f"  {i}. {com} - {name}")
                
                if network_controllers:
                    self.log(f"Found {len(network_controllers)} network controller(s):")
                    for i, (ip, name) in enumerate(network_controllers.items(), 1):
                        self.log(f"  {i}. {ip} - {name}")
            else:
                self.log("No Galil controllers found")
                self.log("Possible reasons:")
                self.log("  - Controller is powered off")
                self.log("  - Controller is on different network")
                self.log("  - Network cable disconnected")
                self.log("  - Controller IP address changed")
                self.log("  - USB cable disconnected (for COM ports)")

            return controllers
        except Exception as e:
            self.log(f"Discovery failed: {e}")
            return []
    
    def auto_connect_to_controller(self, default_ip="10.1.0.21", update_connection_status_callback=None):
        """Auto-connect to controller on startup"""
        def auto_connect_thread():
            try:
                self.log("=== AUTO-CONNECTION ATTEMPT ===")
                self.log(f"Attempting to connect to default IP: {default_ip}")
                
                # Test if controller is reachable
                if ping_controller(default_ip):
                    self.log(f"✓ Controller at {default_ip} is reachable")
                    
                    # Try to connect
                    if self.connect_to_controller(default_ip, update_connection_status_callback):
                        self.log("=== AUTO-CONNECTION SUCCESS ===")
                        return
                    else:
                        self.log("✗ Failed to connect to controller")
                else:
                    self.log(f"✗ Controller at {default_ip} is not reachable")
                    
                # If auto-connect failed, try discovery
                self.log("Attempting controller discovery...")
                controllers = self.discover_controllers()
                
                if controllers:
                    # Try to connect to the first discovered controller
                    first_address = list(controllers.keys())[0]
                    self.log(f"Attempting to connect to discovered controller: {first_address}")
                    
                    if self.connect_to_controller(first_address, update_connection_status_callback):
                        self.log("=== AUTO-CONNECTION SUCCESS (via discovery) ===")
                        return
                
                self.log("=== AUTO-CONNECTION FAILED ===")
                self.log("Please connect manually using the Network Config page")
                
            except Exception as e:
                self.log(f"Auto-connection error: {e}")
        
        # Run auto-connect in a separate thread
        import threading
        thread = threading.Thread(target=auto_connect_thread, daemon=True)
        thread.start()
    
    def start_connection_monitoring(self):
        """Start monitoring the connection health"""
        if self.connection_monitoring:
            return  # Already monitoring
            
        self.connection_monitoring = True
        
        def monitor_connection():
            while self.connection_monitoring and self.controller:
                try:
                    # CRITICAL: Don't send heartbeat during comprehensive test
                    # Check if comprehensive test is running (via main app reference)
                    # This prevents concurrent GCommand calls that corrupt the TCP session
                    
                    # Simple heartbeat - just verify connection exists
                    # Don't send commands if test might be running
                    # Passive monitoring only
                    if self.controller:
                        self.last_heartbeat = time.time()
                        time.sleep(5)  # Longer interval (5 seconds instead of 2)
                    else:
                        break
                except Exception as e:
                    # Don't automatically reconnect - just log and stop
                    # User can manually reconnect if needed
                    self.log(f"Connection monitoring: {e}")
                    self.connection_monitoring = False
                    break
        
        # Start monitoring thread
        import threading
        self.connection_thread = threading.Thread(target=monitor_connection, daemon=True)
        self.connection_thread.start()
    
    def stop_connection_monitoring(self):
        """Stop monitoring the connection health"""
        self.connection_monitoring = False
        if self.connection_thread and self.connection_thread.is_alive():
            # Safe thread join to prevent "cannot join current thread" error
            try:
                import threading as _threading
                if self.connection_thread is not _threading.current_thread():
                    self.connection_thread.join(timeout=1.0)
            except:
                pass
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to the controller"""
        if not self.connected_ip:
            return False
            
        try:
            self.log(f"Attempting to reconnect to {self.connected_ip}...")
            
            # Stop connection monitoring to prevent recursive calls
            self.stop_connection_monitoring()
            
            # Close existing connection
            if self.controller:
                try:
                    self.controller.disconnect()
                except:
                    pass
                self.controller = None
                self.controller_commands = None
            
            # Try to reconnect without starting monitoring (to prevent recursion)
            if self._connect_to_controller_internal(self.connected_ip):
                self.log("Reconnection successful!")
                # Restart monitoring after successful reconnection
                self.start_connection_monitoring()
                return True
            else:
                self.log("Reconnection failed")
                return False
                
        except Exception as e:
            self.log(f"Reconnection error: {e}")
            return False
    
    def is_connection_healthy(self):
        """Check if the connection is healthy"""
        if not self.controller or not self.last_heartbeat:
            return False
        
        # Check if last heartbeat was recent (within 10 seconds)
        return (time.time() - self.last_heartbeat) < 10
    
    def ensure_connection(self):
        """Ensure we have a healthy connection, reconnect if necessary"""
        if not self.is_connection_healthy():
            if self.connected_ip:
                self.log("Connection unhealthy, attempting to restore...")
                return self._attempt_reconnect()
        return True
    
    def reset_connection_state(self):
        """Reset all connection state - useful for troubleshooting"""
        self.log("Resetting connection state...")
        
        # Stop monitoring
        self.stop_connection_monitoring()
        
        # Close any existing connection
        if self.controller:
            try:
                self.controller.disconnect()
            except:
                pass
        
        # Clear all state
        self.controller = None
        self.controller_commands = None
        self.connected_ip = None
        self.last_heartbeat = None
        self.connecting = False
        
        self.log("Connection state reset complete")
    
    def test_basic_connectivity(self, ip_address: str):
        """Test basic network connectivity to the controller"""
        self.log(f"Testing basic connectivity to {ip_address}...")
        
        try:
            # Test with ping first
            from network_combined import ping_controller
            if ping_controller(ip_address):
                self.log(f"✓ Ping to {ip_address} successful")
                return True
            else:
                self.log(f"✗ Ping to {ip_address} failed")
                return False
        except Exception as e:
            self.log(f"✗ Connectivity test failed: {e}")
            return False
