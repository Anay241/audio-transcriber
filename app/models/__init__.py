# app/models/__init__.py
"""
Models module for Audio Transcriber.

This module contains model management functionality including:
- ModelManager: Handles downloading, loading, and managing Whisper models
"""

from .model_manager import ModelManager

__all__ = ['ModelManager']

