import os
import sys
import logging
import subprocess
import argparse
import signal
import time
from pathlib import Path
from model_manager import ModelManager
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

class LaunchManager:
    """Manages the application launch process and modes."""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.pid_file = Path("transcriber.pid")
        
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
            logger.debug(f"Found running instance with PID {pid}")
            return True
        except OSError:
            # Process not running, clean up stale PID file
            logger.debug(f"Found stale PID file for {pid}")
            self._cleanup_pid()
            return False
    
    def stop_running_instance(self) -> None:
        """Stop any running instance of the application."""
        pid = self._read_pid()
        if pid is not None:
            try:
                logger.info(f"Stopping existing instance (PID: {pid})")
                os.kill(pid, signal.SIGTERM)
                # Wait for process to terminate
                for _ in range(10):  # Wait up to 1 second
                    time.sleep(0.1)
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        break
                else:
                    logger.warning(f"Process {pid} did not terminate gracefully")
            except OSError as e:
                logger.error(f"Error stopping process {pid}: {e}")
            finally:
                self._cleanup_pid()
    
    def launch(self, change_model: bool = False) -> None:
        """
        Launch the application.
        
        Args:
            change_model: If True, run the model switcher interface
        """
        try:
            # Handle existing instance
            if self.is_app_running():
                if change_model:
                    # Stop existing instance for model change
                    self.stop_running_instance()
                else:
                    logger.info("Application already running")
                    return

            if change_model:
                # Run model switcher
                from setup_manager import SetupManager
                setup_manager = SetupManager()
                if setup_manager.run_setup():
                    # Start new instance with new model
                    self._start_app()
            else:
                # Normal launch
                self._start_app()

        except Exception as e:
            logger.error(f"Launch failed: {e}")
            raise
    
    def _start_app(self) -> None:
        """Start the application process."""
        try:
            # Start the process
            process = subprocess.Popen(
                [sys.executable, "run_transcriber.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Save PID
            self._write_pid(process.pid)
            logger.info(f"Application launched in background (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise

def main():
    """Entry point for the launch process."""
    parser = argparse.ArgumentParser(description="AudioTranscriber Launcher")
    parser.add_argument('--change-model', action='store_true', 
                      help='Run model switcher interface')
    args = parser.parse_args()
    
    launch_manager = LaunchManager()
    launch_manager.launch(change_model=args.change_model)

if __name__ == "__main__":
    main() 