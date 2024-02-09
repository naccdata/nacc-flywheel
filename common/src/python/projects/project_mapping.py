"""Mappings from NACC projects and centers to Flywheel groups and projects.

A coordinating center project is a multi-center study that collects data of one
or more datatypes.
For each center, there is a pipeline consisting of ingest and accepted stages.
A center has one ingest stage for each datatype collected by the project that
holds data that has not passed QC and been accepted by center curators.
The accepted stage holds all curated data that has been approved for general
use by the center curators.
This stage consolidates data accepted from ingest for all datatypes.

A Flywheel group is used to represent a center that contains Flywheel projects
for each stage of a project in which the center participates.
The mapping defined in this module is from a project P and center C to
1. one FW group for center C
2. one ingest and one sandbox FW project in this group for each datatype in
   project P
3. one accepted FW project in this group
The name of project P is used in the names of FW projects unless project P is
the primary project of the coordinating center.

For projects for which data shared externally by the coordinating center, there
is an additional release stage where data across centers is consolidated.
To represent this a project release group is created with a single "master"
project for managing the consolidated data.
"""
import logging
from typing import Dict, List, Optional

from centers.center_group import CenterGroup
from flywheel import AccessPermission
from flywheel.models.group_role import GroupRole
from flywheel_adaptor.flywheel_proxy import (FlywheelProxy, GroupAdaptor,
                                             ProjectAdaptor)
from projects.project import Center, Project

log = logging.getLogger(__name__)


class ProjectMappingAdaptor:
    """Defines an adaptor for the coordinating center Project class that
    supports mapping to a data pipeline using Flywheel groups and projects."""

    def __init__(self,
                 *,
                 project: Project,
                 flywheel_proxy: FlywheelProxy,
                 admin_access: Optional[List[AccessPermission]] = None,
                 center_roles: List[GroupRole],
                 new_only: bool) -> None:
        """Creates an adaptor mapping the given project to the corresponding
        objects in the flywheel instance linked by the proxy.

        Args:
            project: the domain project
            flywheel_proxy: the proxy for the flywheel instance
            admin_access: the access permissions for administrative users
            center_roles: the roles for center users
            new_only: whether to only process new centers
        """
        self.__fw = flywheel_proxy
        self.__project = project
        self.__release_group: Optional[GroupAdaptor] = None
        self.__admin_access = admin_access
        self.__center_roles = center_roles
        self.__new_centers_only = new_only

    def has_datatype(self, datatype: str) -> bool:
        """Indicates whether this project has the datatype.

        Args:
            datatype: name of the datatype
        Returns:
            True if datatype is in this project, False otherwise
        """
        return datatype in self.__project.datatypes

    @property
    def datatypes(self) -> List[str]:
        """Exposes datatypes of this project."""
        return self.__project.datatypes

    @property
    def name(self) -> str:
        """Exposes project name."""
        return self.__project.name

    def build_project_label(self, prefix: str) -> str:
        """Builds a FW project ID string from the given prefix.

        Concatenates the name of the project, if is not the primary
        project of the coordinating center.

        Args:
            prefix: the prefix for the project ID
        Returns:
          the project id built using prefix
        """
        assert self.__project
        if self.__project.is_primary():
            return prefix
        return prefix + "-" + self.__project.project_id

    @property
    def accepted_label(self) -> str:
        """Builds a project ID for the accepted stage of this project."""
        return self.build_project_label('accepted')

    def get_ingest_label(self, datatype: str) -> Optional[str]:
        """Builds a project ID for the ingest for the data type of this
        project.

        Args:
            datatype: the name of the datatype
        Returns:
            the ingest project ID, or None if datatype is not in this project
        """
        if datatype not in self.__project.datatypes:
            return None

        return self.build_project_label('ingest-' + datatype.lower())

    @property
    def release_label(self) -> Optional[str]:
        """Builds the FW project ID string for the release stage for this
        project."""
        if not self.__project.is_published():
            return None

        return "release-" + self.__project.project_id

    def get_release_group(self) -> Optional[GroupAdaptor]:
        """Returns the release group for this project if it is published.
        Otherwise, returns None.

        Returns:
            the release group if project is published, otherwise None
        """
        if not self.__project.is_published():
            return None

        release_id = self.release_label
        assert release_id
        if not self.__release_group:
            group = self.__fw.get_group(group_label=self.__project.name +
                                        " Release",
                                        group_id=release_id)
            assert group
            self.__release_group = GroupAdaptor(group=group, proxy=self.__fw)
        return self.__release_group

    def get_master_project(self) -> Optional[ProjectAdaptor]:
        """Returns the FW consolidation project for this project if it is
        published. Otherwise, returns None.

        Returns:
            the consolidation project if published, otherwise None
        """
        if not self.__project.is_published():
            return None

        release_group = self.get_release_group()
        assert release_group
        project = release_group.get_project(label='master-project')
        if not project:
            return None

        return ProjectAdaptor(project=project, proxy=self.__fw)

    def create_center_pipelines(self) -> None:
        """Creates data pipelines for centers in this project."""
        if not self.__project.centers:
            log.warning(
                "Not creating center groups for project %s: no centers given",
                self.__project.name)
            return

        for center in self.__project.centers:
            if self.__new_centers_only and 'new-center' not in center.tags:
                continue

            center_adaptor = CenterMappingAdaptor(
                center=center,
                flywheel_proxy=self.__fw,
                admin_access=self.__admin_access,
                center_roles=self.__center_roles)
            center_adaptor.create_center_pipeline(self)

    def create_release_pipeline(self) -> None:
        """Creates the release pipeline for this project if the project is
        published."""
        if not self.__project.is_published():
            log.info("Project %s has no release project", self.__project.name)
            return

        release_group = self.get_release_group()
        master_project = self.get_master_project()

        if self.__project.is_published() and self.__admin_access:
            assert release_group
            for permission in self.__admin_access:
                release_group.add_user_access(permission)

            assert master_project
            master_project.add_admin_users(self.__admin_access)

    def create_project_pipelines(self) -> None:
        """Creates the pipelines for this project."""
        self.create_center_pipelines()
        self.create_release_pipeline()


class CenterMappingAdaptor:
    """Defines an adaptor mapping a center to Flywheel groups and projects to
    implement data pipelines for projects."""

    def __init__(self,
                 *,
                 center: Center,
                 flywheel_proxy: FlywheelProxy,
                 admin_access: Optional[List[AccessPermission]] = None,
                 center_roles: Optional[List[GroupRole]]) -> None:
        """Initializes an adaptor for the given center using the Flywheel
        instance linked by the proxy.

        Args:
          center: the center object
          flywheel_proxy: the flywheel instance proxy
          admin_access: the administrative users from admin group
          template_map: template projects for project resources
          center_roles: the list of custom roles for user in center
        """
        self.__center = center
        self.__fw = flywheel_proxy
        self.__group: Optional[CenterGroup] = None
        self.__admin_access = admin_access
        self.__center_roles = center_roles

    def get_group(self) -> CenterGroup:
        """Gets the FW group for this center.

        Uses memoization - gets the group once.

        Returns:
            the Flywheel group for this center
        """
        if not self.__group:
            group = self.__fw.get_group(group_label=self.__center.name,
                                        group_id=self.__center.center_id)
            self.__group = CenterGroup(group=group, proxy=self.__fw)
        return self.__group

    def get_project(self, label: str) -> Optional[ProjectAdaptor]:
        """Creates a project with the given label in the group.

        If the project already exists, returns that project.

        Args:
          label: the project label
        Returns:
          ProjectAdaptor for the project.
        """
        center_group = self.get_group()
        project = center_group.get_project(label=label)
        if not project:
            return None

        return ProjectAdaptor(project=project, proxy=self.__fw)

    def create_ingest_projects(self, project: ProjectMappingAdaptor,
                               label_prefix: str) -> Dict[str, ProjectAdaptor]:
        """Creates projects for ingesting a particular datatype.

        Args:
          project: the mapping for the study
          label_prefix: the prefix for project names
        Returns:
          Map from datatype to project
        """
        project_map = {}
        for datatype in project.datatypes:
            project_label = project.build_project_label(label_prefix + '-' +
                                                        datatype.lower())
            assert project_label

            ingest_project = self.get_project(label=project_label)

            if ingest_project:
                project_map[datatype] = ingest_project
                self.add_tags(ingest_project)

        return project_map

    def add_tags(self, project: ProjectAdaptor) -> None:
        """Adds tags from this center to the project.

        Note: requires that tag is enabled in the group for the center.

        Args:
          project: the project to add tags to
        """
        for tag in self.__center.tags:
            project.add_tag(tag)

    def create_center_pipeline(self, project: ProjectMappingAdaptor) -> None:
        """Creates FW groups and projects for data pipeline of the given
        project in this center.

        Args:
            project: the project mapping adaptor
        """
        center_group = self.get_group()
        for tag in self.__center.tags:
            if tag not in center_group.get_tags():
                center_group.add_tag(tag)
        if self.__center_roles:
            for role in self.__center_roles:
                center_group.add_role(role)
        if self.__admin_access:
            for permission in self.__admin_access:
                center_group.add_user_access(permission)

        if self.__center.is_active():
            self.create_ingest_projects(project, label_prefix='ingest')
            self.create_ingest_projects(project, label_prefix='sandbox')

        self.create_ingest_projects(project, label_prefix='retrospective')

        self.get_project(label=project.accepted_label)
        self.get_project(label='metadata')
