"""Entry script for REDCap Project Info Management."""

import logging
import sys
from typing import List

from centers.center_group import REDCapProjectInput
from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (GearContextVisitor,
                                           GearExecutionEngine,
                                           GearExecutionError)
from inputs.parameter_store import ParameterStore
from inputs.yaml import YAMLReadError, load_from_stream
from pydantic import ValidationError
from redcap_info_app.main import run

log = logging.getLogger(__name__)


class REDCapProjectInfoVisitor(GearContextVisitor):
    """Visitor for the REDCap Project Info Management gear."""

    def __init__(self):
        super().__init__()
        self.admin_group_id = None
        self.input_file_path = None

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visit context to accumulate inputs for the gear.

        Args:
            context: The gear context.
        """
        super().visit_context(context)
        if not self.client:
            raise GearExecutionError("Flywheel client required")
        self.admin_group_id = context.config.get("admin_group", "nacc")
        self.input_file_path = context.get_input_path('input_file')
        if not self.input_file_path:
            raise GearExecutionError('No input file provided')

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """dummy instantiation of abstract method."""

    def run(self, engine: 'GearExecutionEngine') -> None:
        """Run the REDCap Project Info Management gear.

        Args:
            engine: The execution environment for the gear.
        """
        assert self.input_file_path, 'Input file required'
        proxy = self.get_proxy()
        admin_group = NACCGroup.create(proxy=proxy,
                                       group_id=self.admin_group_id)
        project_list = self.__get_project_list(self.input_file_path)
        run(project_list=project_list, admin_group=admin_group)

    # pylint: disable=no-self-use
    def __get_project_list(self,
                           input_file_path: str) -> List[REDCapProjectInput]:
        """Get the REDCap project info objects from the input file.

        Args:
            input_file_path: The path to the input file.
        Returns:
            A list of REDCap project info objects.
        """
        try:
            with open(input_file_path, 'r', encoding='utf-8 ') as input_file:
                object_list = load_from_stream(input_file)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'No REDCap project info read from input: {error}') from error
        if not object_list:
            raise GearExecutionError(
                'No REDCap project info read from input file')

        project_list = []
        for project_object in object_list:
            try:
                project_list.append(
                    REDCapProjectInput.model_validate(project_object))
            except ValidationError as error:
                log.error('Invalid REDCap project info: %s', error)
                continue
        if not project_list:
            raise GearExecutionError(
                'No valid REDCap project info read from input file')

        return project_list


def main():
    """Main method for REDCap Project Info Management."""

    engine = GearExecutionEngine()
    try:
        engine.execute(REDCapProjectInfoVisitor())
    except GearExecutionError as error:
        log.error('Gear execution error: %s', error)
        sys.exit(1)


if __name__ == "__main__":
    main()
