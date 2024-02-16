"""Mappings from NACC studies and centers to Flywheel groups and projects.

A coordinating center study is a multi-center study that collects data of one
or more datatypes.
For each center, there is a pipeline consisting of ingest and accepted stages.
A center has one ingest stage for each datatype collected by the study that
holds data that has not passed QC and been accepted by center curators.
The accepted stage holds all curated data that has been approved for general
use by the center curators.
This stage consolidates data accepted from ingest for all datatypes.

A Flywheel group is used to represent a center that contains Flywheel projects
for each stage of a study in which the center participates.
The mapping defined in this module is from a study P and center C to
1. one FW group for center C
2. one ingest and one sandbox FW project in this group for each datatype in
   study P
3. one accepted FW project in this group
The name of study P is used in the names of FW projects unless study P is
the primary study of the coordinating center.

For studies for which data shared externally by the coordinating center, there
is an additional release stage where data across centers is consolidated.
To represent this a study release group is created with a single "master"
project for managing the consolidated data.
"""
import logging
from typing import Dict, List, Optional

from centers.center_group import CenterGroup
from centers.nacc_group import NACCGroup
from flywheel import AccessPermission
from flywheel.models.group_role import GroupRole
from flywheel_adaptor.flywheel_proxy import (FlywheelProxy, GroupAdaptor,
                                             ProjectAdaptor)
from projects.study import Study

log = logging.getLogger(__name__)


class StudyMappingAdaptor:
    """Defines an adaptor for the coordinating center Study class that supports
    mapping to a data pipeline using Flywheel groups and projects."""

    def __init__(self,
                 *,
                 study: Study,
                 nacc_group: NACCGroup,
                 flywheel_proxy: FlywheelProxy,
                 admin_access: Optional[List[AccessPermission]] = None,
                 center_roles: List[GroupRole],
                 new_only: bool) -> None:
        """Creates an adaptor mapping the given study to the corresponding
        objects in the flywheel instance linked by the proxy.

        Args:
            study: the study
            flywheel_proxy: the proxy for the flywheel instance
            admin_access: the access permissions for administrative users
            center_roles: the roles for center users
            new_only: whether to only process new centers
        """
        self.__fw = flywheel_proxy
        self.__study = study
        self.__nacc_group = nacc_group
        self.__release_group: Optional[GroupAdaptor] = None
        self.__admin_access = admin_access
        self.__center_roles = center_roles
        self.__new_centers_only = new_only

    def has_datatype(self, datatype: str) -> bool:
        """Indicates whether this study has the datatype.

        Args:
            datatype: name of the datatype
        Returns:
            True if datatype is in this study, False otherwise
        """
        return datatype in self.__study.datatypes

    @property
    def datatypes(self) -> List[str]:
        """Exposes datatypes of this study."""
        return self.__study.datatypes

    @property
    def name(self) -> str:
        """Exposes study name."""
        return self.__study.name

    def build_project_label(self, prefix: str) -> str:
        """Builds a FW project label string from the given prefix.

        Concatenates the name of the study, if is not the primary
        study of the coordinating center.

        Args:
            prefix: the prefix for the project label
        Returns:
          the project label built using prefix
        """
        assert self.__study
        if self.__study.is_primary():
            return prefix
        return prefix + "-" + self.__study.study_id

    @property
    def accepted_label(self) -> str:
        """Builds a project label for the accepted stage of this study."""
        return self.build_project_label('accepted')

    @property
    def release_label(self) -> Optional[str]:
        """Builds the FW project ID string for the release stage for this
        study."""
        if not self.__study.is_published():
            return None

        return "release-" + self.__study.study_id

    def get_release_group(self) -> Optional[GroupAdaptor]:
        """Returns the release group for this study if it is published.
        Otherwise, returns None.

        Returns:
            the release group if study is published, otherwise None
        """
        if not self.__study.is_published():
            return None

        release_id = self.release_label
        assert release_id
        if not self.__release_group:
            group = self.__fw.get_group(group_label=self.__study.name +
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
        if not self.__study.is_published():
            return None

        release_group = self.get_release_group()
        assert release_group
        return release_group.get_project(label='master-project')

    def create_center_pipelines(self) -> None:
        """Creates data pipelines for centers in this project."""
        if not self.__study.centers:
            log.warning(
                "Not creating center groups for project %s: no centers given",
                self.__study.name)
            return

        for center in self.__study.centers:
            if self.__new_centers_only and 'new-center' not in center.tags:
                continue

            center_group = CenterGroup.create_from_center(center=center,
                                                          proxy=self.__fw)
            center_group.add_roles(self.__center_roles)
            self.__nacc_group.add_center(center_group)

            if self.__admin_access:
                center_group.add_permissions(self.__admin_access)

            if center.is_active():
                ingest_projects = self.create_ingest_projects(
                    center_group, label_prefix='ingest')
                sandbox_projects = self.create_ingest_projects(
                    center_group, label_prefix='sandbox')

            self.create_ingest_projects(center_group,
                                        label_prefix='retrospective')

            center_group.get_project(label=self.accepted_label)
            center_group.get_project(label='metadata')
            center_group.get_project(label='center-portal')

            center_group.publish_projects(
                projects=[ingest_projects, sandbox_projects])

    def create_ingest_projects(self, center_group: CenterGroup,
                               label_prefix: str) -> Dict[str, ProjectAdaptor]:
        """Creates projects for ingesting a particular datatype.

        Args:
        center_adaptor: the mapping for the center
        label_prefix: the prefix for project names
        Returns:
        Map from datatype to project
        """
        project_map = {}
        for datatype in self.datatypes:
            project_label = self.build_project_label(label_prefix + '-' +
                                                     datatype.lower())
            assert project_label

            ingest_project = center_group.get_project(label=project_label)
            if ingest_project:
                project_map[datatype] = ingest_project
                ingest_project.add_tags(center_group.get_tags())

        return project_map

    def create_release_pipeline(self) -> None:
        """Creates the release pipeline for this study if the study is
        published."""
        if not self.__study.is_published():
            log.info("Study %s has no release project", self.__study.name)
            return

        release_group = self.get_release_group()
        master_project = self.get_master_project()

        if self.__study.is_published() and self.__admin_access:
            assert release_group
            for permission in self.__admin_access:
                release_group.add_user_access(permission)

            assert master_project
            master_project.add_admin_users(self.__admin_access)

    def create_study_pipelines(self) -> None:
        """Creates the pipelines for this study."""
        self.create_center_pipelines()
        self.create_release_pipeline()
