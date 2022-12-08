"""Reads a YAML file with project info.

project - name of project
centers - array of centers
    center-id - "ADC" ID of center (protected info)
    name - name of center
    is-active - whether center is active, has users if True
datatypes - array of datatype names (form, dicom)
published - boolean indicating whether data is to be published
"""
import argparse
import logging
from pathvalidate import ValidationError, validate_filename, sanitize_filename
import sys

import yaml
import flywheel
from flywheel import ApiException

from projects.project import Center, Project, ProjectVisitor, convert_to_slug


DRYRUN = True


def sanitize_name(name: str, groupid: bool = False) -> str:
    """ Sanitizes a name for flywheel

    Flywheel name/label requirments are that it must be less than 64 characters,
    and group ids can include lowercase letters, numbers, dashes, and underscores as long as it’s unique.

    Args:
        name: the name to be sanitized
        groupid: boolean indicating if the name is a group ID or not (which has special sanitation rules)

    Returns:
        safe_name: the new sanitized name for the container/group that's safe for flywheel

    """

    safe_name = ""
    if groupid:
        # Group ID can include lowercase letters, numbers, dashes, and underscores as long as it’s unique.
        modname = name.lower() # Convert to lowercase
        modname = modname.replace(" ", "_") # Replace spaces with dashes
        for c in modname:
            safe_name += c if c.isalnum() or c in ['-','_'] else ""

    else:
        safe_name = name[:64]

    if safe_name != name:
        logging.info(f"changed from {name} to {safe_name}")

    return safe_name

def flywheel_path_exists(fwpath: str, fw: flywheel.Client) -> bool:
    """ ensure that a fw path (group, or group/project) is valid for creation.
    i.e., ensure that it doesn't exist already

    Args:
        fwpath: a string path to a group, or group/project (just "<groupid>", or "<groupid>/<project>")
        fw: flywheel Client

    Returns: True|False

    """

    try:
        fw.lookup(fwpath)
    except ApiException as e:
        if e.status == 404:
            return False
    return True


def create_flywheel_group(*, group_label: str, group_id: str, fw: flywheel.Client) -> str:
    """Creates FW group with label and ID.

    Args:
      group_label: the name of the project to be created
      group_id: the id for the group
      fw: flywheel sdk Client
    Returns:
      the ID of the FW group
    """
    group_label = sanitize_name(group_label)
    group_id = sanitize_name(group_id, groupid=True)

    if flywheel_path_exists(group_id):
        logging.info(f"Flywheel group {group_id} already exists")
        return group_id

    logging.info("Creating group %s with id %s", group_label, group_id)
    logging.info("  group label: %s", group_label)
    logging.info("  group ID: %s", group_id)

    if not DRYRUN:
        group_id = fw.add_group(flywheel.Group(group_id, group_label))
        logging.info("\tsuccess")

    return group_id



def create_flywheel_project(*, group_id: str, project_id: str,
                            project_label: str) -> None:
    """Creates FW project w/in group with given name.

    Args:
      group_id: the group
      project_id: the name of the project
      project_label: the display name of the project
    """
    project_ref = f"fw://{group_id}/{project_id}"
    logging.info("Creating project %s with id %s", project_label, project_ref)
    logging.info("  project: %s", project_ref)
    logging.info("  project name: %s", project_label)
    return project_ref


class FlywheelProjectArtifactCreator(ProjectVisitor):
    """Creates project artifacts in Flywheel."""

    def __init__(self) -> None:
        """Inititializes visitor with FW instance details."""
        self.__current_project = None

    def __create_accepted(self, center):
        label = self.__current_project.name + " " + center.name + " Accepted"
        group_id = convert_to_slug(label)
        create_flywheel_group(group_label=label, group_id=group_id)
        create_flywheel_project(group_id=group_id,
                                project_id=center.center_id,
                                project_label=center.name)

    def __create_ingest(self, center):
        label = self.__current_project.name + " " + center.name + " Ingest"
        group_id = convert_to_slug(label)
        create_flywheel_group(group_label=label, group_id=group_id)
        for datatype in self.__current_project.datatypes:
            label = center.name + " " + datatype.capitalize() + " Ingest"
            project_id = center.center_id + "-" + datatype
            create_flywheel_project(group_id=group_id,
                                    project_id=project_id,
                                    project_label=label)

    def __create_release(self):
        label = self.__current_project.name + " Release"
        group_id = convert_to_slug(label)
        create_flywheel_group(group_label=label, group_id=group_id)

    def visit_center(self, center: Center):
        """Creates project in FW instance."""
        if not self.__current_project:
            logging.error("No project given")
            return

        if center.is_active():
            if self.__current_project.datatypes:
                self.__create_ingest(center)
            else:
                logging.warning(
                    "Not creating ingest group for project %s: no datatypes given",
                    self.__current_project.name)
        else:
            logging.info("Not creating ingest for inactive center %s",
                         center.name)

        self.__create_accepted(center)

    def visit_project(self, project: Project):
        """Creates groups in FW instance:

        - one ingest groups for each datatype for each center
        - one "accepted" groups for each center
        - "release" group for project if project.published
        """
        self.__current_project = project

        if self.__current_project.centers:
            for center in self.__current_project.centers:
                center.apply(self)
        else:
            logging.warning(
                "Not creating accepted group for project %s: no centers given",
                self.__current_project.name)

        if self.__current_project.is_published():
            self.__create_release()
        else:
            logging.info("Project %s has no release project",
                         self.__current_project.name)

        self.__current_project = None

    def visit_datatype(self, datatype: str):
        pass


def main():
    """Main method to create project from the adrc_program.yaml file."""

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Create FW structures for Project")
    parser.add_argument('filename')
    args = parser.parse_args()
    project_file = args.filename
    with open(project_file, 'r', encoding='utf-8') as stream:
        try:
            project_gen = yaml.safe_load_all(stream)
        except yaml.YAMLError as exception:
            logging.error("Error in YAML file: %s", project_file)
            if hasattr(exception, 'problem_mark'):
                mark = exception.problem_mark
                logging.error("Error: line %s, column %s", mark.line + 1,
                              mark.column + 1)
            sys.exit(1)
        else:
            project_list = list(project_gen)

    visitor = FlywheelProjectArtifactCreator()
    for project_doc in project_list:
        project = Project.create(project_doc)
        project.apply(visitor)


if __name__ == "__main__":
    main()
