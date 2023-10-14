"""Module for handling user data from directory."""
import logging
from typing import Dict, List

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

    user_entries = []
    for user_record in user_report:
        entry = UserDirectoryEntry.create_from_record(user_record)
        if entry:
            user_entries.append(entry.as_dict())

    project.upload_file(
        FileSpec(user_filename,
                 contents=yaml.safe_dump(user_entries,
                                         allow_unicode=True,
                                         default_flow_style=False),
                 content_type='text/yaml'))
