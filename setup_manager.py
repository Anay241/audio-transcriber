import logging
from typing import Optional, Tuple
from model_manager import ModelManager

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
        print(f"\nPreparing to download model: {model_name}")
        
        # Check disk space first
        has_space, space_msg = self.model_manager.check_disk_space(model_name)
        if not has_space:
            print(f"Error: {space_msg}")
            return False, space_msg

        print("Starting download (this may take a while depending on your internet connection)...")
        success, message = self.model_manager.download_model(model_name)
        
        if success:
            print(f"\nSuccess: {message}")
        else:
            print(f"\nError: {message}")
        
        return success, message

    def run_setup(self) -> bool:
        """Run the complete setup process."""
        print("\nWelcome to AudioTranscriber Setup!")
        print("Let's choose a model for transcription.")
        
        while True:
            self.display_model_options()
            model_choice = self.get_user_model_choice()
            
            if model_choice is None:
                print("\nSetup cancelled.")
                return False
            
            # Confirm choice
            model_info = self.model_manager.get_model_info(model_choice)
            print(f"\nYou selected: {model_choice}")
            print(f"Description: {model_info['description']}")
            confirm = input("Proceed with this model? (y/n): ").lower()
            
            if confirm == 'y':
                success, message = self.handle_model_download(model_choice)
                if success:
                    # Set as active model
                    self.model_manager.set_active_model(model_choice)
                    print("\nSetup completed successfully!")
                    return True
                else:
                    retry = input("\nWould you like to try a different model? (y/n): ").lower()
                    if retry != 'y':
                        print("\nSetup cancelled.")
                        return False
            else:
                print("\nOkay, let's choose again.") 