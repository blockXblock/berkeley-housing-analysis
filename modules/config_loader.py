"""
Config loader with automatic project root detection.
Works in any environment: local, Binder, Colab, etc.
"""

import os
import sys
import json
from pathlib import Path


def find_project_root(marker_files=None):
    """
    Find the project root by looking for marker files.

    Args:
        marker_files: List of files that indicate project root.
                     Defaults to ['00_config', 'modules', 'requirements.txt']

    Returns:
        Path to project root
    """
    if marker_files is None:
        marker_files = ['00_config', 'modules', 'requirements.txt']

    # Start from current working directory
    current = Path.cwd()

    # Check current directory and parents
    for path in [current] + list(current.parents):
        for marker in marker_files:
            if (path / marker).exists():
                return path

    # Fallback: try to find from this file's location
    module_path = Path(__file__).resolve().parent
    if module_path.name == 'modules':
        return module_path.parent

    raise FileNotFoundError(
        f"Could not find project root. "
        f"Looking for: {marker_files}"
    )


def load_config(config_name='berkeley_config.json'):
    """
    Load configuration with paths resolved to absolute paths.

    Args:
        config_name: Name of config file in 00_config/

    Returns:
        dict: Configuration with absolute paths
    """
    root = find_project_root()
    config_path = root / '00_config' / config_name

    with open(config_path) as f:
        config = json.load(f)

    # Resolve all paths to absolute
    if 'paths' in config:
        for key, value in config['paths'].items():
            if isinstance(value, str) and not value.startswith('http'):
                config['paths'][key] = str(root / value)

    # Add project root to config
    config['project_root'] = str(root)

    return config


def setup_environment():
    """
    Setup Python path for imports.
    Call this at the start of each notebook.

    Returns:
        tuple: (project_root, config)
    """
    root = find_project_root()

    # Add project root to Python path for module imports
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    # Load config
    config = load_config()

    return root, config


# Convenience function for notebooks
def init_notebook():
    """
    Initialize notebook environment.

    Usage in notebook:
        from modules.config_loader import init_notebook
        ROOT, CONFIG = init_notebook()

    Returns:
        tuple: (project_root Path, config dict)
    """
    root, config = setup_environment()

    print(f"✅ Project root: {root}")
    print(f"✅ Data directory: {config['paths']['data_dir']}")

    return Path(root), config
