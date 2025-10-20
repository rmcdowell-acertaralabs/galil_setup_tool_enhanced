"""
Logging Utilities for Galil Setup Tool

Provides comprehensive logging functionality for the application.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Callable, Any
from pathlib import Path

class LoggingUtils:
    """Comprehensive logging utilities for the Galil Setup Tool"""
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        """
        Initialize logging utilities
        
        Args:
            callback: Optional callback function for real-time log messages
        """
        self.callback = callback
        self.logger = self._setup_logger()
        self.log_file = self._setup_log_file()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup the main application logger"""
        logger = logging.getLogger('galil_setup_tool')
        logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_log_file(self) -> Optional[Path]:
        """Setup log file for persistent logging"""
        try:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f'galil_setup_{timestamp}.log'
            
            # File handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            return log_file
        except Exception as e:
            self.logger.warning(f"Could not setup log file: {e}")
            return None
    
    def log_info(self, message: str) -> None:
        """Log an info message"""
        self.logger.info(message)
        self._callback_log(message)
    
    def log_debug(self, message: str) -> None:
        """Log a debug message"""
        self.logger.debug(message)
        self._callback_log(f"[DEBUG] {message}")
    
    def log_warning(self, message: str) -> None:
        """Log a warning message"""
        self.logger.warning(message)
        self._callback_log(f"[WARNING] {message}")
    
    def log_error(self, message: str) -> None:
        """Log an error message"""
        self.logger.error(message)
        self._callback_log(f"[ERROR] {message}")
    
    def log_critical(self, message: str) -> None:
        """Log a critical message"""
        self.logger.critical(message)
        self._callback_log(f"[CRITICAL] {message}")
    
    def log_command(self, command: str, response: str = "") -> None:
        """Log a Galil command and response"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        if response:
            message = f"[{timestamp}] Command: {command} -> Response: {response}"
        else:
            message = f"[{timestamp}] Command: {command}"
        
        self.logger.info(message)
        self._callback_log(message)
    
    def log_connection(self, event: str, details: str = "") -> None:
        """Log connection events"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] Connection: {event}"
        if details:
            message += f" - {details}"
        
        self.logger.info(message)
        self._callback_log(message)
    
    def log_motor_setup(self, axis: str, step: str, details: str = "") -> None:
        """Log motor setup events"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] Motor Setup - Axis {axis}: {step}"
        if details:
            message += f" - {details}"
        
        self.logger.info(message)
        self._callback_log(message)
    
    def log_test_result(self, test_name: str, result: str, details: str = "") -> None:
        """Log test results"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] Test: {test_name} - {result}"
        if details:
            message += f" - {details}"
        
        self.logger.info(message)
        self._callback_log(message)
    
    def _callback_log(self, message: str) -> None:
        """Send message to callback if available"""
        if self.callback:
            try:
                self.callback(message)
            except Exception as e:
                self.logger.warning(f"Callback error: {e}")
    
    def set_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set or update the callback function"""
        self.callback = callback
    
    def get_log_file_path(self) -> Optional[str]:
        """Get the path to the current log file"""
        return str(self.log_file) if self.log_file else None
    
    def clear_log_file(self) -> None:
        """Clear the current log file"""
        if self.log_file and self.log_file.exists():
            try:
                self.log_file.unlink()
                self.logger.info("Log file cleared")
            except Exception as e:
                self.logger.error(f"Could not clear log file: {e}")
    
    def log_system_info(self) -> None:
        """Log system information"""
        import platform
        import sys
        
        self.log_info("=== System Information ===")
        self.log_info(f"Platform: {platform.platform()}")
        self.log_info(f"Python Version: {sys.version}")
        self.log_info(f"Working Directory: {os.getcwd()}")
        self.log_info(f"Log File: {self.get_log_file_path()}")
        self.log_info("=========================")
    
    def log_application_start(self) -> None:
        """Log application startup"""
        self.log_info("=== Galil Setup Tool Enhanced Started ===")
        self.log_system_info()
    
    def log_application_end(self) -> None:
        """Log application shutdown"""
        self.log_info("=== Galil Setup Tool Enhanced Shutdown ===")
    
    def log_exception(self, exception: Exception, context: str = "") -> None:
        """Log an exception with full traceback"""
        import traceback
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] Exception"
        if context:
            message += f" in {context}"
        message += f": {str(exception)}"
        
        self.logger.error(message)
        self.logger.debug(traceback.format_exc())
        self._callback_log(f"[ERROR] {message}")
    
    def log_performance(self, operation: str, duration: float, details: str = "") -> None:
        """Log performance metrics"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] Performance: {operation} took {duration:.3f}s"
        if details:
            message += f" - {details}"
        
        self.logger.info(message)
        self._callback_log(message)
    
    def log_validation_result(self, command: str, result: Any) -> None:
        """Log command validation results"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        if hasattr(result, 'valid'):
            status = "VALID" if result.valid else "INVALID"
            message = f"[{timestamp}] Validation: {command} - {status}"
            if hasattr(result, 'error_message') and result.error_message:
                message += f" - {result.error_message}"
            if hasattr(result, 'warning_message') and result.warning_message:
                message += f" - Warning: {result.warning_message}"
        else:
            message = f"[{timestamp}] Validation: {command} - {result}"
        
        self.logger.info(message)
        self._callback_log(message)
