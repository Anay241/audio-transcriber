from typing import Optional, Set, List
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
        self.stop()
        rumps.quit_application()

    def toggle_recording(self, _):
        logger.debug("Menu item clicked: toggle recording")
        self.processor.toggle_recording()
    
    def stop(self):
        """Called by rumps when quitting the application."""
        logger.debug("Stopping application")
        self.processor.cleanup()
        super().stop()  # Call parent's stop method

class AudioProcessor:
    def __init__(self, app) -> None:
        """Initialize the audio processing system."""
        logger.debug("Initializing AudioProcessor")
        self.app = app
        
        # Audio settings
        self.sample_rate: int = 16000
        self.channels: int = 1
        self.dtype = np.int16
        self.blocksize: int = 8192
        self.is_recording: bool = False
        self.frames: List[np.ndarray] = []
        
        # Model settings
        self.model = None
        self.model_timeout = 300  # 5 minutes
        self.last_use_time = None
        self.model_cache_dir = os.path.expanduser("~/.cache/huggingface/hub/")
        
        # Setup keyboard listener
        self.keys_pressed: Set = set()
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
        logger.debug("Keyboard listener started")

    def ensure_model_loaded(self) -> WhisperModel:
        """Ensure model is loaded, loading it if necessary."""
        if self.model is None:
            logger.info("Loading Whisper medium model from cache...")
            try:
                self.model = WhisperModel(
                    "medium", 
                    device="cpu", 
                    compute_type="int8",
                    download_root=self.model_cache_dir
                )
                self.last_use_time = time.time()
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.app.title = "❌"  # Error indicator
                AudioNotifier.play_sound('error')
                raise
        return self.model

    def check_model_timeout(self) -> None:
        """Check if model should be unloaded due to inactivity."""
        if (self.model is not None and 
            self.last_use_time is not None and 
            time.time() - self.last_use_time > self.model_timeout):
            self.unload_model()

    def unload_model(self) -> None:
        """Unload model from memory but keep files in cache."""
        if self.model is not None:
            logger.info("Unloading model due to inactivity")
            self.model = None
            self.last_use_time = None
            gc.collect()  # Force garbage collection
            # Reset and refresh the menu bar icon
            self.app.title = "🎤"
            rumps.Timer(lambda _: self.app._nsapp.activateIgnoringOtherApps_(True), 0.1).start()
            rumps.Timer(lambda _: self.app._nsapp.activateIgnoringOtherApps_(False), 0.2).start()

    def cleanup(self) -> None:
        """Clean up resources before app exit."""
        logger.debug("Cleaning up AudioProcessor resources")
        self.stop_recording()
        self.unload_model()
        if self.listener:
            self.listener.stop()
            self.listener = None

    def callback(self, indata: np.ndarray, frames: int, time_info: dict, status: Optional[str]) -> None:
        """Handle audio recording callback."""
        if status:
            logger.warning(f'Audio status: {status}')
        
        # Process audio data
        audio_data = (indata * 32767).astype(np.int16)
        noise_threshold = 100
        audio_data[np.abs(audio_data) < noise_threshold] = 0
        
        self.frames.append(audio_data)
        
        # Update icon to show recording level
        volume_norm = np.linalg.norm(indata) * 20
        new_title = "🎙️" if volume_norm > 2 else "🎤"
        if self.app.title != new_title:
            logger.debug(f"Updating menu bar icon to {new_title}")
            self.app.title = new_title

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
            self.app.title = "💭"  # Thinking emoji
            
            # Ensure model is loaded
            model = self.ensure_model_loaded()
            self.last_use_time = time.time()
            
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
                    self.check_model_timeout()
                    
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
            self.app.title = "🎤"  # Reset icon

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
        """Handle keyboard release events."""
        try:
            if hasattr(key, 'char'):
                self.keys_pressed.discard(key.char.lower())
            else:
                self.keys_pressed.discard(key)
        except Exception as e:
            logger.error(f"Error in key release handler: {e}")

    def toggle_recording(self) -> None:
        """Toggle the recording state."""
        if not self.is_recording:
            logger.info("Starting new recording")
            Thread(target=self.start_recording).start()
        else:
            logger.info("Stopping recording")
            self.stop_recording()

    def start_recording(self) -> None:
        """Start audio recording."""
        if not self.is_recording:
            logger.debug("Initializing recording")
            self.app.title = "⏺️"  # Recording indicator
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
                self.app.title = "🎤"
                AudioNotifier.play_sound('error')

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
                        self.app.title = "✅"  # Success indicator
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
            
            self.app.title = "🎤"  # Reset icon

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