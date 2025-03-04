import os
import logging
from pathlib import Path
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if the directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def get_file_size(file_path: str) -> Optional[int]:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Size of the file in bytes, or None if the file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return None
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return None

def delete_file(file_path: str) -> bool:
    """
    Delete a file if it exists.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file was deleted or didn't exist, False if there was an error
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False

def get_app_directory() -> Path:
    """
    Get the application directory for storing configuration and data.
    
    Returns:
        Path to the application directory
    """
    home = Path.home()
    app_dir = home / ".audio_transcriber"
    ensure_directory_exists(str(app_dir))
    return app_dir 