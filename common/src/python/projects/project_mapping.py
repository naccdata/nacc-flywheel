"""Mappings from NACC projects and centers to Flywheel groups and projects.

A coordinating center project is a multicenter study that collects data of one
or more datatypes.
For each center, there is a pipeline consisting of ingest and accepted stages.
A center has one ingest stage for each datatype collected by the project that
holds data that has not passed QC and been accepted by center curators.
The accepted stage holds all curated data that has been approved for general
use by the center curators.
This stage consolodates data accepted from ingest for all datatypes.

A Flywheel group is used to represent a center that contains Flywheel projects
for each stage of a project in which the center participates.
The mapping defined in this module is from a project P and center C to
1. one FW group for center C
2. one ingest FW project in this group for each datatype in project P
3. one accepted FW project in this group
The name of project P is used in the names of FW projects unless project P is
the primary project of the coordinating center.

For projects for which data shared externally by the coordinating center, there
is an additional release stage where data across centers is consolodated.
To represent this a project release group is created with a single "master"
project for managing the consolodated data.
"""
import logging
from typing import Optional

import flywheel  # type: ignore
from projects.flywheel_proxy import FlywheelProxy
from projects.project import Center, Project

log = logging.getLogger(__name__)


class ProjectMappingAdaptor:
    """Defines an adaptor for the coordinating center Project class that
    supports mapping to a data pipeline using Flywheel groups and projects."""

    def __init__(self, *, project: Project,
                 flywheel_proxy: FlywheelProxy) -> None:
        """Creates an adaptor mapping the given project to the corresponding
        objects in the flywheel instance linked by the proxy.

        Args:
            project: the domain project
            flywheel_proxy: the proxy for the flywheel instance
        """
        self.__fw = flywheel_proxy
        self.__project = project
        self.__release_group = None

    def has_datatype(self, datatype: str) -> bool:
        """Indicates whether this project has the datatype.

        Args:
            datatype: name of the datatype
        Returns:
            True if datatype is in this project, False otherwise
        """
        return datatype in self.__project.datatypes

    @property
    def datatypes(self):
        """Exposes datatypes of this project."""
        return self.__project.datatypes

    @property
    def name(self):
        """Exposes project name."""
        return self.__project.name

    def build_project_id(self, prefix: str) -> str:
        """Builds a FW project ID string from the given prefix.

        Concatenates the name of the project, if is not the primary
        project of the coordinating center.

        Args:
            prefix: the prefix for the project ID
        """
        assert self.__project
        if self.__project.is_primary():
            return prefix
        return prefix + "-" + self.__project.project_id

    @property
    def accepted_id(self):
        """Builds a project ID for the accepted stage of this project."""
        return self.build_project_id('accepted')

    def get_ingest_id(self, datatype: str) -> Optional[str]:
        """Builds a project ID for the ingest for the data type of this
        project.

        Args:
            datatype: the name of the datatype
        Returns:
            the ingest project ID, or None if datatype is not in this project
        """
        if datatype not in self.__project.datatypes:
            return None

        return self.build_project_id('ingest-' + datatype.lower())

    @property
    def release_id(self):
        """Builds the FW project ID string for the release stage for this
        project."""
        if not self.__project.is_published():
            return None

        return "release-" + self.__project.project_id

    def get_release_group(self) -> Optional[flywheel.Group]:
        """Returns the release group for this project if it is published.
        Otherwise, returns None.

        Returns:
            the release group if project is published, otherwise None
        """
        if not self.__project.is_published():
            return None

        if not self.__release_group:
            self.__release_group = self.__fw.get_group(
                group_label=self.__project.name + " Release",
                group_id=self.release_id)
        return self.__release_group

    def get_master_project(self) -> Optional[flywheel.Project]:
        """Returns the FW consolidation project for this project if it is
        published. Otherwise, returns None.

        Returns:
            the consolidation project if published, otherwise None
        """
        if not self.__project.is_published():
            return None

        return self.__fw.get_project(group=self.get_release_group(),
                                     project_label="master-project")

    def create_center_pipelines(self):
        """Creates data pipelines for centers in this project."""
        if not self.__project.centers:
            log.warning(
                "Not creating center groups for project %s: no centers given",
                self.__project.name)
            return

        for center in self.__project.centers:
            center_adaptor = CenterMappingAdaptor(center=center,
                                                  flywheel_proxy=self.__fw)
            center_adaptor.create_center_pipeline(self.__project)

    def create_release_pipeline(self):
        """Creates the release pipeline for this project if the project is
        published."""
        if not self.__project.is_published():
            log.info("Project %s has no release project", self.__project.name)
            return

        self.get_release_group()
        self.get_master_project()

    def create_project_pipelines(self):
        """Creates the pipelines for this project."""
        self.create_center_pipelines()
        self.create_release_pipeline()


class CenterMappingAdaptor:
    """Defines an adaptor mapping a center to Flywheel groups and projects to
    implement data pipelines for projects."""

    def __init__(self, *, center: Center,
                 flywheel_proxy: FlywheelProxy) -> None:
        """Initializes an adaptor for the given center using the Flywheel
        instance linked by the proxy."""
        self.__center = center
        self.__fw = flywheel_proxy
        self.__group = None

    def get_group(self) -> flywheel.Group:
        """Gets the FW group for this center.

        Uses memoization - gets the group once.

        Returns:
            the Flywheel group for this center
        """
        if not self.__group:
            self.__group = self.__fw.get_group(
                group_label=self.__center.name,
                group_id=self.__center.center_id)
        return self.__group

    def get_accepted_project(
            self,
            project: ProjectMappingAdaptor) -> Optional[flywheel.Project]:
        """Returns the FW project for the accepted stage of the project for
        this center.

        Returns:
            the Flywheel project
        """
        return self.__fw.get_project(group=self.get_group(),
                                     project_label=project.accepted_id)

    def get_ingest_project(self, *, project: ProjectMappingAdaptor,
                           datatype: str) -> Optional[flywheel.Project]:
        """Returns the FW project for the ingest stage of this center for the
        project and datatype. Requires that the center is active in the
        project, and that the datatype is included in the project.

        Returns:
            the ingest FW project, or None if datatype not in project or
            center is not active in project
        """
        if not self.__center.is_active():
            return None
        if not project.has_datatype(datatype):
            return None

        ingest_id = project.get_ingest_id(datatype)
        assert ingest_id

        return self.__fw.get_project(group=self.get_group,
                                     project_label=ingest_id)

    def get_metadata_project(self) -> Optional[flywheel.Project]:
        """Returns the FW project for storing center metadata.

        Returns:
            the FW project
        """
        return self.__fw.get_project(group=self.get_group(),
                                     project_label="metadata")

    def create_ingest_projects(self, project: ProjectMappingAdaptor) -> None:
        """Creates ingest projects for the given project within the group for
        this center.

        Args:
            project: the mapping adaptor for the project
        """
        if not self.__center.is_active():
            log.info("Not creating ingest for inactive center %s",
                     self.__center.name)
            return
        if not project.datatypes:
            log.warning("No ingest groups created for %s: no datatypes given",
                        project.name)
            return

        for datatype in project.datatypes:
            self.get_ingest_project(project=project, datatype=datatype)

    def create_center_pipeline(self, project: ProjectMappingAdaptor) -> None:
        """Creates FW groups and projects for data pipeline of the given
        project in this center.

        Args:
            project: the project mapping adaptor
        """
        self.get_group()
        self.create_ingest_projects(project)
        self.get_accepted_project(project)
        self.get_metadata_project()
