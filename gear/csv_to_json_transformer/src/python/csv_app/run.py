"""Entrypoint script for the csv-to-json transformer app."""

import logging
import sys
from typing import Optional

from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    ContextClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
    InputFileWrapper,
)
from inputs.context_parser import get_config
from inputs.parameter_store import ParameterStore
from outputs.errors import ListErrorWriter

from csv_app.main import run

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


class CsvToJsonVisitor(GearExecutionEnvironment):

    def __init__(self, client: ClientWrapper,
                 file_input: InputFileWrapper) -> None:
        self.__client = client
        self.__file_input = file_input

    @classmethod
    def create(
            cls, context: GearToolkitContext,
            parameter_store: Optional[ParameterStore]) -> 'CsvToJsonVisitor':
        client = ContextClient.create(context=context)
        file_input = InputFileWrapper.create(input_name='input_file',
                                             context=context)

        return CsvToJsonVisitor(client=client, file_input=file_input)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the CSV to JSON Transformer app.

        Args:
          context: the gear execution context
        """

        proxy = self.__client.get_proxy()
        file_id = self.__file_input.file_id
        try:
            file = proxy.get_file(file_id)
        except ApiException as error:
            raise GearExecutionError(
                f'Failed to find the input file: {error}') from error

        project = proxy.get_project_by_id(file.parents.project)
        if not project:
            raise GearExecutionError(
                f'Failed to find the project with ID {file.parents.project}')

        required_fields = get_config(gear_context=context,
                                     key='required_fields',
                                     default=None)

        with open(self.__file_input.filepath, mode='r',
                  encoding='utf-8') as csv_file:
            error_writer = ListErrorWriter(container_id=file_id,
                                           fw_path=proxy.get_lookup_path(file))
            success, sys_errors = run(input_file=csv_file,
                                      proxy=proxy,
                                      project=project,
                                      error_writer=error_writer,
                                      required_fields=required_fields)

            context.metadata.add_qc_result(self.__file_input.file_input,
                                           name='validation',
                                           state='PASS' if success else 'FAIL',
                                           data=error_writer.errors())

            context.metadata.add_file_tags(self.__file_input.file_input,
                                           tags=context.manifest.get(
                                               'name',
                                               'csv-to-json-transformer'))
            if sys_errors:
                raise GearExecutionError(
                    'System errors occurred while processing the input file')


def main():
    """Gear main method to transform CSV where row is participant data to set
    of JSON files, one per participant."""

    GearEngine().run(gear_type=CsvToJsonVisitor)


if __name__ == "__main__":
    main()
