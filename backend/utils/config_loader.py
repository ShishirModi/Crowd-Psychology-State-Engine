import yaml
import os
from pathlib import Path

# config.yaml lives at project root, two levels above backend/utils/
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config.yaml'
_config = None


def load_config(path=None) -> dict:
    global _config
    resolved = Path(path) if path else _CONFIG_PATH
    if not resolved.exists():
        print(f"Config file not found at {resolved}, using defaults.")
        return {}
    with open(resolved, 'r') as f:
        _config = yaml.safe_load(f)
    return _config


def get_config() -> dict:
    global _config
    if _config is None:
        return load_config()
    return _config
