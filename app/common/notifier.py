#app/common/notifier.py


import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AudioNotifier:
    """Handle system sound notifications."""
    
    SOUNDS = {
        'start': '/System/Library/Sounds/Pop.aiff',
        'stop': '/System/Library/Sounds/Bottle.aiff',
        'success': '/System/Library/Sounds/Glass.aiff',
        'error': '/System/Library/Sounds/Basso.aiff'
    }
    
    @staticmethod
    def play_sound(sound_type: str) -> None:
        try:
            if sound_type in AudioNotifier.SOUNDS:
                sound_file = AudioNotifier.SOUNDS[sound_type]
                if os.path.exists(sound_file):
                    os.system(f'afplay {sound_file} &')
        except Exception as e:
            logger.error(f"Error playing sound: {e}") 