from typing import Optional, Set, List, Tuple
import os
import time
import wave
from datetime import datetime
from threading import Thread
import sys
import logging
import ssl
import certifi
import gc
import noisereduce as nr

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.verify_mode = ssl.CERT_REQUIRED

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import pyperclip
from pynput import keyboard
import rumps
from model_manager import ModelManager

class AudioNotifier:
    """Handle system sound notifications."""
    
    SOUNDS = {
        'start': '/System/Library/Sounds/Pop.aiff',      # Recording start
        'stop': '/System/Library/Sounds/Bottle.aiff',    # Recording stop
        'success': '/System/Library/Sounds/Glass.aiff',  # Transcription complete
        'error': '/System/Library/Sounds/Basso.aiff'     # Error occurred
    }
    
    @staticmethod
    def play_sound(sound_type: str) -> None:
        """Play a system sound."""
        try:
            if sound_type in AudioNotifier.SOUNDS:
                sound_file = AudioNotifier.SOUNDS[sound_type]
                if os.path.exists(sound_file):
                    os.system(f'afplay {sound_file} &')
        except Exception as e:
            logger.error(f"Error playing sound: {e}")

class AudioTranscriberApp(rumps.App):
    def __init__(self):
        logger.debug("Initializing AudioTranscriberApp")
        super().__init__(
            "Audio Transcriber",     # App name
            title="🎤",             # Menu bar icon
            quit_button=None        # Disable default quit button to prevent accidental quits
        )
        
        # Initialize audio processor
        self.processor = AudioProcessor(self)
        
        # Menu items with separator to ensure clickability
        self.menu = [
            rumps.MenuItem("Start/Stop Recording (⌘+⇧+9)", callback=self.toggle_recording),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # Set up periodic icon refresh
        rumps.Timer(self.refresh_icon, 60).start()  # Refresh icon every minute
        
        logger.info("Audio Transcriber running in background")
        logger.info("Use Command+Shift+9 from any application to start/stop recording")

    def refresh_icon(self, _):
        """Periodically refresh the menu bar icon to prevent visual glitches."""
        if not self.processor.is_recording:
            current_title = self.title
            self.title = current_title  # Force a refresh of the icon

    def quit_app(self, _):
        """Quit the application."""
        logger.info("Quitting application")
        self.processor.cleanup()  # Clean up resources
        
        # Import cleanup function from run_transcriber and clean logs
        try:
            from run_transcriber import cleanup_logs
            cleanup_logs()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        rumps.quit_application()  # Quit the application
    
    def stop(self):
        """Called by rumps when quitting the application."""
        logger.debug("Stopping application")
        self.processor.cleanup()

    def toggle_recording(self, _):
        """Toggle recording state via menu bar."""
        logger.debug("Menu item clicked: toggle recording")
        self.processor.toggle_recording()

class AudioProcessor:
    """Handle audio recording and processing."""
    
    def __init__(self, app):
        """Initialize the audio processing system."""
        logger.debug("Initializing AudioProcessor")
        self.app = app
        
        # Reverting to original working audio settings
        self.sample_rate: int = 16000
        self.channels: int = 1
        self.dtype = np.int16
        self.blocksize: int = 8192
        
        # Recording state
        self.is_recording: bool = False
        self.ready_to_record: bool = True
        self.frames: List[np.ndarray] = []
        
        # Model management
        self.model_manager = ModelManager()
        
        # Icon state
        self._icon_state = "🎤"
        
        # Setup keyboard listener
        self.keys_pressed: Set = set()
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
        logger.debug("Keyboard listener started")
        
        # Start icon refresh timer
        rumps.Timer(self.refresh_icon_state, 1).start()

    @property
    def icon_state(self):
        """Get current icon state."""
        return self._icon_state

    @icon_state.setter
    def icon_state(self, value):
        """Set icon state and update menu bar."""
        self._icon_state = value
        try:
            self.app.title = value
        except Exception as e:
            logger.error(f"Error updating icon: {e}")

    def refresh_icon_state(self, _):
        """Refresh the icon state periodically."""
        if not self.is_recording:
            try:
                current = self.icon_state
                # Temporarily set to a different state and back
                self.icon_state = "🎤 "  # Note the space
                time.sleep(0.1)
                self.icon_state = current
            except Exception as e:
                logger.error(f"Error in icon refresh: {e}")

    def ensure_model_loaded(self) -> WhisperModel:
        """Get a loaded model for transcription."""
        try:
            return self.model_manager.get_model()
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.icon_state = "❌"
            AudioNotifier.play_sound('error')
            raise

    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_data: The audio data to transcribe
            
        Returns:
            Transcription text or None if transcription failed
        """
        try:
            logger.info("Starting transcription")
            self.icon_state = "💭"  # Thinking emoji
            
            # Get model for transcription
            model = self.ensure_model_loaded()
            
            # Save temporary audio file
            temp_file = "temp_recording.wav"
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            # Transcribe using Faster Whisper
            try:
                segments, _ = model.transcribe(
                    temp_file,
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                # Process segments
                text_segments = []
                for segment in segments:
                    # Clean up the segment text
                    segment_text = segment.text.strip()
                    if segment_text:
                        text_segments.append(segment_text)
                
                # Join and process the text
                if text_segments:
                    text = ' '.join(text_segments)
                    processed_text = self.process_text(text)
                    logger.info(f"Transcription successful: {processed_text}")
                    
                    # Check if we should unload the model
                    self.model_manager.check_timeout()
                    
                    return processed_text
                else:
                    logger.warning("No speech detected in audio")
                    return None
                    
            finally:
                # Ensure temporary file is always cleaned up
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return None
        finally:
            self.icon_state = "🎤"  # Reset icon

    def process_text(self, text: str) -> str:
        """
        Process transcribed text to improve formatting.
        
        Args:
            text: Raw transcribed text
            
        Returns:
            Formatted text with proper capitalization and punctuation
        """
        if not text:
            return text
            
        # Split into sentences (Whisper sometimes misses proper sentence breaks)
        sentences = []
        current_sentence = []
        
        # Split by existing periods but keep them
        parts = text.replace('. ', '.').split('.')
        
        for part in parts:
            if not part.strip():
                continue
                
            # Clean up the part
            cleaned = part.strip()
            
            # Capitalize first letter
            if cleaned:
                cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
            
            # Add period if it's a complete thought
            if cleaned and not cleaned.endswith(('!', '?', '.')):
                cleaned += '.'
            
            sentences.append(cleaned)
        
        # Join sentences with proper spacing
        return ' '.join(sentences)

    def on_press(self, key: keyboard.Key) -> None:
        """Handle keyboard press events."""
        try:
            # Track pressed keys
            if hasattr(key, 'char'):
                self.keys_pressed.add(key.char.lower())
            else:
                self.keys_pressed.add(key)
            
            # Check for hotkey combination (Cmd+Shift+9)
            if (keyboard.Key.cmd in self.keys_pressed and 
                keyboard.Key.shift in self.keys_pressed and 
                '9' in self.keys_pressed):
                logger.debug("Hotkey detected: Command+Shift+9")
                self.toggle_recording()
        except Exception as e:
            logger.error(f"Error in key press handler: {e}")

    def on_release(self, key: keyboard.Key) -> None:
        """
        Handle keyboard release events.
        
        Args:
            key: The key that was released, can be None if key couldn't be determined
        """
        try:
            # Safety check for None key
            if key is None:
                logger.debug("Received None key in release handler")
                return
                
            # Handle character keys
            if hasattr(key, 'char'):
                if key.char is not None:  # Make sure we have a valid character
                    self.keys_pressed.discard(key.char.lower())
                else:
                    logger.debug("Key has char attribute but char is None")
            # Handle special keys (like shift, ctrl, etc.)
            else:
                self.keys_pressed.discard(key)
                
        except Exception as e:
            logger.error(f"Error in key release handler: {e}")
            # Don't re-raise the exception - we want to keep running even if key handling fails

    def toggle_recording(self) -> None:
        """Toggle recording state."""
        if not self.is_recording and self.ready_to_record:
            logger.info("Starting new recording")
            Thread(target=self.start_recording).start()
        elif self.is_recording:
            logger.info("Stopping recording")
            self.stop_recording()

    def start_recording(self) -> None:
        """Start audio recording."""
        if not self.is_recording and self.ready_to_record:  # Check both conditions
            logger.debug("Initializing recording")
            self.icon_state = "⏺️"  # Recording indicator
            self.frames = []
            self.is_recording = True
            
            try:
                AudioNotifier.play_sound('start')  # Play start sound
                with sd.InputStream(
                    callback=self.callback,
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    blocksize=self.blocksize,
                    dtype=np.float32
                ):
                    logger.info("Recording started")
                    while self.is_recording:
                        time.sleep(0.1)
                        
            except Exception as e:
                logger.error(f"Error during recording: {e}")
                self.is_recording = False
                self.icon_state = "🎤"
                AudioNotifier.play_sound('error')

    def callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
        """
        Callback function for audio recording.
        
        Args:
            indata: Input audio data as numpy array
            frames: Number of frames
            time_info: Dictionary with timing information
            status: Status flags indicating errors
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Convert float32 to int16
        audio_data = (indata * np.iinfo(np.int16).max).astype(np.int16)
        self.frames.append(audio_data.copy())

    def stop_recording(self) -> None:
        """Stop recording and process the audio."""
        logger.debug("Stopping recording")
        self.is_recording = False
        AudioNotifier.play_sound('stop')  # Play stop sound
        
        if self.frames:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"recording_{timestamp}.wav"
            
            # Process audio
            audio_data = self.save_audio(audio_filename)
            
            if audio_data is not None:
                try:
                    # Transcribe and copy to clipboard
                    transcript = self.transcribe_audio(audio_data)
                    if transcript:
                        pyperclip.copy(transcript)
                        logger.info("Transcription copied to clipboard")
                        self.icon_state = "✅"  # Success indicator
                        AudioNotifier.play_sound('success')  # Play success sound
                        time.sleep(1)  # Show success briefly
                    else:
                        AudioNotifier.play_sound('error')  # Play error sound if no transcription
                finally:
                    # Cleanup
                    try:
                        os.remove(audio_filename)
                        logger.debug("Temporary audio file deleted")
                    except Exception as e:
                        logger.error(f"Could not delete audio file: {e}")
                        AudioNotifier.play_sound('error')
            else:
                AudioNotifier.play_sound('error')  # Play error sound if audio processing failed
                
            self.icon_state = "🎤"  # Reset icon
            self.ready_to_record = True  # Set ready to record back to True after processing

    def save_audio(self, filename: str) -> Optional[np.ndarray]:
        """
        Save recorded audio to file.
        
        Args:
            filename: The name of the file to save
            
        Returns:
            The audio data if successful, None otherwise
        """
        if not self.frames:
            logger.warning("No audio frames to save")
            return None
            
        try:
            audio_data = np.concatenate(self.frames)
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            logger.debug(f"Audio saved as {filename}")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return None

    def cleanup(self):
        """Clean up resources."""
        logger.debug("Cleaning up resources")
        self.listener.stop()

def main():
    """Main function to run the audio transcriber app."""
    try:
        logger.info("Starting Audio Transcriber")
        app = AudioTranscriberApp()
        app.run()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 