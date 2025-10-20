import json
import os
from typing import Dict, Any
from pathlib import Path

class ConfigManager:
    """Manages application configuration settings"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = {
            "dataset_directory": "image_library",
            "metadata_file": "metadata.json",
            "model_path": "yolov8n-seg.pt",
            "conf_threshold": 0.5,
            "max_similar_items": 10
        }
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    return {**self.default_config, **loaded_config}
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                return self.default_config.copy()
        else:
            # Create default config file
            self.save_config(self.default_config)
            return self.default_config.copy()

    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """Save configuration to file"""
        try:
            config_to_save = config if config is not None else self.config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default=None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value and save"""
        self.config[key] = value
        return self.save_config()

    def update(self, updates: Dict[str, Any]) -> bool:
        """Update multiple configuration values"""
        self.config.update(updates)
        return self.save_config()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self.config.copy()

    def validate_directory(self, path: str) -> bool:
        """Validate that a directory exists or can be created"""
        if not path:
            return False

        path_obj = Path(path)

        # Check if it exists and is a directory
        if path_obj.exists():
            return path_obj.is_dir()

        # Try to create it
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
