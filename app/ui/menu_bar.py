#app/ui/menu_bar.py

import logging
import rumps
import time
from app.core.audio_processor import AudioProcessor
from app.common.notifier import AudioNotifier

# Set up logging
logger = logging.getLogger(__name__)

# App states and their icons
APP_STATES = {
    'idle': '🎤',
    'recording': '🔴',
    'processing': '⏳',
    'completed': '✅'
}

class AudioTranscriberApp(rumps.App):
    def __init__(self):
        logger.debug("Initializing AudioTranscriberApp")
        super().__init__(
            "Audio Transcriber",     # App name
            title=APP_STATES['idle'],  # Menu bar icon
            quit_button=None        # Disable default quit button to prevent accidental quits
        )
        
        # Initialize state
        self.current_state = 'idle'
        self.last_state_change = time.time()
        
        # Initialize audio processor
        self.processor = AudioProcessor(self)
        
        # Menu items with separator to ensure clickability
        self.menu = [
            rumps.MenuItem("Start/Stop Recording (⌘+⇧+9)", callback=self.toggle_recording),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # Set up periodic icon refresh
        rumps.Timer(self.refresh_icon, 0.5).start()  # Refresh icon every half second
        
        logger.info("Audio Transcriber running in background")
        logger.info("Use Command+Shift+9 from any application to start/stop recording")
    
    def set_state(self, state):
        """Set the application state and update the icon."""
        if state in APP_STATES:
            self.current_state = state
            self.title = APP_STATES[state]
            self.last_state_change = time.time()
            logger.debug(f"App state changed to: {state}")
            
            # Play sound notification for state changes
            if state == 'recording':
                AudioNotifier.play_sound('start')
            elif state == 'completed':
                AudioNotifier.play_sound('success')
                # No need to schedule a separate timer - we'll handle this in refresh_icon

    def refresh_icon(self, _):
        """Refresh the icon based on current state."""
        # Check if we need to reset from completed to idle
        if self.current_state == 'completed':
            elapsed = time.time() - self.last_state_change
            if elapsed >= 3.0:  # Reset after 3 seconds
                logger.debug(f"Auto-resetting from completed to idle after {elapsed:.1f} seconds")
                self.current_state = 'idle'
                self.title = APP_STATES['idle']
                self.last_state_change = time.time()
                return
        
        # Add animation for processing state
        if self.current_state == 'processing':
            elapsed = time.time() - self.last_state_change
            animation_chars = ['⏳', '⌛']
            self.title = animation_chars[int(elapsed * 2) % len(animation_chars)]
        
        # Blink for recording state
        elif self.current_state == 'recording':
            elapsed = time.time() - self.last_state_change
            if int(elapsed * 2) % 2 == 0:
                self.title = APP_STATES['recording']
            else:
                self.title = '⚫'
        
        # For completed state, ensure it stays visible until timeout
        elif self.current_state == 'completed':
            self.title = APP_STATES['completed']

    def quit_app(self, _):
        """Quit the application."""
        logger.info("Quitting application")
        try:
            self.stop()
            rumps.quit_application()
        except Exception as e:
            logger.error(f"Error quitting application: {e}")
            rumps.quit_application()

    def stop(self):
        """Stop all processes before quitting."""
        try:
            if hasattr(self, 'processor'):
                self.processor.cleanup()
        except Exception as e:
            logger.error(f"Error stopping processes: {e}")

    def toggle_recording(self, _):
        """Toggle recording state."""
        self.processor.toggle_recording()

def main():
    """Run the audio transcriber application."""
    app = AudioTranscriberApp()
    app.run()
    
    return app 