"""Defines project creation functions for calls to Flywheel."""
import logging
from typing import List

import flywheel

log = logging.getLogger()


class FlywheelProxy:
    """Defines a proxy object for group and project creation on a Flywheel
    instance."""

    def __init__(self, api_key: str, dry_run: bool = True) -> None:
        self.__fw = flywheel.Client(api_key, root=True)
        self.__dry_run = dry_run

    @property
    def dry_run(self):
        """Indicates whether proxy is set for a dry run."""
        return self.__dry_run

    def find_project(self, *, group_id: str,
                     project_label: str) -> List[flywheel.Project]:
        """Finds a flywheel project with a given label, within a group ID if
        specified. Otherwise it's site wide.

        Args:
            project_label: the project label to search for
            group_id: the group ID the project may be in

        Returns:
            existing: a list of all matching projects.
        """
        return self.__fw.projects.find(
            f"parents.group={group_id},label={project_label}")

    def find_group(self, group_id: str) -> List[flywheel.Group]:
        """Searches for and returns a group if it exists.

        Args:
            group_id: the ID to search for

        Returns:
            group: the group (or empty list if not found)
        """
        return self.__fw.groups.find(f'_id={group_id}')

    def get_group(self, *, group_id: str, group_label: str) -> flywheel.Group:
        """Returns the flywheel group with the given ID and label.

        If the group already exists, returns that group.
        Otherwise, creates a new group.

        if self.dry_run is true, creates a dummy object

        Args:
          group_id: the group ID to create
          group_label: the group label to create

        Returns:
          group: the created group
        """
        group = self.find_group(group_id)
        if group:
            return group[0]

        if self.__dry_run:
            log.info('Dry Run, would create group %s', group_id)
            return flywheel.Group(label=group_label, id=group_id)

        log.info('creating group...')
        # This just returns a string of the group ID
        group = self.__fw.add_group(flywheel.Group(group_id, group_label))
        # we must fw.get_group() with ID string to get the actual Group object.
        group = self.__fw.get_group(group)
        log.info("success")

        return group

    def get_project(self, *, group: flywheel.Group,
                    project_label: str) -> flywheel.Project:
        """Given a flywheel project label and optional group ID, search for the
        project, and create it if it doesn't exist returns the project, found
        or created.

        Args:
            project_label: the project label to find or create
            group_id: the group id the project is in - required if creating

        Returns:
            project: the found or created project
        """
        existing_projects = self.find_project(group_id=group.id,
                                              project_label=project_label)
        if existing_projects and len(existing_projects) == 1:
            project_ref = f"{group.id}/{project_label}"
            log.info('Project %s exists', project_ref)
            return existing_projects[0]

        if not group:
            log.error(('No project named %s and no group id provided.'
                       '  Please provide a group ID to create the project in'),
                      project_label)
            return None

        project_ref = f"{group.id}/{project_label}"
        if self.__dry_run:
            log.info('Dry Run: would create project %s', project_ref)
            return flywheel.Project(label=project_label,
                                    parents={'group': group.id})

        log.info('creating project...')
        project = group.add_project(label=project_label)
        log.info('success')

        return project
