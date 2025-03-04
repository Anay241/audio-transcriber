#app/core/audio_processor.py

from typing import Optional, Set, List
import os
import time
import wave
from datetime import datetime
from threading import Thread
import logging
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import pyperclip
from pynput import keyboard
import rumps
import atexit
import gc
import multiprocessing
import multiprocessing.resource_tracker
import signal
import sys

from app.models.model_manager import ModelManager
from app.core.text_processor import process_text
from app.common.notifier import AudioNotifier

# Set up logging
logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handle audio recording and processing."""
    
    def __init__(self, app):
        """Initialize the audio processing system."""
        logger.debug("Initializing AudioProcessor")
        self.app = app
        
        # Reverting to original working audio settings
        self.sample_rate: int = 44100
        self.channels: int = 1
        self.dtype = np.int16
        self.blocksize: int = 8192
        
        # Recording state
        self.is_recording: bool = False
        self.ready_to_record: bool = True
        self.frames: List[np.ndarray] = []
        
        # Model management
        self.model_manager = ModelManager()
        
        # Thread tracking
        self.transcription_thread = None
        
        # Setup keyboard listener
        self.keys_pressed: Set = set()
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
        logger.debug("Keyboard listener started")
        
        # Register cleanup function to be called at exit
        atexit.register(self.cleanup)
        logger.debug("Registered cleanup function with atexit")

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
                    processed_text = process_text(text)
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

    def on_press(self, key: keyboard.Key) -> None:
        """Handle key press events."""
        try:
            # Add the key to the set of pressed keys
            self.keys_pressed.add(key)
            
            # Check for Command+Shift+9 combination
            if (keyboard.Key.cmd in self.keys_pressed and 
                keyboard.Key.shift in self.keys_pressed and 
                hasattr(key, 'char') and key.char == '9'):
                # Toggle recording
                self.toggle_recording()
        except Exception as e:
            logger.error(f"Error in key press handler: {e}")

    def on_release(self, key: keyboard.Key) -> None:
        """Handle key release events."""
        try:
            # Remove the key from the set of pressed keys if it's there
            self.keys_pressed.discard(key)
        except Exception as e:
            logger.error(f"Error in key release handler: {e}")

    def toggle_recording(self) -> None:
        """Toggle recording state."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        """Start recording audio."""
        if self.is_recording or not self.ready_to_record:
            logger.warning("Cannot start recording: already recording or not ready")
            return
            
        try:
            logger.info("Starting recording")
            self.ready_to_record = False  # Prevent multiple starts
            self.frames = []  # Clear previous frames
            self.is_recording = True
            
            # Update app state
            self.app.set_state('recording')
            
            # Start recording stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=self.callback
            )
            self.stream.start()
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.is_recording = False
            AudioNotifier.play_sound('error')
        finally:
            self.ready_to_record = True  # Ready for next recording

    def callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback for audio stream to collect frames."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        self.frames.append(indata.copy())

    def stop_recording(self) -> None:
        """Stop recording and process the audio."""
        if not self.is_recording:
            logger.warning("Cannot stop recording: not currently recording")
            return
            
        try:
            logger.info("Stopping recording")
            self.is_recording = False
            
            # Update app state to processing
            self.app.set_state('processing')
            
            # Play stop sound
            AudioNotifier.play_sound('stop')
            
            # Stop and close the stream
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            
            # Process the recorded audio if we have frames
            if self.frames:
                # Convert frames to a single array
                audio_data = np.concatenate(self.frames, axis=0)
                
                # Start transcription in a separate thread to keep UI responsive
                def transcribe_thread():
                    try:
                        # Transcribe the audio
                        logger.info("Starting transcription")
                        transcription = self.transcribe_audio(audio_data)
                        
                        if transcription:
                            # Copy to clipboard
                            pyperclip.copy(transcription)
                            logger.info(f"Transcription successful: {transcription}")
                            logger.info("Transcription copied to clipboard")
                            
                            # Set completed state
                            self.app.set_state('completed')
                        else:
                            logger.warning("No transcription result")
                            AudioNotifier.play_sound('error')
                            self.app.set_state('idle')
                    except Exception as e:
                        logger.error(f"Error in transcription thread: {e}")
                        AudioNotifier.play_sound('error')
                        self.app.set_state('idle')
                
                # Start the transcription thread and track it
                self.transcription_thread = Thread(target=transcribe_thread)
                self.transcription_thread.daemon = True  # Make it a daemon thread
                self.transcription_thread.start()
                logger.debug("Transcription thread started")
            else:
                logger.warning("No audio frames captured")
                self.app.set_state('idle')
                
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            AudioNotifier.play_sound('error')
            self.app.set_state('idle')

    def save_audio(self, filename: str) -> Optional[np.ndarray]:
        """Save recorded audio to a WAV file."""
        if not self.frames:
            logger.warning("No audio frames to save")
            return None
            
        try:
            # Combine all frames
            audio_data = np.concatenate(self.frames, axis=0)
            
            # Save to WAV file
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
                
            logger.info(f"Audio saved to {filename}")
            return audio_data
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return None

    def cleanup(self):
        """Clean up resources when the application exits."""
        logger.info("Cleaning up AudioProcessor resources")
        
        # Stop keyboard listener if active
        if hasattr(self, 'listener') and self.listener:
            logger.info("Stopping keyboard listener")
            self.listener.stop()
        
        # Stop audio stream if active
        if hasattr(self, 'stream') and self.stream and self.stream.active:
            logger.info("Stopping audio stream")
            self.stream.stop()
            self.stream.close()
        
        # Stop transcription thread if active
        if hasattr(self, 'transcription_thread') and self.transcription_thread and self.transcription_thread.is_alive():
            logger.info("Waiting for transcription thread to complete")
            # Give the thread a chance to complete naturally
            self.transcription_thread.join(timeout=2.0)
        
        # Unload model if loaded
        if hasattr(self, 'model_manager') and self.model_manager:
            logger.info("Unloading Whisper model")
            self.model_manager.unload_model()
        
        # Force garbage collection
        logger.info("Forcing garbage collection")
        gc.collect()
        
        logger.info("AudioProcessor cleanup completed") 