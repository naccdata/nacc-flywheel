"""Module for handling user data from directory."""
import logging
from typing import Any, Dict, List

import yaml
from users.nacc_directory import UserEntry

log = logging.getLogger(__name__)


def run(*, user_report: List[Dict[str, Any]]) -> str:
    """Converts user report records to UserDirectoryEntry and saves as list of
    dictionary objects to the project.

    Args:
      user_report: user report records
    """

    user_map = {}
    for user_record in user_report:
        entry = UserEntry.create_from_record(user_record)
        if not entry:
            continue

        if entry.email in user_map:
            log.warning('Email %s occurs in more than one contact', entry.email)
        

        user_map[entry.email] = entry

    entries = [entry.as_dict() for entry in user_map.values()]

    return yaml.safe_dump(data=entries,
                          allow_unicode=True,
                          default_flow_style=False)
