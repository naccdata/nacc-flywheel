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
from typing import Any, List, Optional

from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, ContextClient,
                                           GearEngine,
                                           GearExecutionEnvironment,
                                           GearExecutionError)
from inputs.parameter_store import ParameterStore
from inputs.yaml import YAMLReadError, get_object_lists
from project_app.main import run

log = logging.getLogger(__name__)


class ProjectCreationVisitor(GearExecutionEnvironment):
    """Defines the project management gear."""

    def __init__(self,
                 admin_id: str,
                 client: ClientWrapper,
                 project_list: List[List[Any]],
                 new_only: bool = False):
        self.__client = client
        self.__new_only = new_only
        self.__project_list = project_list
        self.__admin_id = admin_id

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'ProjectCreationVisitor':
        """Creates a projection creation execution visitor.

        Args:
          context: the gear context
        Returns:
          the project creation visitor
        Raises:
          GearExecutionError if the project file cannot be loaded
        """
        client = ContextClient.create(context=context)
        project_file = context.get_input_path('project_file')
        try:
            project_list = get_object_lists(project_file)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'Unable to read YAML file {project_file}: {error}') from error
        if not project_list:
            raise GearExecutionError("Failed to read project file")
        admin_id = context.config.get("admin_group", "nacc")

        return ProjectCreationVisitor(admin_id=admin_id,
                                      client=client,
                                      project_list=project_list,
                                      new_only=context.config.get(
                                          "new_only", False))

    def run(self, context: GearToolkitContext) -> None:
        """Executes the gear.

        Args:
            context: the gear execution context

        Raises:
            AssertionError: If admin group ID or project list is not provided.
        """
        proxy = self.__client.get_proxy()
        admin_group = NACCGroup.create(proxy=proxy, group_id=self.__admin_id)

        run(proxy=proxy,
            admin_group=admin_group,
            project_list=self.__project_list,
            role_names=['curate', 'upload'],
            new_only=self.__new_only)


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

    GearEngine().run(gear_type=ProjectCreationVisitor)


if __name__ == "__main__":
    main()
