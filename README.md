# AudioTranscriber

A macOS menu bar application that provides real-time audio transcription using Whisper AI. Simply press a hotkey, speak, and get your speech transcribed to text instantly.

## Features

- 🎤 Menu bar interface with hotkey support (Cmd+Shift+9)
- 🔄 Real-time audio capture and transcription
- 📋 Automatic clipboard copying of transcribed text
- 🎯 Multiple Whisper models to choose from (varying accuracy and speed)
- 💾 Smart memory management (auto-unloads model when inactive)
- 🔔 Audio feedback for actions
- 🔄 Visual state indicators (recording, processing, completed)

## System Requirements

- macOS (tested on macOS Sonoma and above)
- Python 3.11 or higher
- At least 2GB of free disk space (for models)
- Internet connection (for first-time model download)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Anay241/Audio_Transcriber.git
   cd Audio_Transcriber
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Make the launch script executable:
   ```bash
   chmod +x setup/launch_transcriber.sh
   chmod +x bin/main.py
   ```

## First-Time Setup

1. Run the application:
   ```bash
   ./setup/launch_transcriber.sh
   ```

2. On first run, you'll be prompted to choose a transcription model:
   - **tiny** (150MB): Fastest, basic accuracy
   - **base** (400MB): Very fast, good accuracy
   - **small** (900MB): Fast, better accuracy
   - **medium** (3GB): Moderate speed, very good accuracy
   - **large** (6GB): Slow, best accuracy

   Choose based on your needs and available system resources.

## Project Structure

```
Audio_Transcriber/
├── app/                    # Main application code
│   ├── common/             # Common utilities
│   ├── core/               # Core functionality
│   │   └── audio_processor.py  # Audio processing and transcription
│   ├── models/             # Model management
│   └── ui/                 # User interface
│       └── menu_bar.py     # Menu bar implementation
├── bin/                    # Executable scripts
│   └── main.py             # Main entry point
├── logs/                   # Log files directory
├── setup/                  # Setup and launch scripts
│   ├── launch_manager.py   # Application launcher
│   ├── launch_transcriber.sh  # Launch script
│   └── setup_manager.py    # First-time setup
└── utils/                  # Utility functions
    ├── file_utils.py       # File handling utilities
    └── logger.py           # Logging configuration
```

## Usage

1. The app runs in your menu bar (look for the 🎤 icon)

2. To transcribe:
   - Press `Cmd+Shift+9` to start recording
   - Speak clearly
   - Press `Cmd+Shift+9` again to stop recording
   - The transcribed text will be automatically copied to your clipboard

3. Visual Indicators:
   - 🎤 Ready to record (idle state)
   - ⏺️ Recording in progress (recording state)
   - 💭 Transcribing (processing state)
   - ✅ Transcription complete (completed state - automatically returns to idle)

4. Audio Feedback:
   - Pop sound: Recording started
   - Bottle sound: Recording stopped
   - Glass sound: Transcription successful
   - Basso sound: Error occurred

## Changing Models

To switch to a different model:
```bash
./setup/launch_transcriber.sh --change-model
```

This will:
1. Show your current model and its characteristics
2. Let you choose a new model
3. Handle the download and switch automatically

## Model Storage and Management

Models are stored in the Hugging Face cache directory:
```
~/.cache/huggingface/hub/
```

For advanced users:
- Models are shared between applications using Whisper
- Each model is stored in: `models--guillaumekln--faster-whisper-{model_name}`
- You can manually delete models from this directory if needed
- The app will automatically download models again if needed

## Troubleshooting

1. **No menu bar icon?**
   - Make sure you're running from the correct directory
   - Check the logs in `logs/transcriber.log`

2. **Model download fails?**
   - Check your internet connection
   - Ensure you have enough disk space
   - Try a smaller model first

3. **Transcription not working?**
   - Make sure your microphone is working and permitted
   - Check if the model was downloaded successfully
   - Try restarting the application

## Logs

Logs are stored in the `logs` directory:
- `transcriber.log`: Main application logs
- `launcher.log`: Launch script logs
- `launcher.error.log`: Launch error logs
- `pid.txt`: Process ID file for the running application

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 