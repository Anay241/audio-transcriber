import os
import logging
import shutil
import psutil
from pathlib import Path
from typing import Optional, Callable
from faster_whisper import WhisperModel
import time
import gc

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
        self.config_dir = self.app_support_dir / "config"
        self.config_file = self.config_dir / self.CONFIG_FILE
        
        # Cache directory for models
        self.cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        
        # Model state management
        self.model = None
        self.last_use_time = None
        self.model_timeout = 300  # 5 minutes
        
        # Ensure directories exist
        self._setup_directories()
        
        # Load or initialize current model
        self.current_model = self._load_config().get('current_model', None)
        
        logger.debug(f"ModelManager initialized with current model: {self.current_model}")
        
    def _setup_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        try:
            self.app_support_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Application directory setup at: {self.app_support_dir}")
            
            self.config_dir.mkdir(exist_ok=True)
            logger.info(f"Config directory setup at: {self.config_dir}")
            
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cache directory setup at: {self.cache_dir}")
            
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
            
    def get_model_location(self, model_name: str) -> Path:
        """Get the path where the model is stored."""
        return self.cache_dir / f"models--Systran--faster-whisper-{model_name}"
    
    def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists in the cache."""
        if model_name is None:
            return False
            
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model name: {model_name}")
            
        # Check for model files in any snapshot directory
        model_dir = self.get_model_location(model_name)
        if not model_dir.exists():
            return False
            
        # Look for model files in snapshot directories
        for snapshot_dir in (model_dir / "snapshots").glob("*"):
            if (snapshot_dir / "model.bin").exists():
                return True
        
        return False
    
    def get_model_path(self) -> Path:
        """Get the path where current model files are stored."""
        if self.current_model is None:
            raise ValueError("No model currently selected")
            
        model_dir = self.get_model_location(self.current_model)
        # Find the first snapshot directory containing model.bin
        for snapshot_dir in (model_dir / "snapshots").glob("*"):
            if (snapshot_dir / "model.bin").exists():
                return snapshot_dir
        
        raise FileNotFoundError(f"Model files not found for {self.current_model}")
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable[[float], None]] = None) -> tuple[bool, str]:
        """Download a model using faster-whisper."""
        if model_name not in self.AVAILABLE_MODELS:
            return False, f"Invalid model name: {model_name}"
        
        try:
            logger.info(f"Starting download of model: {model_name}")
            
            # This will automatically download the model to cache
            model = WhisperModel(model_name, download_root=str(self.cache_dir))
            
            # Give a longer delay for filesystem to update and verify
            import time
            attempts = 0
            while attempts < 5:  # Try for up to 5 seconds
                time.sleep(1)
                if self.check_model_exists(model_name):
                    logger.info(f"Model {model_name} successfully downloaded")
                    return True, "Model downloaded successfully"
                attempts += 1
            
            logger.error("Model download completed but model not found in expected location")
            return False, "Model download failed: Model not found after download"
                
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            return False, f"Error downloading model: {e}"
    
    def get_model_size_on_disk(self, model_name: str) -> Optional[int]:
        """Get the actual size of a downloaded model in bytes."""
        try:
            import glob
            total_size = 0
            model_path = self.get_model_location(model_name)
            if model_path.exists():
                for path in model_path.rglob('*'):
                    if path.is_file():
                        total_size += path.stat().st_size
                return total_size
        except Exception as e:
            logger.error(f"Error calculating model size: {e}")
        return None
    
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
        
        # Use check_model_location instead of check_model_exists
        exists, _ = self.check_model_location(model_name)
        if exists:
            self.current_model = model_name
            # Save the choice to config
            config = self._load_config()
            config['current_model'] = model_name
            self._save_config(config)
            
            logger.info(f"Switched to model '{model_name}'")
            return True, f"Successfully switched to model '{model_name}'"
        else:
            return False, f"Model '{model_name}' not found. Please download it first"
    
    def check_disk_space(self, model_name: str) -> tuple[bool, str]:
        """
        Check if there's enough disk space for the model.
        Returns: (has_space: bool, message: str)
        """
        try:
            model_size = self.AVAILABLE_MODELS[model_name]["size_mb"] * 1024 * 1024  # Convert MB to bytes
            # Get free space in cache directory
            free_space = psutil.disk_usage(self.cache_dir).free
            
            # Add 20% buffer for safety
            required_space = model_size * 1.2
            
            if free_space >= required_space:
                return True, f"Sufficient disk space available ({free_space // (1024*1024)} MB free)"
            else:
                return False, f"Insufficient disk space. Need {required_space // (1024*1024)} MB, but only {free_space // (1024*1024)} MB available"
                
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return False, f"Error checking disk space: {e}" 
    
    def check_model_location(self, model_name: str) -> tuple[bool, Optional[Path]]:
        """
        Check if a model exists and return its location.
        
        Args:
            model_name: Name of the model to check (tiny, base, small, medium, large)
            
        Returns:
            Tuple of (exists: bool, location: Optional[Path])
            - exists: True if model exists, False otherwise
            - location: Path to model if it exists, None otherwise
        """
        # Basic validation
        if model_name is None:
            logger.debug("Model name is None")
            return False, None
        
        if model_name not in self.AVAILABLE_MODELS:
            logger.debug(f"Invalid model name: {model_name}")
            return False, None
        
        # Get model directory
        model_dir = self.get_model_location(model_name)
        if not model_dir.exists():
            logger.debug(f"Model directory not found: {model_dir}")
            return False, None
        
        # Look for model files in snapshot directories
        snapshots_dir = model_dir / "snapshots"
        if not snapshots_dir.exists():
            logger.debug(f"Snapshots directory not found: {snapshots_dir}")
            return False, None
            
        # Find first snapshot with model.bin
        for snapshot_dir in snapshots_dir.glob("*"):
            if (snapshot_dir / "model.bin").exists():
                logger.debug(f"Found model at: {snapshot_dir}")
                return True, snapshot_dir
        
        logger.debug(f"No model.bin found in snapshots: {snapshots_dir}")
        return False, None
    
    def get_model(self) -> WhisperModel:
        """Get a loaded model ready for use. Loads the model if not loaded."""
        if self.model is None:
            logger.info("Loading Whisper model from cache...")
            
            # Get current model name
            model_name = self.current_model
            if not model_name:
                logger.error("No model selected in configuration")
                raise ValueError("No model selected in configuration")
            
            # Check if model exists
            exists, model_path = self.check_model_location(model_name)
            if not exists:
                logger.error(f"Model {model_name} not found")
                raise FileNotFoundError(f"Model {model_name} not found")
            
            # Load the model
            try:
                self.model = WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(self.cache_dir)
                )
                self.last_use_time = time.time()
                logger.info(f"Model {model_name} loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model {model_name}: {e}")
                self.model = None
                raise
        
        # Update last use time
        self.last_use_time = time.time()
        return self.model

    def check_timeout(self) -> None:
        """Check if model should be unloaded due to inactivity."""
        if (self.model is not None and 
            self.last_use_time is not None and 
            time.time() - self.last_use_time > self.model_timeout):
            logger.debug("Model timeout reached")
            self.unload_model()

    def unload_model(self) -> None:
        """Unload model from memory but keep files in cache."""
        if self.model is not None:
            logger.info("Unloading model from memory")
            self.model = None
            self.last_use_time = None
            gc.collect()
            logger.debug("Model unloaded successfully") 