"""Reads a YAML file with project info.

project - name of project
centers - array of centers
    center-id - "ADC" ID of center (protected info)
    name - name of center
    is-active - whether center is active, has users if True
datatypes - array of datatype names (form, dicom)
published - boolean indicating whether data is to be published
"""
import logging

import yaml
from projects.project import Center, Project, ProjectVisitor


def create_group(*, group_label: str, group_id: str) -> str:
    """Creates FW group with label and ID.

    Args:
      group_label: the name of the project to be created
      group_id: the id for the group
    Returns:
      the ID of the FW group
    """
    logging.info("Creating group %s with id %s", group_label, group_id)
    print(f"group label: {group_label}")
    print(f"group ID: {group_id}")
    return group_id


def create_project(*, group_id: str, project_id: str,
                   project_label: str) -> None:
    """Creates FW project w/in group with given name.

    Args:
      group_id: the group
      project_id: the name of the project
      project_label: the display name of the project
    """
    project_ref = f"fw://{group_id}/{project_id}"
    logging.info("Creating project %s with id %s", project_label, project_ref)
    print(f"project: {project_ref}")
    print(f"project name: {project_label}")


class FlywheelProjectArtifactCreator(ProjectVisitor):
    """Creates project artifacts in Flywheel."""

    def __init__(self) -> None:
        """Inititializes visitor with FW instance details."""
        self.__current = None
        self.__ingest_group_id = None
        self.__accepted_group_id = None

    def __create_group(self, extension: str) -> str:
        group_id = self.__current.project_id + "-" + extension.lower()
        create_group(group_label=self.__current.name + " " + extension,
                     group_id=group_id)
        return group_id

    def visit_center(self, center: "Center"):
        """Creates project in FW instance."""
        if not self.__current:
            logging.error("No project given")
            return
        if not self.__accepted_group_id:
            self.__accepted_group_id = self.__create_group("Accepted")
        create_project(group_id=self.__accepted_group_id,
                       project_id=center.center_id,
                       project_label=center.name)

    def visit_project(self, project: "Project"):
        """Creates groups in FW instance:

        - one ingest groups for each datatype for each center
        - one "accepted" groups for each center
        - "release" group for project if project.published
        """
        self.__current = project

        if project.datatypes:
            for datatype in project.datatypes:
                self.visit_datatype(datatype)
        else:
            logging.warning(
                "Not creating ingest group for project %s, which has no datatypes",
                project.name)

        if project.centers:
            for center in project.centers:
                center.apply(self)
        else:
            logging.warning(
                "Not creating accepted group for project %s, which has no centers",
                project.name)

        if project.published:
            self.__create_group("Release")
        else:
            logging.info("Project %s has no release project", project.name)

        self.__current = None
        self.__accepted_group_id = None
        self.__ingest_group_id = None

    def visit_datatype(self, datatype: str):
        if not self.__current:
            logging.error("No project given")
            return
        if not self.__ingest_group_id:
            self.__ingest_group_id = self.__create_group("Ingest")

        for center in self.__current.centers:
            project_label = center.name + " " + datatype + " ingest"
            project_id = center.center_id + "-" + datatype
            create_project(group_id=self._ingest_group_id,
                           project_id=project_id,
                           project_label=project_label)


def main():
    with open("adrc_program.yaml", 'r', encoding='utf-8') as stream:
        project_dict = yaml.load(stream)

    project = Project.create(project_dict)
    project.apply(FlywheelProjectArtifactCreator())


if __name__ == "__main__":
    main()
