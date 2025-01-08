"""Entry script for prescreening."""
import logging
from typing import List, Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
    InputFileWrapper,
)
from inputs.parameter_store import ParameterStore

from prescreening_app.main import run

log = logging.getLogger(__name__)


class PreScreeningVisitor(GearExecutionEnvironment):
    """Visitor for the Pre-Screening gear."""

    def __init__(self,
                 client: ClientWrapper,
                 file_input: InputFileWrapper,
                 accepted_modules: List[str],
                 tags_to_add: List[str],
                 local_run: bool = False):
        super().__init__(client=client)

        self.__file_input = file_input
        self.__accepted_modules = accepted_modules
        self.__tags_to_add = tags_to_add
        self.__local_run = local_run

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'PreScreeningVisitor':
        """Creates a gear execution object.

        Args:
            context: The gear context.
            parameter_store: The parameter store
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)

        file_input = InputFileWrapper.create(input_name='input_file',
                                             context=context)
        local_run = context.config.get('local_run', False)
        accepted_modules = context.config.get('accepted_modules', None)
        tags_to_add = context.config.get('tags_to_add', None)

        if not accepted_modules:
            raise GearExecutionError("No accepted modules provided")
        if not tags_to_add:
            raise GearExecutionError("No tags to add provided")

        return PreScreeningVisitor(
            client=client,
            file_input=file_input,  # type: ignore
            accepted_modules=[
                x.strip().lower() for x in accepted_modules.split(',')
            ],
            tags_to_add=[x.strip().lower() for x in tags_to_add.split(',')],
            local_run=local_run)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the PreScreening app."""
        run(proxy=self.proxy,
            file_input=self.__file_input,
            accepted_modules=self.__accepted_modules,
            tags_to_add=self.__tags_to_add,
            local_run=self.__local_run)


def main():
    """Main method for PreScreeningVisitor.

    Prescreens the input file.
    """

    GearEngine.create_with_parameter_store().run(gear_type=PreScreeningVisitor)


if __name__ == "__main__":
    main()
