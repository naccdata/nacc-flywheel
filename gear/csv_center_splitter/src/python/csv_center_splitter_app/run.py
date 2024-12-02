"""Entry script for csv_center_splitter."""
import logging
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    ContextClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from inputs.parameter_store import ParameterStore

from csv_center_splitter_app.main import run

log = logging.getLogger(__name__)

class CsvCenterSplitterVisitor(GearExecutionEnvironment):
    """Visitor for the CSV Center Splitter gear."""

    def __init__(self, client: ClientWrapper, input_filepath: str,
                 input_filename: str, adcid_key: str, target_project: str,
                 delimiter: str):
        super().__init__(client=client)

        self.__input_filepath = input_filepath
        self.__input_filename = input_filename
        self.__adcid_key = adcid_key
        self.__target_project = target_project
        self.__delimiter = delimiter

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'CsvCenterSplitterVisitor':
        """Creates a gear execution object.

        Args:
            context: The gear context.
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        client = ContextClient.create(context=context)
        input_filepath = context.get_input_path('input_file')

        if not input_filepath:
            raise GearExecutionError("No input CSV provided")
        input_filename = context.get_input_filename('input_file')

        target_project = context.config.get('target_project', None)

        if not target_project:
            raise GearExecutionError("No target project provided")

        adcid_key = context.config.get('adcid_key', None)
        if not adcid_key:
            raise GearExecutionError("No ADCID key provided")

        return CsvCenterSplitterVisitor(client=client,
                                        input_filepath=input_filepath,
                                        input_filename=input_filename,
                                        adcid_key=adcid_key,
                                        target_project=target_project,
                                        delimiter=context.config.get(
                                            'delimiter', ","))

    def run(self, context: GearToolkitContext) -> None:
        """Runs the CSV Center Splitter app."""
        run(proxy=self.proxy,
            input_filepath=self.__input_filepath,
            input_filename=self.__input_filename,
            adcid_key=self.__adcid_key,
            target_project=self.__target_project,
            delimiter=self.__delimiter)


def main():
    """Main method for CsvCenterSplitter.

    Splits CSV and distributes per center.
    """

    GearEngine().run(gear_type=CsvCenterSplitterVisitor)


if __name__ == "__main__":
    main()
