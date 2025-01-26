#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate Python virtual environment
source "$DIR/venv/bin/activate"

# Run the launch manager with appropriate mode
cd "$DIR"
if [ "$1" = "--change-model" ]; then
    echo "Starting model switcher..."
    python3 launch_manager.py --change-model
else
    python3 launch_manager.py
fi 