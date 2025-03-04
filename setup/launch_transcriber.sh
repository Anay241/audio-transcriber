#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$DIR")"

# Activate Python virtual environment
source "$PARENT_DIR/venv/bin/activate"

# Run the launch manager with appropriate mode
cd "$PARENT_DIR"
if [ "$1" = "--change-model" ]; then
    echo "Starting model switcher..."
    python3 -m setup.launch_manager --change-model
else
    python3 -m setup.launch_manager
fi 