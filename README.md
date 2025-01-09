# AudioTranscriber

A macOS menu bar application that provides real-time audio transcription using Whisper AI. Simply press a hotkey, speak, and get your speech transcribed to text instantly.

## Features

- 🎤 Menu bar interface with hotkey support (Cmd+Shift+9)
- 🔄 Real-time audio capture and transcription
- 📋 Automatic clipboard copying of transcribed text
- 🎯 Multiple Whisper models to choose from (varying accuracy and speed)
- 💾 Smart memory management (auto-unloads model when inactive)
- 🔔 Audio feedback for actions

## System Requirements

- macOS (tested on macOS Sonoma and above)
- Python 3.11 or higher
- At least 2GB of free disk space (for models)
- Internet connection (for first-time model download)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/audio_transcriber.git
   cd audio_transcriber
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
   chmod +x launch_transcriber.sh
   ```

## First-Time Setup

1. Run the application:
   ```bash
   ./launch_transcriber.sh
   ```

2. On first run, you'll be prompted to choose a transcription model:
   - **tiny** (150MB): Fastest, basic accuracy
   - **base** (400MB): Very fast, good accuracy
   - **small** (900MB): Fast, better accuracy
   - **medium** (3GB): Moderate speed, very good accuracy
   - **large** (6GB): Slow, best accuracy

   Choose based on your needs and available system resources.

## Usage

1. The app runs in your menu bar (look for the 🎤 icon)

2. To transcribe:
   - Press `Cmd+Shift+9` to start recording
   - Speak clearly
   - Press `Cmd+Shift+9` again to stop recording
   - The transcribed text will be automatically copied to your clipboard

3. Visual Indicators:
   - 🎤 Ready to record
   - ⏺️ Recording in progress
   - 💭 Transcribing
   - ✅ Transcription complete

4. Audio Feedback:
   - Pop sound: Recording started
   - Bottle sound: Recording stopped
   - Glass sound: Transcription successful
   - Basso sound: Error occurred

## Changing Models

To switch to a different model:
```bash
./launch_transcriber.sh --change-model
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
   - Check the logs in `transcriber.log`

2. **Model download fails?**
   - Check your internet connection
   - Ensure you have enough disk space
   - Try a smaller model first

3. **Transcription not working?**
   - Make sure your microphone is working and permitted
   - Check if the model was downloaded successfully
   - Try restarting the application

## Logs

Logs are stored in:
- `transcriber.log`: Main application logs
- `launcher.log`: Launch script logs
- `launcher.error.log`: Launch error logs

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 