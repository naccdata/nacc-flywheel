"""Entrypoint script for the csv-to-json transformer app."""

import logging
import sys
from pathlib import Path
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    ContextClient,
    GearEngine,
    GearExecutionEnvironment,
    InputFileWrapper,
)
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
        file = proxy.get_file(file_id)
        input_path = Path(self.__file_input.filepath)
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            error_writer = ListErrorWriter(container_id=file_id,
                                           fw_path=proxy.get_lookup_path(file))
            success = run(input_file=csv_file,
                          proxy=proxy,
                          error_writer=error_writer)

            context.metadata.add_qc_result(self.__file_input.file_input,
                                           name='validation',
                                           state='PASS' if success else 'FAIL',
                                           data=error_writer.errors())

            context.metadata.add_file_tags(self.__file_input.file_input,
                                           tags=context.manifest.get(
                                               'name',
                                               'csv-to-json-transformer'))


def main():
    """Gear main method to transform CSV where row is participant data to set
    of JSON files, one per participant."""

    GearEngine().run(gear_type=CsvToJsonVisitor)

    if __name__ == "__main__":
        main()
