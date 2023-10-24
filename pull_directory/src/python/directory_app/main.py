"""Module for handling user data from directory."""
import logging
from collections import defaultdict
from typing import Any, Dict, List

import yaml
from flywheel import FileSpec, Project
from redcap.nacc_directory import UserDirectoryEntry

log = logging.getLogger(__name__)


def run(*, user_report: List[Dict[str, str]], user_filename: str,
        project: Project, dry_run: bool):
    """Converts user report records to UserDirectoryEntry and saves as list of
    dictionary objects to the project.

    Args:
      user_report: user report records
      user_filename: name of file to create
      project: project to which file is uploaded
    """

    if dry_run:
        log.info('Would write user entries to file %s on project %s',
                 user_filename, project.label)
        return

    entry_map: Dict[str, Any] = {}
    conflicts: Dict[str, List[Any]] = defaultdict(list)
    for user_record in user_report:
        entry = UserDirectoryEntry.create_from_record(user_record)

        if not entry:
            continue

        user_id = entry.credentials['id']
        if user_id not in entry_map.keys():
            entry_map[user_id] = entry.as_dict()
            continue

        conflicts[user_id].append(entry.as_dict())
        conflicts[user_id].append(entry_map.pop(user_id))

    project.upload_file(
        FileSpec(user_filename,
                 contents=yaml.safe_dump(list(entry_map.values()),
                                         allow_unicode=True,
                                         default_flow_style=False),
                 content_type='text/yaml'))

    project.upload_file(
        FileSpec(f"conflicts-{user_filename}",
                 contents=yaml.safe_dump(conflicts,
                                         allow_unicode=True,
                                         default_flow_style=False),
                 content_type='text/yaml'))
