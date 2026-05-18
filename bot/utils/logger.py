"""
Logging configuration for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import colorlog


def setup_logger(name: str = "auto_anime", log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Setup colored logger with file and console handlers"""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # File handler (with date in filename)
    if not log_file:
        log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    else:
        log_file = Path(log_file)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Colored formatter for console
    console_format = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_format)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


class AdminLogFilter(logging.Filter):
    """Filter for admin logs"""
    def __init__(self, level: int = logging.ERROR):
        super().__init__()
        self.level = level
    
    def filter(self, record):
        return record.levelno >= self.level


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return setup_logger(name)


class LoggerContext:
    """Context manager for temporary log level changes"""
    
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)
