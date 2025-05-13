import os
import yaml
from pathlib import Path
from .defaults import DEFAULTS

def load_config(config_path="config.yaml"):
    """
    Load configuration with fallback to defaults
    Returns merged configuration dictionary
    """
    config = DEFAULTS.copy()
    
    try:
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        _deep_update(config, user_config)
    except Exception as e:
        print(f"⚠️ Config loading warning: {str(e)}")
        print("Using default configuration")
    
    return config

def _deep_update(target, source):
    """Recursively update dictionaries"""
    for key, value in source.items():
        if isinstance(value, dict) and key in target:
            _deep_update(target[key], value)
        else:
            target[key] = value

def validate_config(config):
    """Ensure required configuration exists"""
    required_paths = [
        config['data']['historical_path'],
        config['data']['stats_dir'],
        config['data']['results_dir']
    ]
    
    for path in required_paths:
        if not Path(path).parent.exists():
            os.makedirs(Path(path).parent, exist_ok=True)

# Expose the active configuration
active_config = load_config()
validate_config(active_config)

__all__ = ['DEFAULTS', 'load_config', 'active_config']