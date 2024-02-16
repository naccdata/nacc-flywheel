"""Module for handling user data from directory."""
import logging
from typing import Any, Dict, List

import yaml
from flywheel import FileSpec
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from redcap.nacc_directory import UserDirectory, UserDirectoryEntry
from yaml.representer import RepresenterError

log = logging.getLogger(__name__)


def upload_yaml(*, project: ProjectAdaptor, filename: str, data: Any):
    """Uploads data as YAML to file on project.

    Args:
      project: destination project
      filename: name of file
      data: data object to write as contents
    """

    try:
        contents = yaml.safe_dump(data=data,
                                  allow_unicode=True,
                                  default_flow_style=False)
    except RepresenterError as error:
        log.error("Error: can't create YAML for file %s: %s", filename, error)
        return

    project.upload_file(
        FileSpec(filename, contents=contents, content_type='text/yaml'))


def run(*, user_report: List[Dict[str, Any]], user_filename: str,
        project: ProjectAdaptor, dry_run: bool):
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

    entries = [entry.as_dict() for entry in directory.get_entries()]
    if entries:
        upload_yaml(project=project, filename=user_filename, data=entries)

    # TODO: figure out why conflicts are causing file errors
    # this will flag conflicts
    directory.get_conflicts()
    # conflicts = directory.get_conflicts()
    # if conflicts:
    #     upload_yaml(project=project,
    #                 filename=f"conflicts-{user_filename}",
    #                 data=conflicts)
