"""Gear context parser for user management."""
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext  # type: ignore

def get_api_key(gear_context: GearToolkitContext) -> Optional[str]:
    """Returns the api key from the gear context if there is one.

    Args:
      gear_context: the gear context
    Returns:
      the API key if exists in context, None otherwise
    """
    api_key_dict = gear_context.get_input('api-key')
    if not api_key_dict:
        return None
    
    return api_key_dict.get('key')
