#!/usr/bin/env python3
"""
Audio Transcriber - Main Entry Point

This is the main entry point for the Audio Transcriber application.
It sets up the Python path and calls the run_transcriber module.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import after path setup
from bin import run_transcriber

if __name__ == "__main__":
    # Run the transcriber
    run_transcriber.main() 