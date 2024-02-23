"""Module for handling user data from directory."""
import logging
from typing import Any, Dict, List

import yaml
from redcap.nacc_directory import UserDirectory, UserDirectoryEntry

log = logging.getLogger(__name__)


def run(*, user_report: List[Dict[str, Any]]) -> str:
    """Converts user report records to UserDirectoryEntry and saves as list of
    dictionary objects to the project.

    Args:
      user_report: user report records
    """

    directory = UserDirectory()
    for user_record in user_report:
        entry = UserDirectoryEntry.create_from_record(user_record)
        if not entry:
            continue

        directory.add(entry)

    entries = [entry.as_dict() for entry in directory.get_entries()]

    # this call logs any conflicts
    directory.get_conflicts()
    # TODO: want to write to metadata for userfile instead

    return yaml.safe_dump(data=entries,
                          allow_unicode=True,
                          default_flow_style=False)
