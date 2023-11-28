"""Defines project creation functions for calls to Flywheel."""
import json
import logging
from typing import List, Mapping, Optional

import flywheel
from flywheel import (Client, ContainerIdViewInput, DataView, GearRule,
                      GearRuleInput, RolesRole, ViewIdOutput)
from flywheel.models.project_parents import ProjectParents
from flywheel_adaptor.group_adaptor import GroupAdaptor
from fw_client import FWClient
from fw_utils import AttrDict

log = logging.getLogger(__name__)


# pylint: disable=(too-many-public-methods)
class FlywheelProxy:
    """Defines a proxy object for group and project creation on a Flywheel
    instance."""

    def __init__(self,
                 client: Client,
                 fw_client: Optional[FWClient] = None,
                 dry_run: bool = True) -> None:
        """Initializes a flywheel proxy object.

        Args:
          client: the Flywheel SDK client
          fw-client: the fw-client client
          dry_run: whether proxy will be used for a dry run
        """
        self.__fw = client
        self.__fw_client = fw_client
        self.__dry_run = dry_run
        self.__project_roles: Optional[Mapping[str, RolesRole]] = None
        self.__project_admin_role: Optional[RolesRole] = None

    @property
    def dry_run(self):
        """Indicates whether proxy is set for a dry run.

        Returns:
            True if proxy is set for a dry run. False otherwise.
        """
        return self.__dry_run

    def find_projects(self, *, group_id: str,
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

    def find_groups(self, group_id: str) -> List[flywheel.Group]:
        """Searches for and returns a group if it exists.

        Args:
            group_id: the ID to search for

        Returns:
            the group (or empty list if not found)
        """
        return self.__fw.groups.find(f'_id={group_id}')

    def find_group(self, group_id: str) -> Optional[GroupAdaptor]:
        """Returns group for group id.

        Args:
          group_id: the group ID
        Returns:
          group with ID if exists, None otherwise
        """
        groups = self.find_groups(group_id)
        if not groups:
            return None

        return GroupAdaptor(group=groups[0], proxy=self)

    def find_groups_by_tag(self, tag_pattern: str) -> List[flywheel.Group]:
        """Searches for groups with tags matching the pattern.

        Args:
          tag_pattern: raw string regex pattern

        Returns:
          the list of groups
        """
        return self.__fw.groups.find(f"tags=~{tag_pattern}")

    def find_user(self, user_id: str) -> Optional[flywheel.User]:
        """Searches for and returns a user if it exists.

        Args:
            user_id: the ID to search for

        Returns:
            a list with the user, or None if not found
        """
        return self.__fw.users.find_first(f'_id={user_id}')

    def add_user(self, user: flywheel.User) -> str:
        """Adds the user and returns the user id.

        Note: the user ID and email have to be the same here.
        Update using set_user_email after the user has been added.

        Args:
          user: the user to add
        Returns:
          the user id for the user added
        """
        if self.dry_run:
            log.info('Dry run: would create user %s', user.id)
            assert user.id
            return user.id

        return self.__fw.add_user(user)

    def set_user_email(self, user: flywheel.User, email: str) -> None:
        """Sets user email on client.

        Args:
          user: local instance of user
          email: email address to set
        """
        assert user.id
        if self.dry_run:
            log.info('Dry run: would set user %s email to %s', user.id, email)
            return

        self.__fw.modify_user(user.id, {'email': email})

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
        group_list = self.find_groups(group_id)
        if group_list:
            return group_list[0]

        if self.__dry_run:
            log.info('Dry Run: would create group %s', group_id)
            return flywheel.Group(label=group_label, id=group_id)

        log.info('creating group...')
        # This just returns a string of the group ID
        added_group_id = self.__fw.add_group(
            flywheel.Group(group_id, group_label))
        # we must fw.get_group() with ID string to get the actual Group object.
        group = self.__fw.get_group(added_group_id)
        log.info("success")

        return group

    def get_project(self, *, group: flywheel.Group,
                    project_label: str) -> Optional[flywheel.Project]:
        """Given a flywheel project label and optional group ID, search for the
        project, and create it if it doesn't exist returns the project, found
        or created.

        Args:
            project_label: the project label to find or create
            group_id: the group id the project is in - required if creating

        Returns:
            project: the found or created project
        """
        group_id = group.id
        assert group_id
        existing_projects = self.find_projects(group_id=group_id,
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
                                    parents=ProjectParents(group=group.id))

        log.info('creating project %s', project_ref)
        project = group.add_project(label=project_label)
        log.info('success')

        return project

    def get_roles(self) -> Mapping[str, RolesRole]:
        """Gets all roles for the FW instance.

        Does not include GroupRoles.
        """
        if not self.__project_roles:
            all_roles = self.__fw.get_all_roles()
            self.__project_roles = {role.label: role for role in all_roles}
        return self.__project_roles

    def get_role(self, label: str) -> Optional[RolesRole]:
        """Gets project role with label.

        Args:
          label: the name of the role
        Returns:
          the role with the name if one exists. None, otherwise
        """
        role_map = self.get_roles()
        return role_map.get(label)

    def get_admin_role(self) -> Optional[RolesRole]:
        """Gets admin role."""
        if not self.__project_admin_role:
            self.__project_admin_role = self.get_role('admin')
        return self.__project_admin_role

    def add_group_role(self, *, group: flywheel.Group,
                       role: RolesRole) -> None:
        """Add role to the group.

        Args:
          group: the group
          role: the role
        """
        if role.id in group.roles:
            return

        if self.dry_run:
            log.info("Dry run: would add role %s to group %s", role.id,
                     group.label)
            return

        self.__fw.add_role_to_group(group.id, role)

    def get_project_gear_rules(self,
                               project: flywheel.Project) -> List[GearRule]:
        """Get the gear rules from the given project.

        Args:
          project: the flywheel project

        Returns:
          the gear rules
        """
        return self.__fw.get_project_rules(project.id)

    def add_project_rule(self, *, project: flywheel.Project,
                         rule_input: GearRuleInput) -> None:
        """Forwards call to the FW client."""
        if self.dry_run:
            log.info('Would add rule %s to project %s', rule_input,
                     project.label)
            return

        self.__fw.add_project_rule(project.id, rule_input)

    def remove_project_gear_rule(self, *, project: flywheel.Project,
                                 rule: GearRule) -> None:
        """Removes the gear rule from the project.

        Args:
          project: the project
          rule: the gear rule
        """
        if self.dry_run:
            log.info('Dry run: would remove rule %s from project %s',
                     rule.name, project.label)
            return

        self.__fw.remove_project_rule(project.id, rule.id)

    def get_dataviews(self, project: flywheel.Project) -> List[DataView]:
        """Get the dataviews for the project.

        Args:
          project: the project
        Returns:
          the dataviews for the project
        """

        dataviews = self.__fw.get_views(project.id)
        return [view for view in dataviews if view.parent != "site"]

    def add_dataview(self, *, project: flywheel.Project,
                     viewinput: ContainerIdViewInput) -> ViewIdOutput:
        """Adds the data view to the enclosed project.

        Args:
          project: the project to which to add the data view
          viewinput: the object representing the data view
        """
        # TODO: setup dry run for add_dataview
        # if self.dry_run:
        #     log.info("Dry run: would add %s to project %s", viewinput,
        #              project.label)
        #     return ""

        return self.__fw.add_view(project.id, viewinput)

    def modify_dataview(self, *, source: DataView,
                        destination: DataView) -> None:
        """Updates the destination data view by copying from the source view.

        Args:
          source: the source DataView
          destination: the DataView to modify
        """
        if self.dry_run:
            # TODO: add detail to dry run message
            log.info('Dry run: would modify data view')
            return

        temp_id = source._id  # pylint: disable=(protected-access)
        temp_parent = source.parent
        source._id = None  # pylint: disable=(protected-access)
        source.parent = destination.parent
        self.__fw.modify_view(destination.id, source)
        source._id = temp_id  # pylint: disable=(protected-access)
        source.parent = temp_parent

    def delete_dataview(self, view: DataView) -> bool:
        """Removes the indicated dataview.

        Args:
          view: the dataview to remove
        Returns:
          True if the dataview is deleted, False otherwise
        """
        if self.dry_run:
            log.info('Dry run: would delete dataview %s', view)
            return False

        result = self.__fw.delete_view(view.id)
        return bool(result.deleted)

    # def get_project_apps(self, project: flywheel.Project) -> List[ViewerApp]:
    #     """Returns the viewer apps for the project.

    #     Args:
    #       project: the project
    #     Returns:
    #       The list of apps for the project
    #     """
    #     settings = self.__fw.get_project_settings(project.id)
    #     if not settings:
    #         return []

    #     return settings.viewer_apps

    def get_project_settings(self, project: flywheel.Project) -> AttrDict:
        """Returns the settings object for the project.

        Args:
          project: the project
        Returns:
          the project settings
        """
        assert self.__fw_client, "Requires FWClient to be instantiated"
        return self.__fw_client.get(
            f"/api/projects/{project.id}/settings")  # type: ignore

    def set_project_settings(self, *, project: flywheel.Project,
                             settings: AttrDict) -> None:
        """Sets the project settings to the argument.

        Args:
          project: the project
          settings: the settings dictionary
        """
        assert self.__fw_client, "Requires FWClient to be instantiated"
        self.__fw_client.put(url=f"/api/projects/{project.id}/settings",
                             data=json.dumps(settings))

    def get_project_apps(self, project: flywheel.Project) -> List[AttrDict]:
        """Returns the viewer apps for the project.

        Note: Temporary fix using FWClient because flywheel-sdk doesn't manage
        type of viewer_apps.

        Args:
          project: the project
        """
        settings = self.get_project_settings(project)
        if not settings:
            return []

        return settings.viewer_apps  # type: ignore

    # def set_project_apps(self, *, project: flywheel.Project,
    #                      apps: List[ViewerApp]):
    #     """Sets the apps to the project settings to the list of apps.

    #     Note: this will replace any existing apps

    #     Args:
    #       project: the project
    #       apps: the list of viewer apps
    #     """
    #     if self.dry_run:
    #         log.info('Dry run: would set viewer %s in project %s', apps,
    #                  project.label)
    #         return

    #     self.__fw.modify_project_settings(project.id, {"viewer_apps": apps})

    def set_project_apps(self, *, project: flywheel.Project,
                         apps: List[AttrDict]) -> None:
        """Sets the viewer apps of the project to the list of apps.

        Note: this will replace any existing apps.

        Note: temporary fix using FWCliennt because flywheel-sdk doesn't manage
        type of viewer_apps.

        Args:
          project: the project
          apps: the list of viewer apps
        """
        assert self.__fw_client, "Requires FWClient to be instantiated"
        if self.dry_run:
            log.info('Dry run: would set viewer %s in project %s', apps,
                     project.label)
            return

        settings = self.get_project_settings(project)
        if not settings:
            log.warning('Project %s has no settings', project.label)
            return

        settings['viewer_apps'] = apps  # type: ignore
        self.set_project_settings(project=project, settings=settings)

    def get_site(self):
        """Returns URL for site of this instance."""
        return self.__fw.get_config()["site"]["redirect_url"]
