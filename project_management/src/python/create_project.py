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
import os
import sys
from typing import Optional

import flywheel
import yaml
from fw_create_project import FlywheelProxy
from projects.project import Center, Project, ProjectVisitor


class FlywheelProjectArtifactCreator(ProjectVisitor):
    """Creates project artifacts in Flywheel."""

    def __init__(self, flywheel_proxy: FlywheelProxy) -> None:
        """Initializes visitor with FW instance details."""
        self.__current_project: Optional[Project] = None
        self.__fw = flywheel_proxy

    def __create_accepted(self, group) -> None:
        """Creates an accepted project for current project within given group.

        Args:
          group: the ID for parent group of project
        """
        assert self.__current_project
        project_id = self.__build_project_id("accepted")
        self.__fw.get_project(group=group, project_label=project_id)

    def __build_project_id(self, prefix: str) -> str:
        """Builds a FW project ID string from the given prefix.

        Concatenates the name of the current project, if is not the primary
        project of the coordinating center.

        Args:
          prefix: the prefix for the project ID
        """
        assert self.__current_project
        if self.__current_project.is_primary():
            return prefix
        return prefix + "-" + self.__current_project.project_id

    def __create_ingest(self, group) -> None:
        """Creates an ingest project for current project within the given group
        for each data type in the project.

        Args:
          group_id: the ID for the parent group of the ingest projects.
        """
        assert self.__current_project
        for datatype in self.__current_project.datatypes:
            project_id = self.__build_project_id("ingest-" + datatype.lower())
            self.__fw.get_project(group=group, project_label=project_id)

    def __create_release(self, project: Project):
        """Creates a release FW group for the given project with a master FW
        project.

        Args:
            project: the project
        """
        group = self.__fw.get_group(group_label=project.name + " Release",
                                    group_id="release-" + project.project_id)

        return self.__fw.get_project(group=group,
                                     project_label="master-project")

    def visit_center(self, center: Center) -> None:
        """Creates center specific details for project in FW instance.

        Adds a FW group for the center containing
        - one FW project per project and datatype, if center is active
        - one FW project per project for "accepted" data
        - one FW project per center for metadata

        Args:
          center: the Center
        """
        if not self.__current_project:
            logging.error("No project given")
            return

        group = self.__fw.get_group(group_label=center.name,
                                    group_id=center.center_id)

        if center.is_active():
            if self.__current_project.datatypes:
                self.__create_ingest(group)
            else:
                logging.warning(
                    "No ingest groups created for %s: no datatypes given",
                    self.__current_project.name)
        else:
            logging.info("Not creating ingest for inactive center %s",
                         center.name)

        self.__create_accepted(group)
        self.__fw.get_project(group=group, project_label="metadata")

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
                "Not creating center groups for project %s: no centers given",
                self.__current_project.name)

        if self.__current_project.is_published():
            self.__create_release(self.__current_project)
        else:
            logging.info("Project %s has no release project",
                         self.__current_project.name)

        self.__current_project = None

    def visit_datatype(self, datatype: str):
        pass


def main():
    """Main method to create project from the adrc_program.yaml file."""

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = build_parser()
    args = parser.parse_args()

    if args.gear:
        context = flywheel.GearContext()
        config = context.config
        dry_run = config['dry_run']
        project_file = context.get_input_path('project_file')
    else:
        dry_run = args.dry_run
        project_file = args.filename

    project_list = get_project_list(project_file)

    api_key = get_api_key()
    if not api_key:
        logging.error('No API key: expecting FW_API_KEY to be set')
        sys.exit(1)

    flywheel_proxy = FlywheelProxy(api_key=api_key, dry_run=dry_run)
    visitor = FlywheelProjectArtifactCreator(flywheel_proxy)
    for project_doc in project_list:
        project = Project.create(project_doc)
        project.apply(visitor)


def build_parser():
    """Builds and returns the argument parser."""
    parser = argparse.ArgumentParser(
        description="Create FW structures for Project")
    parser.add_argument('-g',
                        '--gear',
                        help='whether to read arguments from gear input',
                        default=False,
                        action='store_true')
    parser.add_argument('-d',
                        '--dry_run',
                        help='do a dry run to check input file',
                        default=False,
                        action='store_true')
    parser.add_argument('filename')
    return parser


def get_api_key() -> Optional[str]:
    """Get the Flywheel API key from environment.

    Returns None if the key is not defined.
    """
    api_key = None
    if 'FW_API_KEY' in os.environ:
        api_key = os.environ['FW_API_KEY']
    return api_key


def get_project_list(project_file):
    """Gets list of projects from the project file."""
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
    return project_list


if __name__ == "__main__":
    main()
