"""Reads a YAML file with project info.

project - name of project
centers - array of centers
    center-id - the group ID of center
    adcid - the ADC ID used to code data
    name - name of center
    is-active - whether center is active, has users if True
datatypes - array of datatype names (form, dicom)
published - boolean indicating whether data is to be published
"""
import logging
import sys

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (GearContextVisitor,
                                           GearExecutionEngine,
                                           GearExecutionError)
from inputs.yaml import YAMLReadError, get_object_lists
from project_app.main import run

log = logging.getLogger(__name__)


class ProjectCreationVisitor(GearContextVisitor):
    """Defines the project management gear."""

    def __init__(self):
        super().__init__()
        self.admin_group_id = None
        self.new_only = False
        self.project_list = []

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visits the gear context to gather inputs.

        Args:
            context (GearToolkitContext): The gear context.

        Raises:
            GearExecutionError: If the Flywheel client is not available or
            if there is an error reading the YAML file.
        """
        super().visit_context(context)
        if not self.client:
            raise GearExecutionError("Flywheel client required")

        project_file = context.get_input_path('project_file')
        try:
            self.project_list = get_object_lists(project_file)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'Unable to read YAML file {project_file}: {error}') from error

        self.new_only = context.config.get("new_only", False)

    def run(self, engine: GearExecutionEngine) -> None:
        """Executes the gear.

        Args:
            engine (GearExecutionEngine): The gear execution engine.

        Raises:
            AssertionError: If admin group ID or project list is not provided.
        """
        assert self.project_list, 'Project list required'

        admin_group = self.get_admin_group()
        admin_access = admin_group.get_user_access()

        proxy = self.get_proxy()
        run(proxy=proxy,
            project_list=self.project_list,
            admin_access=admin_access,
            role_names=['curate', 'upload'],
            new_only=self.new_only)


def main():
    """Main method to create project from the adrc_program.yaml file.

    Uses command line argument `gear` to indicate whether being run as a gear.
    If running as a gear, the arguments are taken from the gear context.
    Otherwise, arguments are taken from the command line.

    Arguments are
      * admin_group: the name of the admin group in the instance
        default is `nacc`
      * dry_run: whether to run as a dry run, default is False
      * the project file

    Gear rules are taken from template projects in the admin group.
    These projects are expected to be named `<datatype>-<stage>-template`,
    where `datatype` is one of the datatypes that occur in the project file,
    and `stage` is one of 'accepted', 'ingest' or 'retrospective'.
    (These are pipeline stages that can be created for the project)
    """
    engine = GearExecutionEngine()
    try:
        engine.execute(ProjectCreationVisitor())
    except GearExecutionError as error:
        log.error('Error: %s', error)
        sys.exit(1)


if __name__ == "__main__":
    main()
