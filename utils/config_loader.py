import yaml
import os

_config = None

def load_config(path="config.yaml"):
    global _config
    if _config:
        return _config
    
    if not os.path.exists(path):
        print(f"Config file not found at {path}, using defaults.")
        return {}
        
    with open(path, 'r') as f:
        _config = yaml.safe_load(f)
    return _config

def get_config():
    if _config is None:
        return load_config()
    return _config
