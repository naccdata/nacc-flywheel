"""Defines project creation functions for calls to Flywheel."""
import logging
import os
from typing import Optional

import flywheel

# This assumes that there is an environment variable
# called "FW_API_KEY" to create the flywheel client from
fw = flywheel.Client(os.environ["FW_API_KEY"], root=True)

log = logging.getLogger()

DRYRUN = True


def fw_find_project(*,
                    project_label: str,
                    group_id: Optional[str] = None) -> list[flywheel.Project]:
    """Finds a flywheel project with a given label, within a group ID if
    specified. Otherwise it's site wide.

    Args:
        project_label: the project label to search for
        group_id: the group ID the project may be in

    Returns:
        existing: a list of all matching projects.
    """
    if group_id:
        existing = fw.projects.find(
            f"parents.group={group_id},label={project_label}")
    else:
        existing = fw.projects.find(f"label={project_label}")
    return existing


def fw_project_exists(*,
                      project_label: str,
                      group_id: Optional[str] = None,
                      single: bool = True) -> bool:
    """Checks to see if a flywheel project exists.

    Args:
        project_label: The label of the proejct to check for
        group_id: the group the project belongs to
        single: allow only one result (T/F)

    Returns:
        True if exists, False if not OR if more than one exists and single = True
    """
    existing = fw_find_project(project_label=project_label, group_id=group_id)
    if not existing:
        return False
    if single and len(existing) > 1:
        return False

    return True


def fw_group_exists(group_id: str) -> bool:
    """Checks to see if a group exists given an id.

    Args:
        group_id: the group ID to search for

    Returns:
        bool: T/F
    """

    group = fw_find_group(group_id)
    if group:
        return True
    return False


def fw_find_group(group_id: str) -> list[flywheel.Group]:
    """Searches for and returns a group if it exists.

    Args:
        group_id: the ID to search for

    Returns:
        group: the group (or empty list if not found)
    """
    group = fw.groups.find(f'_id={group_id}')
    return group


def fw_create_project(*, group: flywheel.Group,
                      project_label: str) -> flywheel.Project:
    """Makes a project given a group id and a project label. Assumes group and
    project items have already been validated.

    if DRYRUN is true, creates a dummy object.

    Args:
        group_id: the ID of the group to create the project in
        project_label: the label of the project to make

    Returns:
        project_ref: the ref of the created project.
    """
    project_ref = f"{group.id}/{project_label}"
    if DRYRUN:
        log.info('Dry Run, would create project %s', project_ref)
        return flywheel.Project(label=project_label,
                                parents={'group': group.id})

    log.info('creating project...')
    group = fw.get_group(group.id)
    project = group.add_project(label=project_label)
    log.info('success')

    return project


def fw_create_group(*,
                    group_id: str,
                    group_label: Optional[str] = None) -> flywheel.Group:
    """Creates a flywheel group given an ID and an option label.

    if DRYRUN is true, creates a dummy object

    Args:
        group_id: the group ID to create
        group_label: the group label to create

    Returns:
        group: the created group
    """

    if not group_label:
        group_label = group_id

    if DRYRUN:
        log.info('Dry Run, would create group %s', group_id)
        return flywheel.Group(label=group_label, id=group_id)

    log.info('creating group...')
    group = fw.add_group(flywheel.Group(group_id, group_label))
    log.info("success")
    return group


def fw_get_or_create_project(
        *,
        project_label: str,
        group_id: Optional[str] = None) -> flywheel.Project:
    """Given a flywheel project label and optional group ID, search for the
    project, and create it if it doesn't exist returns the project, found or
    created.

    Args:
        project_label: the project label to find or create
        group_id: the group id the project is in - required if creating

    Returns:
        project: the found or created project
    """

    project_ref = f"{group_id}/{project_label}"
    if fw_project_exists(project_label=project_label, group_id=group_id):
        log.info('Project %s exists', project_ref)
        project = fw_find_project(project_label=project_label,
                                  group_id=group_id)[0]
        return project

    if not group_id:
        log.error(('No project named %s and no group id provided.'
                   '  Please provide a group ID to create the project in'),
                  project_label)
        return None

    group = fw_get_or_create_group(group_id)
    project = fw_create_project(project_label=project_label, group=group)
    return project


def fw_get_or_create_group(group_id: str) -> flywheel.Group:
    """Given a flywheel group ID, search for the group, and create it if it
    doesn't exist returns the group, found or created.

    Args:
        group_id: the group ID to find or create

    Returns:
        group: the flywheel group found or created
    """
    if not fw_group_exists(group_id):
        group = fw_create_group(group_id=group_id)
    else:
        group = fw_find_group(group_id)[0]
    return group
