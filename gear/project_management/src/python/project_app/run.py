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
from typing import List, Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from inputs.parameter_store import ParameterStore
from inputs.yaml import YAMLReadError, get_object_lists
from projects.study import Study

from project_app.main import run

log = logging.getLogger(__name__)


class ProjectCreationVisitor(GearExecutionEnvironment):
    """Defines the project management gear."""

    def __init__(self, admin_id: str, client: ClientWrapper,
                 project_filepath: str):
        super().__init__(client=client)
        self.__admin_id = admin_id
        self.__project_filepath = project_filepath

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
        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)
        project_filepath = context.get_input_path('project_file')
        if not project_filepath:
            raise GearExecutionError("No project file provided")

        admin_id = context.config.get("admin_group", "nacc")

        return ProjectCreationVisitor(admin_id=admin_id,
                                      client=client,
                                      project_filepath=project_filepath)

    def __get_study_list(self, project_filepath: str) -> List[Study]:
        try:
            project_iterator = get_object_lists(project_filepath)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'Unable to read YAML file {project_filepath}: {error}'
            ) from error
        if not project_iterator:
            raise GearExecutionError("Failed to read project file")

        return [Study.create(study_doc) for study_doc in project_iterator]

    def run(self, context: GearToolkitContext) -> None:
        """Executes the gear.

        Args:
            context: the gear execution context

        Raises:
            AssertionError: If admin group ID or project list is not provided.
        """
        run(proxy=self.proxy,
            admin_group=self.admin_group(admin_id=self.__admin_id),
            project_list=self.__get_study_list(self.__project_filepath))


def main():
    """Main method to run the project creation gear."""

    GearEngine.create_with_parameter_store().run(
        gear_type=ProjectCreationVisitor)


if __name__ == "__main__":
    main()
