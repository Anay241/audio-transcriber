import os
import logging
import shutil
import psutil
from pathlib import Path
from typing import Optional, Callable
from faster_whisper import WhisperModel

# Set up logging
logger = logging.getLogger(__name__)

class ModelManager:
    """Manages Whisper model files and configuration."""
    
    # Default paths
    APP_NAME = "AudioTranscriber"
    CONFIG_FILE = "config.json"
    
    # Available models and their characteristics
    AVAILABLE_MODELS = {
        "tiny": {
            "size_mb": 150,
            "speed": "Fastest",
            "accuracy": "Basic",
            "description": "Best for quick tests and weak hardware"
        },
        "base": {
            "size_mb": 400,
            "speed": "Very Fast",
            "accuracy": "Good",
            "description": "Good balance for basic transcription"
        },
        "small": {
            "size_mb": 900,
            "speed": "Fast",
            "accuracy": "Better",
            "description": "Recommended for most users"
        },
        "medium": {
            "size_mb": 3000,
            "speed": "Moderate",
            "accuracy": "Very Good",
            "description": "Best quality for common hardware"
        },
        "large": {
            "size_mb": 6000,
            "speed": "Slow",
            "accuracy": "Best",
            "description": "Highest quality, requires powerful hardware"
        }
    }
    
    def __init__(self):
        """Initialize the ModelManager."""
        # Set up application directories
        self.app_support_dir = Path.home() / "Library" / "Application Support" / self.APP_NAME
        self.model_dir = self.app_support_dir / "models"
        self.config_dir = self.app_support_dir / "config"
        self.config_file = self.config_dir / self.CONFIG_FILE
        
        # Cache directory for faster-whisper
        self.cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        
        # Ensure directories exist
        self._setup_directories()
        
        # Load or initialize current model
        self.current_model = self._load_config().get('current_model', None)
        
    def _setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        try:
            self.app_support_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Application directory setup at: {self.app_support_dir}")
            
            self.model_dir.mkdir(exist_ok=True)
            logger.info(f"Model directory setup at: {self.model_dir}")
            
            self.config_dir.mkdir(exist_ok=True)
            logger.info(f"Config directory setup at: {self.config_dir}")
            
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise
            
    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                import json
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        return {}
        
    def _save_config(self, config: dict) -> None:
        """Save configuration to file."""
        try:
            import json
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
    def get_cache_model_path(self, model_name: str) -> Path:
        """Get the path where the model would be in cache."""
        return self.cache_dir / f"faster-whisper-{model_name}"
    
    def get_app_model_path(self, model_name: str) -> Path:
        """Get the path where the model would be in our app directory."""
        return self.model_dir / model_name
    
    def check_model_location(self, model_name: str) -> tuple[bool, str]:
        """
        Check if a model exists and where it's located.
        Returns: (exists: bool, location: str)
        location can be 'cache', 'app', or 'none'
        """
        # Handle case when no model is selected yet
        if model_name is None:
            return False, 'none'
            
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model name: {model_name}")
            
        cache_path = self.get_cache_model_path(model_name)
        app_path = self.get_app_model_path(model_name)
        
        if cache_path.exists():
            return True, 'cache'
        elif app_path.exists():
            return True, 'app'
        else:
            return False, 'none'
    
    def check_disk_space(self, model_name: str) -> tuple[bool, str]:
        """
        Check if there's enough disk space for the model.
        Returns: (has_space: bool, message: str)
        """
        try:
            model_size = self.AVAILABLE_MODELS[model_name]["size_mb"] * 1024 * 1024  # Convert MB to bytes
            # Get free space in cache directory (where faster-whisper downloads)
            free_space = psutil.disk_usage(self.cache_dir.parent).free
            
            # Add 20% buffer for safety
            required_space = model_size * 1.2
            
            if free_space >= required_space:
                return True, f"Sufficient disk space available ({free_space // (1024*1024)} MB free)"
            else:
                return False, f"Insufficient disk space. Need {required_space // (1024*1024)} MB, but only {free_space // (1024*1024)} MB available"
                
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return False, f"Error checking disk space: {e}"
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable[[float], None]] = None) -> tuple[bool, str]:
        """Download a model using faster-whisper."""
        if model_name not in self.AVAILABLE_MODELS:
            return False, f"Invalid model name: {model_name}"
        
        try:
            logger.info(f"Starting download of model: {model_name}")
            # This will automatically download the model
            WhisperModel(model_name)
            
            # Check if download was successful
            exists, location = self.check_model_location(model_name)
            if exists:
                logger.info(f"Model {model_name} successfully downloaded to {location}")
                return True, f"Model downloaded successfully to {location}"
            else:
                logger.error("Model download completed but model not found in expected location")
                return False, "Model download failed: Model not found after download"
                
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            return False, f"Error downloading model: {e}"
    
    def get_model_path(self) -> Path:
        """Get the path where current model files are stored."""
        exists, location = self.check_model_location(self.current_model)
        if location == 'cache':
            return self.get_cache_model_path(self.current_model)
        else:
            return self.get_app_model_path(self.current_model)
    
    def get_available_models(self) -> dict:
        """Get information about all available models."""
        return self.AVAILABLE_MODELS
    
    def get_model_info(self, model_name: str) -> dict:
        """Get information about a specific model."""
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Unknown model: {model_name}. Available models: {list(self.AVAILABLE_MODELS.keys())}")
        return self.AVAILABLE_MODELS[model_name]
    
    def set_active_model(self, model_name: str) -> tuple[bool, str]:
        """Set the active model to use for transcription."""
        if model_name not in self.AVAILABLE_MODELS:
            return False, f"Invalid model name: {model_name}"
        
        exists, location = self.check_model_location(model_name)
        if exists:
            self.current_model = model_name
            # Save the choice to config
            config = self._load_config()
            config['current_model'] = model_name
            self._save_config(config)
            
            logger.info(f"Switched to model '{model_name}' from {location}")
            return True, f"Successfully switched to model '{model_name}'"
        else:
            return False, f"Model '{model_name}' not found. Please download it first" 