"""
Cấu hình logging chung cho toàn bộ project.
Import file này ở đầu mỗi module để có logging thống nhất.
"""

import logging
import sys
from typing import Optional

# Format cho log messages
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: str = LOG_FORMAT
) -> None:
    """
    Cấu hình logging cho toàn bộ application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Đường dẫn file để ghi log (optional)
        format_string: Format string cho log messages
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt=DATE_FORMAT,
        handlers=handlers,
        force=True  # Override any existing configuration
    )

def get_logger(name: str) -> logging.Logger:
    """
    Lấy logger instance với tên cụ thể.
    
    Args:
        name: Tên của logger (thường là __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Cấu hình mặc định khi import module này
setup_logging()
