# utils/config.py
import yaml
import os
from typing import Dict, Any

class ConfigManager:
    """Configuration manager for the Re-ID system."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            print(f"⚠️ Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'reid': {
                'model_name': 'osnet_x1_0',
                'model_path': None,
                'embedding_dim': 512,
                'input_size': [256, 128],
                'device': 'cuda',
                'matching': {
                    'threshold': 0.55,
                    'max_distance': 0.8,
                    'gallery_update_rate': 0.1
                },
                'quality': {
                    'min_resolution': [64, 128],
                    'blur_threshold': 1000,
                    'contrast_threshold': 30
                }
            },
            'database': {
                'path': 'database/identities.db'
            },
            'visualization': {
                'show_reid_scores': True,
                'show_global_ids': True,
                'crop_display_size': [128, 256]
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def update(self, key: str, value: Any):
        """Update configuration value."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)