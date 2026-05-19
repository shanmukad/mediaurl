"""
Centralized logging configuration for media platform automation.
Ensures consistent logging across all modules.
"""

import os
import logging
from pathlib import Path


def setup_logging(module_name, log_level=logging.INFO):
    """
    Setup centralized logging for a module.
    
    Args:
        module_name: Name of the module (usually __name__)
        log_level: Logging level (default: INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get logger for this module
    logger = logging.getLogger(module_name)
    logger.setLevel(log_level)
    
    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Create logs directory
    logs_dir = Path(__file__).parent.parent / "runtime" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Log file path
    log_file = logs_dir / "automation.log"
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    
    # Create console handler (also log to console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger (avoid duplicate logs)
    logger.propagate = False
    
    return logger


def get_logger(module_name):
    """
    Get existing logger for a module (if already configured).
    
    Args:
        module_name: Name of the module
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(module_name)