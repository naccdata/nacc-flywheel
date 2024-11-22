"""Utility functions"""

import json
import logging
from typing import Optional

log = logging.getLogger(__name__)


def is_duplicate_record(self, record1: str, record2: str, content_type: Optional[str] = None) -> bool:
    """Check whether the two records are identical.

    Args:
        record1: First record
        record2: Second record

    Returns:
        True if a duplicate detected, else false
    """

    if not content_type or content_type != 'application/json':
        return (record1 == record2)

    try:
        dict1 = sorted(json.loads(record1).items())
        dict2 = sorted(json.loads(record2).items())
        return (dict1 == dict2)
    except json.JSONDecodeError as error:
        log.warning('Error in converting records to JSON format - %s', error)
        return False

    # TODO: Handle other content types
