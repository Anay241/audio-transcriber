import logging
from typing import Optional, Tuple
from app.models.model_manager import ModelManager

# Set up logging
logger = logging.getLogger(__name__)

class SetupManager:
    """Handles the initial setup and configuration of AudioTranscriber."""

    def __init__(self):
        self.model_manager = ModelManager()

    def display_model_options(self):
        """Display available models with their characteristics."""
        models = self.model_manager.get_available_models()
        
        print("\nAvailable models:")
        print("-" * 60)
        print(f"{'#':<3} {'Model':<8} {'Size':<8} {'Speed':<12} {'Accuracy':<10}")
        print("-" * 60)
        
        for idx, (model_name, info) in enumerate(models.items(), 1):
            size = f"{info['size_mb']}MB" if info['size_mb'] < 1000 else f"{info['size_mb']/1000:.1f}GB"
            print(f"{idx:<3} {model_name:<8} {size:<8} {info['speed']:<12} {info['accuracy']:<10}")
        
        print("-" * 60)
        print("Note: Larger models provide better accuracy but require more processing power and time.")

    def get_user_model_choice(self) -> Optional[str]:
        """Get user's model choice and validate it."""
        models = list(self.model_manager.get_available_models().keys())
        
        while True:
            try:
                choice = input(f"\nPlease select a model (1-{len(models)}), or 'q' to quit: ")
                
                if choice.lower() == 'q':
                    return None
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(models):
                    return models[choice_idx]
                else:
                    print(f"Please enter a number between 1 and {len(models)}")
            except ValueError:
                print("Please enter a valid number")

    def handle_model_download(self, model_name: str) -> Tuple[bool, str]:
        """Handle the model download process with progress indication."""
        print(f"\nDownloading {model_name} model...")
        print("This may take a while depending on your internet connection.")
        print("Progress: ", end="", flush=True)
        
        def progress_callback(progress):
            """Display download progress."""
            progress_percent = int(progress * 100)
            if progress_percent % 10 == 0:
                print(".", end="", flush=True)
        
        success, message = self.model_manager.download_model(model_name, progress_callback)
        print(f"\n{message}")
        return success, message

    def run_setup(self) -> bool:
        """Run the setup process to configure the application."""
        print("\n=== Audio Transcriber Setup ===")
        print("This setup will help you choose and download a transcription model.")
        
        # Display available models
        self.display_model_options()
        
        # Get user's model choice
        model_name = self.get_user_model_choice()
        if not model_name:
            logger.info("Setup cancelled by user")
            return False
        
        # Check if model already exists
        if self.model_manager.check_model_exists(model_name):
            print(f"\nModel {model_name} is already downloaded.")
            self.model_manager.set_active_model(model_name)
            return True
        
        # Check disk space
        has_space, message = self.model_manager.check_disk_space(model_name)
        if not has_space:
            print(f"\nError: {message}")
            return False
        
        # Download the model
        success, _ = self.handle_model_download(model_name)
        if success:
            print("\nSetup completed successfully!")
            return True
        else:
            print("\nSetup failed. Please try again later.")
            return False 