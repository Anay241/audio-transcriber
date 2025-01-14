import os
import sys
import logging
from setup_manager import SetupManager
from model_manager import ModelManager

# Log file paths
log_file = 'transcriber.log'
error_log_file = 'transcriber.error.log'

def cleanup_logs():
    """Clean up all log files."""
    try:
        # List of log files to clean
        log_files = [log_file, error_log_file]
        
        for file in log_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"Cleaned up log file: {file}")  # Use print since logger isn't set up yet
                
    except Exception as e:
        print(f"Error cleaning up log files: {e}")

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
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# File handler for error logs only
error_file_handler = logging.FileHandler(error_log_file)
error_file_handler.setLevel(logging.ERROR)  # Only ERROR and CRITICAL
error_file_handler.setFormatter(formatter)
logger.addHandler(error_file_handler)

# Get logger for this module
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
                cleanup_logs()
                sys.exit(1)
        
        # Import and run audio capture
        logger.info("Starting audio transcription...")
        import audio_capture
        audio_capture.main()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        cleanup_logs()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        cleanup_logs()
        sys.exit(1)

if __name__ == "__main__":
    main() 