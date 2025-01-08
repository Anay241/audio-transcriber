# Audio Transcriber

A macOS menu bar application that provides quick audio recording and real-time transcription using OpenAI's Whisper model. The app sits quietly in your menu bar, ready to transcribe your speech with just a keyboard shortcut.

## Features

- 🎙️ Global hotkey (⌘+⇧+9) to start/stop recording from any application
- 🔄 Real-time audio level feedback in menu bar icon
- 🚀 Fast transcription using Faster-Whisper
- 📋 Automatic clipboard copying of transcribed text
- 🔔 Audio notifications for user feedback
- 💻 Runs in the background as a menu bar application
- 🧠 Efficient memory management (model unloads after inactivity)

## Requirements

- macOS (tested on macOS Sonoma)
- Python 3.11 or higher
- Internet connection (for first-time model download)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/audio-transcriber.git
cd audio-transcriber
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Make the launcher script executable:
```bash
chmod +x launch_transcriber.sh
```

## Usage

1. Start the application:
```bash
./launch_transcriber.sh
```

2. The application will appear as a microphone icon (🎤) in your menu bar

3. To record and transcribe:
   - Use the global hotkey ⌘+⇧+9 (Command+Shift+9), or
   - Click the menu bar icon and select "Start/Stop Recording"

4. The transcribed text will be automatically copied to your clipboard

### Menu Bar Icon States
- 🎤 Ready to record
- ⏺️ Recording in progress
- 🎙️ Audio detected during recording
- 💭 Transcribing
- ✅ Transcription successful
- ❌ Error occurred

### Sound Notifications
The application provides audio feedback for:
- Starting recording (Pop sound)
- Stopping recording (Bottle sound)
- Successful transcription (Glass sound)
- Errors (Basso sound)

## Auto-start on Login

To have the application start automatically when you log in:

1. Copy the launch agent plist:
```bash
cp com.user.audiotranscriber.plist ~/Library/LaunchAgents/
```

2. Load the launch agent:
```bash
launchctl load ~/Library/LaunchAgents/com.user.audiotranscriber.plist
```

## Memory Management

The application automatically manages memory by:
- Loading the Whisper model only when needed
- Unloading the model after 5 minutes of inactivity
- Cleaning up temporary audio files after transcription

## Troubleshooting

1. If the menu bar icon becomes misaligned:
   - Click the icon to reset its position
   - Quit and restart the application

2. If recording doesn't start:
   - Check if your microphone permissions are enabled in System Preferences
   - Try quitting and restarting the application

3. If transcription is slow:
   - The first transcription might take longer as it downloads the model
   - Subsequent transcriptions will be faster

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 