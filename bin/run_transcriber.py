#bin/run_transcriber.py

import sys
import logging
import signal
import atexit

from utils.logger import setup_logging
from setup.setup_manager import SetupManager
from app.models.model_manager import ModelManager
from app.ui.menu_bar import main as run_app

# Set up logging
logger = setup_logging()
logger = logging.getLogger(__name__)

# Global reference to the app for signal handlers
app_instance = None

def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown."""
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    if app_instance:
        try:
            app_instance.quit_app(None)
        except Exception as e:
            logger.error(f"Error during signal-triggered shutdown: {e}")
    sys.exit(0)

def main():
    """Main entry point for the AudioTranscriber application."""
    global app_instance
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        model_manager = ModelManager()
        
        # Check if we have a model selected and if it exists
        exists, location = model_manager.check_model_location(model_manager.current_model)
        
        # If no model exists or none is selected, run setup
        if not exists:
            logger.info("No model found or no model selected. Starting setup process...")
            setup_manager = SetupManager()
            if not setup_manager.run_setup():
                logger.error("Setup was cancelled or failed. Exiting.")
                sys.exit(1)
        
        # Run the audio transcriber application
        logger.info("Starting audio transcription...")
        app_instance = run_app()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        if app_instance:
            app_instance.quit_app(None)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 