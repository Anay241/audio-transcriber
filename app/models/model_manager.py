# app/models/model_manager.py

import os
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable, List
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages Whisper model downloads, loading, and configuration."""
    
    def __init__(self):
        """Initialize the ModelManager with model configurations and paths."""
        # Create models directory in user's home directory
        self.models_dir = Path.home() / '.audio_transcriber' / 'models'
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration file path for storing model settings
        self.config_file = self.models_dir / 'config.json'
        
        # Load existing configuration or create default
        self.config = self._load_config()
        
        # Currently loaded model in memory
        self._loaded_model = None
        self._loaded_model_name = None
        self._last_used_time = None
        
        # Model timeout - unload after 5 minutes of inactivity to save memory
        self.model_timeout = 300
        
        # Available faster-whisper models with their characteristics
        # Based on the Systran faster-whisper collection from HuggingFace
        self.available_models = {
            'tiny': {
                'size_mb': 39,
                'speed': 'Very Fast',
                'accuracy': 'Basic',
                'description': 'Fastest model, basic accuracy'
            },
            'tiny.en': {
                'size_mb': 39,
                'speed': 'Very Fast', 
                'accuracy': 'Basic',
                'description': 'English-only tiny model'
            },
            'base': {
                'size_mb': 74,
                'speed': 'Fast',
                'accuracy': 'Good',
                'description': 'Good balance of speed and accuracy'
            },
            'base.en': {
                'size_mb': 74,
                'speed': 'Fast',
                'accuracy': 'Good', 
                'description': 'English-only base model'
            },
            'small': {
                'size_mb': 244,
                'speed': 'Medium',
                'accuracy': 'Better',
                'description': 'Better accuracy, moderate speed'
            },
            'small.en': {
                'size_mb': 244,
                'speed': 'Medium',
                'accuracy': 'Better',
                'description': 'English-only small model'
            },
            'medium': {
                'size_mb': 769,
                'speed': 'Slow',
                'accuracy': 'Very Good',
                'description': 'High accuracy, slower processing'
            },
            'medium.en': {
                'size_mb': 769,
                'speed': 'Slow',
                'accuracy': 'Very Good',
                'description': 'English-only medium model'
            },
            'large-v2': {
                'size_mb': 1550,
                'speed': 'Very Slow',
                'accuracy': 'Excellent',
                'description': 'Highest accuracy, slowest processing'
            },
            'large-v3': {
                'size_mb': 1550,
                'speed': 'Very Slow', 
                'accuracy': 'Excellent',
                'description': 'Latest large model with best accuracy'
            }
        }
        
        # Set default model if none configured (base is good balance)
        if not self.current_model:
            self.current_model = 'base'
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file or create default."""
        default_config = {
            'current_model': None,
            'downloaded_models': [],
            'model_paths': {}
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Ensure all required keys exist with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def _save_config(self) -> None:
        """Save current configuration to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    @property
    def current_model(self) -> Optional[str]:
        """Get the currently selected model name."""
        return self.config.get('current_model')
    
    @current_model.setter
    def current_model(self, model_name: str) -> None:
        """Set the current model and save to config."""
        self.config['current_model'] = model_name
        self._save_config()
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get all available models and their information."""
        return self.available_models.copy()
    
    def check_model_exists(self, model_name: str) -> bool:
        """Check if a model is downloaded and ready to use."""
        if model_name not in self.available_models:
            return False
        
        # Check if model is marked as downloaded in config
        if model_name in self.config.get('downloaded_models', []):
            # For faster-whisper, the model gets cached automatically
            # We just need to verify it can be loaded
            try:
                # Try to create model instance to verify it exists
                test_model = WhisperModel(model_name, device="cpu", compute_type="int8")
                del test_model  # Clean up immediately
                return True
            except Exception as e:
                logger.warning(f"Model {model_name} marked as downloaded but failed to load: {e}")
                # Remove from downloaded list if it can't be loaded
                self.config['downloaded_models'].remove(model_name)
                if model_name in self.config.get('model_paths', {}):
                    del self.config['model_paths'][model_name]
                self._save_config()
                return False
        
        return False
    
    def check_model_location(self, model_name: Optional[str]) -> Tuple[bool, Optional[Path]]:
        """Check if a model exists and return its location."""
        if not model_name:
            return False, None
        
        exists = self.check_model_exists(model_name)
        # For faster-whisper, models are cached in the library's cache directory
        # We don't need to manage the exact location
        location = self.models_dir if exists else None
        return exists, location
    
    def check_disk_space(self, model_name: str) -> Tuple[bool, str]:
        """Check if there's enough disk space for the model."""
        if model_name not in self.available_models:
            return False, f"Unknown model: {model_name}"
        
        required_mb = self.available_models[model_name]['size_mb']
        required_bytes = required_mb * 1024 * 1024
        
        try:
            # Get available disk space
            stat = shutil.disk_usage(self.models_dir)
            available_bytes = stat.free
            
            # Add 20% buffer for safety
            if available_bytes < required_bytes * 1.2:
                available_mb = available_bytes // (1024 * 1024)
                return False, f"Insufficient disk space. Need {required_mb}MB, have {available_mb}MB"
            
            return True, "Sufficient disk space available"
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return False, f"Could not check disk space: {e}"
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Download and prepare a model for use.
        
        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates (0.0 to 1.0)
            
        Returns:
            Tuple of (success, message)
        """
        if model_name not in self.available_models:
            return False, f"Unknown model: {model_name}"
        
        try:
            logger.info(f"Starting download of model: {model_name}")
            
            if progress_callback:
                progress_callback(0.1)
            
            # Initialize model - this triggers download if not cached
            # Using faster-whisper with optimal settings for CPU
            logger.info(f"Downloading faster-whisper model: {model_name}")
            model = WhisperModel(
                model_name, 
                device="cpu", 
                compute_type="int8",  # Optimized for CPU performance
                download_root=None    # Use default cache location
            )
            
            if progress_callback:
                progress_callback(0.6)
            
            # Test the model works by doing a quick transcription test
            logger.info("Testing model functionality...")
            import numpy as np
            import tempfile
            import wave
            
            # Create 1 second of silence for testing
            test_audio = np.zeros(16000, dtype=np.int16)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Write test audio to temporary file
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(test_audio.tobytes())
                
                if progress_callback:
                    progress_callback(0.8)
                
                # Test transcription - this will be empty for silence but verifies model works
                segments, _ = model.transcribe(temp_path)
                list(segments)  # Consume the generator to ensure it works
                
                # Clean up test file
                os.unlink(temp_path)
            
            if progress_callback:
                progress_callback(1.0)
            
            # Update configuration to mark model as downloaded
            if model_name not in self.config.get('downloaded_models', []):
                self.config.setdefault('downloaded_models', []).append(model_name)
            
            # Set as active model
            self.set_active_model(model_name)
            
            logger.info(f"Successfully downloaded and tested model: {model_name}")
            return True, f"Model {model_name} downloaded successfully"
            
        except Exception as e:
            logger.error(f"Error downloading model {model_name}: {e}")
            return False, f"Failed to download model: {str(e)}"
    
    def set_active_model(self, model_name: str) -> None:
        """Set the active model and save configuration."""
        if model_name in self.available_models:
            self.current_model = model_name
            logger.info(f"Set active model to: {model_name}")
        else:
            logger.error(f"Cannot set unknown model as active: {model_name}")
    
    def get_model(self) -> WhisperModel:
        """
        Get the currently loaded model, loading it if necessary.
        
        Returns:
            Loaded WhisperModel instance
        """
        current_time = time.time()
        
        # Check if we need to load a different model
        if (self._loaded_model is None or 
            self._loaded_model_name != self.current_model):
            
            self._load_model()
        
        # Update last used time for timeout tracking
        self._last_used_time = current_time
        
        return self._loaded_model
    
    def _load_model(self) -> None:
        """Load the current model into memory."""
        if not self.current_model:
            raise RuntimeError("No model selected")
        
        if not self.check_model_exists(self.current_model):
            raise RuntimeError(f"Model {self.current_model} is not downloaded")
        
        try:
            logger.info(f"Loading model: {self.current_model}")
            
            # Unload existing model first to free memory
            if self._loaded_model is not None:
                self.unload_model()
            
            # Load the new model with optimized settings
            self._loaded_model = WhisperModel(
                self.current_model,
                device="cpu",
                compute_type="int8"  # Balanced performance and accuracy
            )
            self._loaded_model_name = self.current_model
            self._last_used_time = time.time()
            
            logger.info(f"Successfully loaded model: {self.current_model}")
            
        except Exception as e:
            logger.error(f"Error loading model {self.current_model}: {e}")
            self._loaded_model = None
            self._loaded_model_name = None
            raise
    
    def unload_model(self) -> None:
        """Unload the current model from memory to free resources."""
        if self._loaded_model is not None:
            logger.info(f"Unloading model: {self._loaded_model_name}")
            
            # Delete the model and clear references
            del self._loaded_model
            self._loaded_model = None
            self._loaded_model_name = None
            self._last_used_time = None
            
            # Force garbage collection to free memory
            import gc
            gc.collect()
            
            logger.info("Model unloaded successfully")
    
    def check_timeout(self) -> None:
        """Check if the model should be unloaded due to inactivity timeout."""
        if (self._loaded_model is not None and 
            self._last_used_time is not None and
            time.time() - self._last_used_time > self.model_timeout):
            
            logger.info("Model timeout reached, unloading model to save memory")
            self.unload_model()
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        if model_name in self.available_models:
            info = self.available_models[model_name].copy()
            info['downloaded'] = self.check_model_exists(model_name)
            info['active'] = (model_name == self.current_model)
            return info
        return None
    
    def list_downloaded_models(self) -> List[str]:
        """Get a list of all downloaded models."""
        downloaded = []
        for model_name in self.config.get('downloaded_models', []):
            if self.check_model_exists(model_name):
                downloaded.append(model_name)
        return downloaded
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a downloaded model (marks as not downloaded)."""
        if not self.check_model_exists(model_name):
            return False
        
        try:
            # Unload if currently loaded
            if self._loaded_model_name == model_name:
                self.unload_model()
            
            # Update configuration to mark as not downloaded
            if model_name in self.config.get('downloaded_models', []):
                self.config['downloaded_models'].remove(model_name)
            
            if model_name in self.config.get('model_paths', {}):
                del self.config['model_paths'][model_name]
            
            # If this was the current model, reset to default
            if self.current_model == model_name:
                self.current_model = 'base'
            
            self._save_config()
            
            logger.info(f"Successfully removed model from config: {model_name}")
            logger.info("Note: Model files may still be cached by faster-whisper")
            return True
            
        except Exception as e:
            logger.error(f"Error removing model {model_name}: {e}")
            return False

