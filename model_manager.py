import os
import logging
import shutil
import psutil
import platform
from pathlib import Path
from typing import Optional, Callable, Dict
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
            "description": "Best for quick tests and weak hardware",
            "optimal_settings": {
                "cpu_threads": 3,
                "num_workers": 1,
                "compute_type": "float16",
                "memory_threshold": 0.6  # 30% memory threshold
            }
        },
        "base": {
            "size_mb": 400,
            "speed": "Very Fast",
            "accuracy": "Good",
            "description": "Good balance for basic transcription",
            "optimal_settings": {
                "cpu_threads": 4,
                "num_workers": 1,
                "compute_type": "float16",
                "memory_threshold": 0.6  # 40% memory threshold
            }
        },
        "small": {
            "size_mb": 900,
            "speed": "Fast",
            "accuracy": "Better",
            "description": "Recommended for most users",
            "optimal_settings": {
                "cpu_threads": 4,
                "num_workers": 1,
                "compute_type": "float16",
                "memory_threshold": 0.6  # 50% memory threshold
            }
        },
        "medium": {
            "size_mb": 3000,
            "speed": "Moderate",
            "accuracy": "Very Good",
            "description": "Best quality for common hardware",
            "optimal_settings": {
                "cpu_threads": 6,
                "num_workers": 1,
                "compute_type": "float16",
                "memory_threshold": 0.75  # 60% memory threshold
            }
        },
        "large": {
            "size_mb": 6000,
            "speed": "Slow",
            "accuracy": "Best",
            "description": "Highest quality, requires powerful hardware",
            "optimal_settings": {
                "cpu_threads": 4,
                "num_workers": 1,
                "compute_type": "int8",
                "memory_threshold": 0.8  # 70% memory threshold
            }
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
        
        # System capabilities
        self.system_info = self.get_system_info()
        logger.info(f"System capabilities detected: {self.system_info}")
        
        # Performance monitoring
        self.performance_stats = {
            "load_times": [],
            "memory_usage": [],
            "cpu_usage": []
        }
        
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
    
    def check_memory_status(self) -> tuple[bool, float]:
        """
        Check current memory status.
        
        Returns:
            Tuple of (is_memory_ok: bool, memory_usage: float)
            - is_memory_ok: True if memory usage is within safe limits
            - memory_usage: Current memory usage as a percentage
        """
        try:
            memory = psutil.virtual_memory()
            memory_usage = memory.percent / 100.0  # Convert to decimal
            
            logger.debug(f"Current memory usage: {memory_usage:.1%}")
            return True, memory_usage
            
        except Exception as e:
            logger.warning(f"Error checking memory status: {e}")
            return False, 0.0

    def get_optimal_settings(self, model_name: str) -> Dict:
        """
        Get optimal model settings based on model type and system status.
        
        Args:
            model_name: Name of the model to get settings for
            
        Returns:
            Dict containing optimized settings for model loading
        """
        try:
            # Get model info and optimal settings
            model_info = self.AVAILABLE_MODELS[model_name]
            optimal_settings = model_info["optimal_settings"]
            
            # Check memory status
            memory_ok, memory_usage = self.check_memory_status()
            
            # Base settings with optimal values
            settings = {
                "device": "cpu",
                "compute_type": optimal_settings["compute_type"],
                "cpu_threads": optimal_settings["cpu_threads"],
                "num_workers": optimal_settings["num_workers"]
            }
            
            # If memory usage is high, adjust settings
            if memory_ok and memory_usage > optimal_settings["memory_threshold"]:
                logger.info(f"High memory usage ({memory_usage:.1%}), adjusting settings")
                
                # Reduce threads if memory is tight
                if settings["cpu_threads"] > 3:
                    settings["cpu_threads"] -= 1
                
                # Use int8 for better memory efficiency
                settings["compute_type"] = "int8"
            
            logger.info(f"Using settings for {model_name}: {settings}")
            return settings
            
        except Exception as e:
            logger.warning(f"Error determining optimal settings: {e}")
            # Return conservative defaults
            return {
                "device": "cpu",
                "compute_type": "int8",
                "cpu_threads": 1,
                "num_workers": 1
            }

    def monitor_performance(self, operation: str):
        """
        Decorator to monitor performance of model operations.
        
        Args:
            operation: Name of the operation being monitored
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                start_cpu = psutil.cpu_percent()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Calculate metrics
                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    end_cpu = psutil.cpu_percent()
                    
                    # Store performance data
                    self.performance_stats["load_times"].append(end_time - start_time)
                    self.performance_stats["memory_usage"].append(end_memory - start_memory)
                    self.performance_stats["cpu_usage"].append(end_cpu - start_cpu)
                    
                    # Log performance data
                    logger.info(f"Performance stats for {operation}:")
                    logger.info(f"  Time taken: {end_time - start_time:.2f} seconds")
                    logger.info(f"  Memory change: {end_memory - start_memory:.1f} MB")
                    logger.info(f"  CPU usage: {end_cpu - start_cpu:.1f}%")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error during {operation}: {e}")
                    raise
                    
            return wrapper
        return decorator

    @staticmethod
    def performance_monitor(operation: str):
        """
        Static decorator for monitoring performance.
        
        Args:
            operation: Name of the operation being monitored
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                start_cpu = psutil.cpu_percent()
                
                try:
                    result = func(self, *args, **kwargs)
                    
                    # Calculate metrics
                    end_time = time.time()
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    end_cpu = psutil.cpu_percent()
                    
                    # Store performance data
                    self.performance_stats["load_times"].append(end_time - start_time)
                    self.performance_stats["memory_usage"].append(end_memory - start_memory)
                    self.performance_stats["cpu_usage"].append(end_cpu - start_cpu)
                    
                    # Log performance data
                    logger.info(f"Performance stats for {operation}:")
                    logger.info(f"  Time taken: {end_time - start_time:.2f} seconds")
                    logger.info(f"  Memory change: {end_memory - start_memory:.1f} MB")
                    logger.info(f"  CPU usage: {end_cpu - start_cpu:.1f}%")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error during {operation}: {e}")
                    raise
                    
            return wrapper
        return decorator

    @performance_monitor("model_loading")
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
            
            # Get optimized settings
            settings = self.get_optimal_settings(model_name)
            
            # Load the model with optimized settings
            try:
                self.model = WhisperModel(
                    model_name,
                    device=settings["device"],
                    compute_type=settings["compute_type"],
                    cpu_threads=settings["cpu_threads"],
                    num_workers=settings["num_workers"],
                    download_root=str(self.cache_dir)
                )
                self.last_use_time = time.time()
                logger.info(f"Model {model_name} loaded successfully with settings: {settings}")
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

    def get_system_info(self) -> Dict:
        """
        Get system capabilities for optimization.
        
        Returns:
            Dict containing system information:
            - cpu_cores: Number of physical CPU cores
            - memory_gb: Total system memory in GB
            - processor: Processor type
            - is_apple_silicon: Whether running on Apple Silicon
        """
        try:
            cpu_count = psutil.cpu_count(logical=False)  # Physical CPU cores
            total_memory = psutil.virtual_memory().total / (1024 * 1024 * 1024)  # GB
            processor = platform.processor()
            is_apple_silicon = 'arm' in processor.lower()
            
            system_info = {
                "cpu_cores": cpu_count or 2,  # Fallback to 2 if detection fails
                "memory_gb": round(total_memory, 1),
                "processor": processor,
                "is_apple_silicon": is_apple_silicon
            }
            
            logger.debug(f"Detected system capabilities: {system_info}")
            return system_info
            
        except Exception as e:
            logger.warning(f"Error getting system info: {e}")
            # Return conservative defaults if detection fails
            return {
                "cpu_cores": 2,
                "memory_gb": 8,
                "processor": "unknown",
                "is_apple_silicon": False
            } 

    def get_performance_summary(self) -> Dict:
        """
        Get a summary of performance statistics.
        
        Returns:
            Dict containing average load times, memory usage, and CPU usage
        """
        if not self.performance_stats["load_times"]:
            return {
                "avg_load_time": 0,
                "avg_memory_usage": 0,
                "avg_cpu_usage": 0
            }
            
        return {
            "avg_load_time": sum(self.performance_stats["load_times"]) / len(self.performance_stats["load_times"]),
            "avg_memory_usage": sum(self.performance_stats["memory_usage"]) / len(self.performance_stats["memory_usage"]),
            "avg_cpu_usage": sum(self.performance_stats["cpu_usage"]) / len(self.performance_stats["cpu_usage"])
        } 

    def get_audio_settings(self, audio_duration: float) -> Dict:
        """
        Determine optimal settings based on audio length.
        
        Args:
            audio_duration: Length of audio in seconds
            
        Returns:
            Dict containing audio-specific settings
        """
        try:
            if not self.current_model:
                raise ValueError("No model selected")
                
            # Get base settings
            settings = self.get_optimal_settings(self.current_model)
            
            # Adjust settings based on audio length
            if audio_duration > 60:  # Long audio (>1 minute)
                logger.info("Long audio detected, optimizing for memory efficiency")
                settings["compute_type"] = "int8"  # Use int8 for longer audio
                if settings["cpu_threads"] > 4:
                    settings["cpu_threads"] = 4  # Reduce threads for longer audio
                    
            elif audio_duration < 10:  # Short audio (<10 seconds)
                logger.info("Short audio detected, optimizing for speed")
                if self.system_info["memory_gb"] >= 8:  # If enough memory
                    settings["compute_type"] = "float16"  # Use float16 for better accuracy
                    
            logger.info(f"Audio-optimized settings: {settings}")
            return settings
            
        except Exception as e:
            logger.error(f"Error getting audio settings: {e}")
            return self.get_optimal_settings(self.current_model)

    def prepare_model_for_audio(self, audio_duration: float = 0) -> None:
        """
        Prepare model with optimal settings for audio length.
        
        Args:
            audio_duration: Length of audio in seconds
        """
        try:
            if self.model is None:
                logger.info("Loading model for first time")
                self.get_model()  # Initial load with default settings
                return
                
            # Get current memory usage
            _, memory_usage = self.check_memory_status()
            
            # Check if we need to reload with different settings
            current_settings = self.get_optimal_settings(self.current_model)
            audio_settings = self.get_audio_settings(audio_duration)
            
            # Decide if reload is needed
            needs_reload = (
                current_settings["compute_type"] != audio_settings["compute_type"] or
                current_settings["cpu_threads"] != audio_settings["cpu_threads"] or
                memory_usage > 0.85  # 85% memory usage threshold
            )
            
            if needs_reload:
                logger.info("Reloading model with audio-optimized settings")
                self.unload_model()
                
                # Load with audio-optimized settings
                self.model = WhisperModel(
                    self.current_model,
                    device="cpu",
                    compute_type=audio_settings["compute_type"],
                    cpu_threads=audio_settings["cpu_threads"],
                    num_workers=audio_settings["num_workers"],
                    download_root=str(self.cache_dir)
                )
                logger.info("Model reloaded with optimized settings")
                
        except Exception as e:
            logger.error(f"Error preparing model: {e}")
            # Fallback to regular model loading if preparation fails
            if self.model is None:
                self.get_model() 