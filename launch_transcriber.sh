#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate Python virtual environment
source "$DIR/venv/bin/activate"

# Run the audio transcriber with setup
cd "$DIR"
python run_transcriber.py 