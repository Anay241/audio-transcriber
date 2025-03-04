import os
import sys
import logging
import subprocess
import argparse
import signal
import time
from pathlib import Path
from app.models.model_manager import ModelManager
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

class LaunchManager:
    """Manages the application launch process and modes."""
    
    def __init__(self):
        self.model_manager = ModelManager()
        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        self.pid_file = logs_dir / "transcriber.pid"
        
    def _read_pid(self) -> Optional[int]:
        """Read the PID from file if it exists."""
        try:
            if self.pid_file.exists():
                pid = int(self.pid_file.read_text().strip())
                return pid
        except (ValueError, IOError) as e:
            logger.error(f"Error reading PID file: {e}")
        return None
        
    def _write_pid(self, pid: int) -> None:
        """Write PID to file."""
        try:
            self.pid_file.write_text(str(pid))
            logger.debug(f"Wrote PID {pid} to {self.pid_file}")
        except IOError as e:
            logger.error(f"Error writing PID file: {e}")
    
    def _cleanup_pid(self) -> None:
        """Clean up the PID file."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.debug("Removed PID file")
        except IOError as e:
            logger.error(f"Error removing PID file: {e}")
    
    def is_app_running(self) -> bool:
        """Check if the application is already running."""
        pid = self._read_pid()
        if pid is None:
            return False
            
        try:
            # Check if process exists
            os.kill(pid, 0)
            return True
        except OSError:
            # Process doesn't exist
            self._cleanup_pid()
            return False
    
    def stop_running_instance(self) -> None:
        """Stop a running instance of the application."""
        pid = self._read_pid()
        if pid is None:
            logger.info("No running instance found")
            return
            
        try:
            # Try to terminate gracefully first
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent termination signal to process {pid}")
            
            # Wait for process to terminate
            for _ in range(10):  # Wait up to 5 seconds
                try:
                    os.kill(pid, 0)  # Check if process exists
                    time.sleep(0.5)
                except OSError:
                    # Process terminated
                    break
            else:
                # Process didn't terminate, force kill
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Force killed process {pid}")
                
            self._cleanup_pid()
        except OSError as e:
            logger.error(f"Error stopping process {pid}: {e}")
            self._cleanup_pid()
    
    def launch(self, change_model: bool = False) -> None:
        """Launch the application."""
        # Check if already running
        if self.is_app_running():
            logger.info("Application is already running")
            if change_model:
                # Stop the running instance
                logger.info("Stopping running instance to change model")
                self.stop_running_instance()
            else:
                # Just exit
                logger.info("Exiting without launching new instance")
                return
        
        # If we're changing the model, run setup
        if change_model:
            from setup.setup_manager import SetupManager
            setup_manager = SetupManager()
            if not setup_manager.run_setup():
                logger.error("Model change cancelled or failed")
                return
        
        # Launch the application
        self._start_app()
    
    def _start_app(self) -> None:
        """Start the application process."""
        try:
            # Launch the application using Python from the bin directory
            cmd = [sys.executable, "bin/main.py"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Write PID to file
            self._write_pid(process.pid)
            logger.info(f"Started application with PID {process.pid}")
        except Exception as e:
            logger.error(f"Error starting application: {e}")

def main():
    """Main entry point for the launch manager."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Launch the Audio Transcriber application")
    parser.add_argument("--change-model", action="store_true", help="Change the transcription model")
    args = parser.parse_args()
    
    # Launch the application
    launch_manager = LaunchManager()
    launch_manager.launch(change_model=args.change_model)

if __name__ == "__main__":
    main() 