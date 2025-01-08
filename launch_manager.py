import os
import sys
import logging
import subprocess
from pathlib import Path
from model_manager import ModelManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('launcher.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class LaunchManager:
    """Manages the application launch process and modes."""
    
    def __init__(self):
        self.model_manager = ModelManager()
        
    def needs_setup(self) -> bool:
        """Check if the application needs first-time setup."""
        exists, _ = self.model_manager.check_model_location(self.model_manager.current_model)
        return not exists
        
    def run_setup_mode(self):
        """Run the application in setup mode (terminal visible)."""
        logger.info("Starting in setup mode...")
        try:
            # Import and run setup directly
            from setup_manager import SetupManager
            setup_manager = SetupManager()
            if setup_manager.run_setup():
                logger.info("Setup completed successfully. Launching in background mode...")
                self.run_background_mode()
            else:
                logger.error("Setup was cancelled or failed.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            sys.exit(1)
    
    def run_background_mode(self):
        """Run the application in background mode."""
        logger.info("Starting in background mode...")
        try:
            # Launch the app in a new process and detach from terminal
            cmd = [sys.executable, "-c", 
                  "import audio_capture; audio_capture.main()"]
            
            # Redirect output to log files
            with open("transcriber.log", "a") as log, \
                 open("transcriber.error.log", "a") as err:
                
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=err,
                    start_new_session=True  # Detach from terminal
                )
                
            logger.info(f"Application launched in background (PID: {process.pid})")
            # Exit the launcher process
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error in background mode: {e}")
            sys.exit(1)
    
    def launch(self):
        """Main launch method that determines and executes the appropriate launch mode."""
        try:
            if self.needs_setup():
                logger.info("First-time setup needed")
                self.run_setup_mode()
            else:
                logger.info("Setup already completed")
                self.run_background_mode()
        except Exception as e:
            logger.error(f"Launch failed: {e}")
            sys.exit(1)

def main():
    """Entry point for the launch process."""
    launch_manager = LaunchManager()
    launch_manager.launch()

if __name__ == "__main__":
    main() 