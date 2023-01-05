"""Provides utilities for pulling input from the OS environment."""
import os
from typing import Optional


def get_api_key() -> Optional[str]:
    """Get the Flywheel API key from environment.

    Returns:
        the API Key if defined. None, otherwise.
    """
    api_key = None
    if 'FW_API_KEY' in os.environ:
        api_key = os.environ['FW_API_KEY']
    return api_key
