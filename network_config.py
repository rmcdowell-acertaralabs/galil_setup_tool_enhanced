"""
Network Configuration Module for Windows
Handles reading and setting network adapter configurations
"""

import subprocess
import re
import os
import platform
from typing import Dict, List, Optional, Tuple
from tkinter import messagebox

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

def is_administrator() -> bool:
    """Check if the current process has administrator privileges."""
    try:
        return os.getuid() == 0
    except AttributeError:
        # Windows
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def check_network_configuration_permissions() -> bool:
    """Check if we have the necessary permissions to configure network settings."""
    if platform.system() != 'Windows':
        return False
    
    # Check if running as administrator
    if not is_administrator():
        return False
    
    return True
