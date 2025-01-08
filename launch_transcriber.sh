#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate Python virtual environment
source "$DIR/venv/bin/activate"

# Run the launch manager
cd "$DIR"
python launch_manager.py 