"""
Proper gclib Wrapper for Galil Setup Tool

This module provides a robust wrapper around the Galil gclib library
with proper error handling and fallback mechanisms.
"""

import platform
import os
import sys
from ctypes import *
from typing import Optional, Union, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GalilConnectionError(Exception):
    """Custom exception for Galil connection errors"""
    pass

class GalilCommandError(Exception):
    """Custom exception for Galil command errors"""
    pass

class GalilLibWrapper:
    """Proper wrapper for Galil gclib with error handling"""
    
    def __init__(self):
        """Initialize the Galil library wrapper"""
        self.g = None
        self.connected = False
        self.connection_string = ""
        self.last_error = ""
        self._setup_library()
    
    def _setup_library(self) -> bool:
        """Setup the Galil library with proper error handling"""
        try:
            if platform.system() == 'Windows':
                return self._setup_windows()
            elif platform.system() == 'Linux':
                return self._setup_linux()
            elif platform.system() == 'Darwin':
                return self._setup_macos()
            else:
                logger.error(f"Unsupported platform: {platform.system()}")
                return False
        except Exception as e:
            logger.error(f"Failed to setup Galil library: {e}")
            return False
    
    def _setup_windows(self) -> bool:
        """Setup Galil library on Windows"""
        try:
            # Try to load from local directory first
            script_dir = os.path.dirname(os.path.abspath(__file__))
            local_gclib = os.path.join(script_dir, 'gclib.dll')
            local_gclibo = os.path.join(script_dir, 'gclibo.dll')
            
            if os.path.exists(local_gclib) and os.path.exists(local_gclibo):
                logger.info("Using local gclib DLLs")
                return self._load_windows_dlls(local_gclib, local_gclibo)
            
            # Try system installation
            if '64 bit' in platform.python_compiler():
                system_gclib = r'C:\Program Files (x86)\Galil\gclib\dll\x64\gclib.dll'
                system_gclibo = r'C:\Program Files (x86)\Galil\gclib\dll\x64\gclibo.dll'
            else:
                system_gclib = r'C:\Program Files (x86)\Galil\gclib\dll\x86\gclib.dll'
                system_gclibo = r'C:\Program Files (x86)\Galil\gclib\dll\x86\gclibo.dll'
            
            if os.path.exists(system_gclib) and os.path.exists(system_gclibo):
                logger.info("Using system gclib DLLs")
                return self._load_windows_dlls(system_gclib, system_gclibo)
            
            logger.warning("No gclib DLLs found, using mock implementation")
            return self._setup_mock()
            
        except Exception as e:
            logger.error(f"Windows setup failed: {e}")
            return self._setup_mock()
    
    def _load_windows_dlls(self, gclib_path: str, gclibo_path: str) -> bool:
        """Load Windows DLLs with proper error handling"""
        try:
            # Load crypto DLLs if available
            self._load_crypto_dlls()
            
            # Load main DLLs
            self._gclib = WinDLL(gclib_path)
            self._gclibo = WinDLL(gclibo_path)
            
            # Setup function signatures for 32-bit
            if '64 bit' not in platform.python_compiler():
                self._setup_32bit_functions()
            
            logger.info("Successfully loaded gclib DLLs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load DLLs: {e}")
            return self._setup_mock()
    
    def _load_crypto_dlls(self):
        """Load crypto DLLs if available"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            crypto_dlls = [
                'libcrypto-3.dll',
                'libssl-3.dll'
            ]
            
            for dll_name in crypto_dlls:
                local_path = os.path.join(script_dir, dll_name)
                if os.path.exists(local_path):
                    WinDLL(local_path)
                    logger.debug(f"Loaded {dll_name} from local directory")
                else:
                    # Try system paths
                    system_paths = [
                        r'C:\Program Files (x86)\Galil\gclib\dll\x64',
                        r'C:\Program Files (x86)\Galil\gclib\dll\x86'
                    ]
                    for sys_path in system_paths:
                        sys_dll_path = os.path.join(sys_path, dll_name)
                        if os.path.exists(sys_dll_path):
                            WinDLL(sys_dll_path)
                            logger.debug(f"Loaded {dll_name} from system")
                            break
        except Exception as e:
            logger.debug(f"Could not load crypto DLLs: {e}")
    
    def _setup_32bit_functions(self):
        """Setup function signatures for 32-bit Windows"""
        try:
            # Reassign symbol names for 32-bit
            setattr(self._gclib, 'GArrayDownload', getattr(self._gclib, '_GArrayDownload@20'))
            setattr(self._gclib, 'GArrayUpload', getattr(self._gclib, '_GArrayUpload@28'))
            setattr(self._gclib, 'GClose', getattr(self._gclib, '_GClose@4'))
            setattr(self._gclib, 'GCommand', getattr(self._gclib, '_GCommand@20'))
            setattr(self._gclib, 'GFirmwareDownload', getattr(self._gclib, '_GFirmwareDownload@8'))
            setattr(self._gclib, 'GInterrupt', getattr(self._gclib, '_GInterrupt@8'))
            setattr(self._gclib, 'GMessage', getattr(self._gclib, '_GMessage@12'))
            setattr(self._gclib, 'GOpen', getattr(self._gclib, '_GOpen@8'))
            setattr(self._gclib, 'GProgramDownload', getattr(self._gclib, '_GProgramDownload@12'))
            setattr(self._gclib, 'GProgramUpload', getattr(self._gclib, '_GProgramUpload@12'))
            
            # gclibo functions
            setattr(self._gclibo, 'GAddresses', getattr(self._gclibo, '_GAddresses@8'))
            setattr(self._gclibo, 'GArrayDownloadFile', getattr(self._gclibo, '_GArrayDownloadFile@8'))
            setattr(self._gclibo, 'GArrayUploadFile', getattr(self._gclibo, '_GArrayUploadFile@12'))
            setattr(self._gclibo, 'GAssign', getattr(self._gclibo, '_GAssign@8'))
            setattr(self._gclibo, 'GError', getattr(self._gclibo, '_GError@12'))
            setattr(self._gclibo, 'GInfo', getattr(self._gclibo, '_GInfo@12'))
            setattr(self._gclibo, 'GIpRequests', getattr(self._gclibo, '_GIpRequests@8'))
            setattr(self._gclibo, 'GMotionComplete', getattr(self._gclibo, '_GMotionComplete@8'))
            setattr(self._gclibo, 'GProgramDownloadFile', getattr(self._gclibo, '_GProgramDownloadFile@12'))
            setattr(self._gclibo, 'GSleep', getattr(self._gclibo, '_GSleep@4'))
            setattr(self._gclibo, 'GProgramUploadFile', getattr(self._gclibo, '_GProgramUploadFile@8'))
            setattr(self._gclibo, 'GTimeout', getattr(self._gclibo, '_GTimeout@8'))
            setattr(self._gclibo, 'GVersion', getattr(self._gclibo, '_GVersion@8'))
            setattr(self._gclibo, 'GSetupDownloadFile', getattr(self._gclibo, '_GSetupDownloadFile@20'))
            setattr(self._gclibo, 'GServerStatus', getattr(self._gclibo, '_GServerStatus@8'))
            setattr(self._gclibo, 'GSetServer', getattr(self._gclibo, '_GSetServer@4'))
            setattr(self._gclibo, 'GListServers', getattr(self._gclibo, '_GListServers@8'))
            setattr(self._gclibo, 'GPublishServer', getattr(self._gclibo, '_GPublishServer@12'))
            setattr(self._gclibo, 'GRemoteConnections', getattr(self._gclibo, '_GRemoteConnections@8'))
        except Exception as e:
            logger.warning(f"Could not setup 32-bit functions: {e}")
    
    def _setup_linux(self) -> bool:
        """Setup Galil library on Linux"""
        try:
            cdll.LoadLibrary("libgclib.so.0")
            self._gclib = CDLL("libgclib.so.0")
            cdll.LoadLibrary("libgclibo.so.0")
            self._gclibo = CDLL("libgclibo.so.0")
            logger.info("Successfully loaded Linux gclib")
            return True
        except Exception as e:
            logger.error(f"Linux setup failed: {e}")
            return self._setup_mock()
    
    def _setup_macos(self) -> bool:
        """Setup Galil library on macOS"""
        try:
            gclib_path = '/Applications/gclib/dylib/gclib.0.dylib'
            gclibo_path = '/Applications/gclib/dylib/gclibo.0.dylib'
            
            cdll.LoadLibrary(gclib_path)
            self._gclib = CDLL(gclib_path)
            cdll.LoadLibrary(gclibo_path)
            self._gclibo = CDLL(gclibo_path)
            logger.info("Successfully loaded macOS gclib")
            return True
        except Exception as e:
            logger.error(f"macOS setup failed: {e}")
            return self._setup_mock()
    
    def _setup_mock(self) -> bool:
        """Setup mock implementation for development"""
        logger.info("Using mock gclib implementation")
        self._gclib = MockDLL("gclib")
        self._gclibo = MockDLL("gclibo")
        return True
    
    def GOpen(self, connection_string: str) -> int:
        """Open connection to Galil controller"""
        try:
            if hasattr(self._gclib, 'GOpen'):
                result = self._gclib.GOpen(connection_string.encode('utf-8'), byref(c_void_p()))
                if result == 0:
                    self.connected = True
                    self.connection_string = connection_string
                    logger.info(f"Connected to: {connection_string}")
                else:
                    self.last_error = f"GOpen failed with code: {result}"
                    logger.error(self.last_error)
                return result
            else:
                # Mock implementation
                self.connected = True
                self.connection_string = connection_string
                logger.info(f"Mock connected to: {connection_string}")
                return 0
        except Exception as e:
            self.last_error = f"GOpen exception: {e}"
            logger.error(self.last_error)
            raise GalilConnectionError(self.last_error)
    
    def GClose(self) -> int:
        """Close connection to Galil controller"""
        try:
            if hasattr(self._gclib, 'GClose') and self.connected:
                result = self._gclib.GClose()
                self.connected = False
                logger.info("Disconnected from controller")
                return result
            else:
                self.connected = False
                logger.info("Mock disconnected")
                return 0
        except Exception as e:
            self.last_error = f"GClose exception: {e}"
            logger.error(self.last_error)
            return -1
    
    def GCommand(self, command: str) -> str:
        """Send command to Galil controller"""
        try:
            if not self.connected:
                raise GalilConnectionError("Not connected to controller")
            
            if hasattr(self._gclib, 'GCommand'):
                # Real implementation
                response_buffer = create_string_buffer(1024)
                result = self._gclib.GCommand(
                    command.encode('utf-8'),
                    response_buffer,
                    sizeof(response_buffer),
                    None
                )
                if result == 0:
                    response = response_buffer.value.decode('utf-8', errors='ignore')
                    logger.debug(f"Command: {command} -> Response: {response}")
                    return response
                else:
                    self.last_error = f"GCommand failed with code: {result}"
                    logger.error(self.last_error)
                    return "?"
            else:
                # Mock implementation
                response = self._mock_command(command)
                logger.debug(f"Mock Command: {command} -> Response: {response}")
                return response
        except Exception as e:
            self.last_error = f"GCommand exception: {e}"
            logger.error(self.last_error)
            raise GalilCommandError(self.last_error)
    
    def GInfo(self) -> str:
        """Get controller information"""
        try:
            if hasattr(self._gclib, 'GInfo'):
                info_buffer = create_string_buffer(1024)
                result = self._gclib.GInfo(info_buffer, sizeof(info_buffer))
                if result == 0:
                    return info_buffer.value.decode('utf-8', errors='ignore')
                else:
                    return f"GInfo failed with code: {result}"
            else:
                return "Mock Galil Controller - Development Mode"
        except Exception as e:
            return f"GInfo exception: {e}"
    
    def _mock_command(self, command: str) -> str:
        """Mock command responses for development"""
        command = command.strip().upper()
        
        # Common mock responses
        mock_responses = {
            "ID": "DMC-4143 Rev 1.2a Mock Controller",
            "TPA": "1000",
            "TPB": "2000", 
            "TPC": "3000",
            "TPD": "4000",
            "IA ?": "192,168,1,100",
            "DH ?": "0",
            "TH": "Mock Network Info",
            "TC": "0",
            "TE": "No error",
            "MG _MOA": "0",
            "MG _MOB": "0",
            "MG _MOC": "0",
            "MG _MOD": "0",
            "MG _BGA": "0",
            "MG _BGB": "0",
            "MG _BGC": "0",
            "MG _BGD": "0"
        }
        
        # Check for exact matches first
        if command in mock_responses:
            return mock_responses[command]
        
        # Check for patterns
        if command.startswith("TP"):
            return "1000"  # Mock position
        elif command.startswith("MG _MO"):
            return "0"  # Mock motor status (0 = on)
        elif command.startswith("MG _BG"):
            return "0"  # Mock motion status (0 = idle)
        elif "?" in command:
            return "Mock response"
        else:
            return ""  # Empty response for set commands

class MockDLL:
    """Mock DLL for development"""
    
    def __init__(self, name: str):
        self.name = name
    
    def __getattr__(self, name):
        def mock_function(*args, **kwargs):
            logger.debug(f"Mock {self.name}.{name} called")
            return 0
        return mock_function

# Create the main wrapper instance
_galil_wrapper = None

def get_galil_wrapper() -> GalilLibWrapper:
    """Get the global Galil wrapper instance"""
    global _galil_wrapper
    if _galil_wrapper is None:
        _galil_wrapper = GalilLibWrapper()
    return _galil_wrapper

# Python wrapper class for compatibility
class py:
    """Python wrapper class for gclib compatibility"""
    
    def __init__(self):
        self.wrapper = get_galil_wrapper()
        self.connected = False
        self.connection_string = ""
    
    def GOpen(self, connection_string: str) -> int:
        """Open connection"""
        result = self.wrapper.GOpen(connection_string)
        if result == 0:
            self.connected = True
            self.connection_string = connection_string
        return result
    
    def GClose(self) -> int:
        """Close connection"""
        result = self.wrapper.GClose()
        self.connected = False
        return result
    
    def GCommand(self, command: str) -> str:
        """Send command"""
        return self.wrapper.GCommand(command)
    
    def GInfo(self) -> str:
        """Get info"""
        return self.wrapper.GInfo()

# Export the wrapper
py = py
