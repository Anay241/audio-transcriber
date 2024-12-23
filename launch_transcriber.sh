#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate Python environment if needed (uncomment and modify if using a virtual environment)
# source ~/path/to/your/venv/bin/activate

# Run the audio transcriber
cd "$DIR"
/usr/local/bin/python3 audio_capture_2.py > "$DIR/transcriber.log" 2>&1 & 