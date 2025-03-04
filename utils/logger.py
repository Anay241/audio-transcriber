import os
import sys
import logging
from pathlib import Path

# Get the project root directory (parent of the directory containing this file)
project_root = Path(__file__).resolve().parent.parent

# Log directory and file paths
log_dir = project_root / 'logs'
log_file = log_dir / 'transcriber.log'
error_log_file = log_dir / 'transcriber.error.log'

def cleanup_logs():
    """Clean up all log files."""
    try:
        # Ensure log directory exists
        log_dir.mkdir(exist_ok=True)
        
        # List of log files to clean
        log_files = [log_file, error_log_file]
        
        for file in log_files:
            if file.exists():
                file.unlink()
                print(f"Cleaned up log file: {file}")  # Use print since logger isn't set up yet
                
    except Exception as e:
        print(f"Error cleaning up log files: {e}")

def setup_logging():
    """Configure logging for the application."""
    # Clean old logs at startup
    cleanup_logs()

    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Formatter for all logs
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler (all logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler for all logs
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # File handler for error logs only
    error_file_handler = logging.FileHandler(str(error_log_file))
    error_file_handler.setLevel(logging.ERROR)  # Only ERROR and CRITICAL
    error_file_handler.setFormatter(formatter)
    logger.addHandler(error_file_handler)
    
    return logger 