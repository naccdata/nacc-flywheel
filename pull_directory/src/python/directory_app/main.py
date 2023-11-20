"""Module for handling user data from directory."""
import logging
from typing import Any, Dict, List

import yaml
from flywheel import FileSpec, Project
from redcap.nacc_directory import UserDirectory, UserDirectoryEntry

log = logging.getLogger(__name__)


def upload_yaml(*, project: Project, filename: str, data: Any):
    """Uploads data as YAML to file on project.
    
    Args:
      project: destination project
      filename: name of file
      data: data object to write as contents
    """
    project.upload_file(
        FileSpec(filename,
                 contents=yaml.safe_dump(data=data,
                                         allow_unicode=True,
                                         default_flow_style=False),
                 content_type='text/yaml'))


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

    directory = UserDirectory()
    for user_record in user_report:
        entry = UserDirectoryEntry.create_from_record(user_record)
        if not entry:
            continue

        directory.add(entry)

    upload_yaml(project=project,
                filename=user_filename,
                data=directory.get_entries())

    upload_yaml(project=project,
                filename=f"conflicts-{user_filename}",
                data=directory.get_conflicts())
