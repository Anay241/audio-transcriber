import os
import sys
import logging
from setup_manager import SetupManager
from model_manager import ModelManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('transcriber.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the AudioTranscriber application."""
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
        
        # Import and run audio capture (your existing main process)
        logger.info("Starting audio transcription...")
        import audio_capture
        audio_capture.main()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 