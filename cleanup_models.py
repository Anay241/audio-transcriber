#!/usr/bin/env python3

import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_whisper_models():
    """Clean up unused Whisper models from cache."""
    # Get Whisper cache directory
    cache_dir = os.path.expanduser("~/.cache/whisper")
    
    # List of models to remove
    models_to_remove = ["base.pt", "tiny.pt", "small.pt"]
    
    logger.info(f"Checking Whisper cache directory: {cache_dir}")
    
    if not os.path.exists(cache_dir):
        logger.info("No Whisper cache directory found.")
        return
    
    # Remove each model if it exists
    for model in models_to_remove:
        model_path = os.path.join(cache_dir, model)
        if os.path.exists(model_path):
            try:
                size_mb = os.path.getsize(model_path) / (1024 * 1024)
                os.remove(model_path)
                logger.info(f"Removed {model} (freed {size_mb:.1f}MB)")
            except Exception as e:
                logger.error(f"Error removing {model}: {e}")
        else:
            logger.info(f"{model} not found in cache")
    
    logger.info("Cleanup complete!")

if __name__ == "__main__":
    cleanup_whisper_models() 