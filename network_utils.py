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

def get_controller_network_settings(controller) -> Dict[str, str]:
    """
    Get current network settings from a connected controller.
    
    Args:
        controller: Connected GalilController instance
        
    Returns:
        Dictionary with network settings
    """
    settings = {}
    
    if not hasattr(controller, 'g') or not controller.g:
        return settings
    
    # Try to get various network settings
    commands = {
        'ip': ['MG _IP', 'MG _IPADDR', 'MG _IPADDRESS'],
        'subnet_mask': ['MG _SM', 'MG _SUBNET', 'MG _MASK'],
        'gateway': ['MG _GW', 'MG _GATEWAY'],
        'mac': ['MG _MAC', 'MG _MACADDR'],
        'hostname': ['MG _HN', 'MG _HOSTNAME']
    }
    
    for setting, cmd_list in commands.items():
        for cmd in cmd_list:
            try:
                response = controller.send_command(cmd)
                if response and response.strip():
                    settings[setting] = response.strip()
                    break
            except:
                continue
    
    return settings

def set_controller_network_settings(controller, settings: Dict[str, str]) -> Dict[str, bool]:
    """
    Set network settings on a connected controller.
    
    Args:
        controller: Connected GalilController instance
        settings: Dictionary with network settings to set
        
    Returns:
        Dictionary with success status for each setting
    """
    results = {}
    
    if not hasattr(controller, 'g') or not controller.g:
        return results
    
    # Define command mappings
    command_mappings = {
        'ip': ['IP{value}', 'IP {value}', 'IP={value}'],
        'subnet_mask': ['SM{value}', 'SM {value}', 'SM={value}'],
        'gateway': ['GW{value}', 'GW {value}', 'GW={value}'],
        'hostname': ['HN{value}', 'HN {value}', 'HN={value}']
    }
    
    for setting, value in settings.items():
        if setting in command_mappings:
            success = False
            for cmd_template in command_mappings[setting]:
                try:
                    cmd = cmd_template.format(value=value)
                    controller.send_command(cmd)
                    success = True
                    break
                except:
                    continue
            results[setting] = success
    
    return results

