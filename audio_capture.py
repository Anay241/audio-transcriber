from typing import Optional, Set, List
import os
import time
import wave
from datetime import datetime
from threading import Thread
import sys
import logging
import ssl
import certifi # type: ignore

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.verify_mode = ssl.CERT_REQUIRED

import numpy as np # type: ignore
import sounddevice as sd # type: ignore
from faster_whisper import WhisperModel # type: ignore
import pyperclip # type: ignore
from pynput import keyboard # type: ignore
import rumps  # type: ignore # For macOS system tray

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
        )
        
        # Initialize audio processor
        self.processor = AudioProcessor(self)
        
        # Menu items with separator to ensure clickability
        self.menu = [
            rumps.MenuItem("Start/Stop Recording (⌘+⇧+9)", callback=self.toggle_recording),
            None,  # Separator - needed for proper menu structure
        ]
        
        logger.info("Audio Transcriber running in background")
        logger.info("Use Command+Shift+9 from any application to start/stop recording")

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
        
        # Initialize Whisper model
        try:
            logger.info("Loading Whisper model...")
            # Initialize Faster Whisper with medium model
            self.model = WhisperModel("medium", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            self.app.title = "❌"  # Error indicator
            AudioNotifier.play_sound('error')
            raise
        
        # Setup keyboard listener
        self.keys_pressed: Set = set()
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
        logger.debug("Keyboard listener started")

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
            
            # Save temporary audio file
            temp_file = "temp_recording.wav"
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            # Transcribe using Faster Whisper
            try:
                segments, _ = self.model.transcribe(temp_file, beam_size=5)
                text = " ".join([segment.text for segment in segments]).strip()
                
                if text:
                    logger.info(f"Transcription successful: {text}")
                    return text
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