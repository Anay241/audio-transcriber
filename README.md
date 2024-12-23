# Audio Transcriber

A macOS menu bar application that provides quick audio recording and transcription using OpenAI's Whisper model.

## Features

- Global hotkey (⌥+⇧+S) to start/stop recording from any application
- Menu bar icon with visual feedback during recording
- Fast transcription using Faster-Whisper
- Automatic clipboard copying of transcribed text
- Audio notifications for user feedback
- Runs in the background as a menu bar application

## Requirements

- macOS (tested on macOS Sonoma)
- Python 3.11 or higher
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/audio-transcriber.git
cd audio-transcriber
```

2. Install required packages:
```bash
pip3 install -r requirements.txt
```

3. Make the launcher script executable:
```bash
chmod +x launch_transcriber.sh
```

## Usage

1. Run the application:
```bash
./launch_transcriber.sh
```

2. The application will appear as a microphone icon (🎤) in your menu bar

3. To record:
   - Use the global hotkey ⌥+⇧+S (Option+Shift+S)
   - Or click the menu bar icon and select "Start/Stop Recording"

4. The transcribed text will be automatically copied to your clipboard

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

## Sound Notifications

The application provides audio feedback for:
- Starting recording (Pop sound)
- Stopping recording (Bottle sound)
- Successful transcription (Glass sound)
- Errors (Basso sound)

## License

MIT License - see LICENSE file for details 