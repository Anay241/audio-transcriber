#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate Python virtual environment
source "$DIR/venv/bin/activate"

# Run the audio transcriber
cd "$DIR"
python audio_capture.py > "$DIR/transcriber.log" 2>&1 & 