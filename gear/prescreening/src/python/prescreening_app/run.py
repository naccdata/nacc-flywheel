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
from gear_execution.gear_trigger import GearInfo
from inputs.parameter_store import ParameterStore

from prescreening_app.main import run

log = logging.getLogger(__name__)


class PrescreeningVisitor(GearExecutionEnvironment):
    """Visitor for the Prescreening gear."""

    def __init__(self,
                 client: ClientWrapper,
                 file_input: InputFileWrapper,
                 accepted_modules: List[str],
                 tags_to_add: List[str],
                 scheduler_gear: GearInfo):
        super().__init__(client=client)

        self.__file_input = file_input
        self.__accepted_modules = accepted_modules
        self.__tags_to_add = tags_to_add
        self.__scheduler_gear = scheduler_gear

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'PrescreeningVisitor':
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
        scheduler_gear = InputFileWrapper.create(input_name='input_file',
                                             context=context)

        accepted_modules = context.config.get('accepted_modules', None)
        tags_to_add = context.config.get('tags_to_add', None)
        config_file_path = context.config.get('scheduler_gear_configs_file', None)

        if not accepted_modules:
            raise GearExecutionError("No accepted modules provided")
        if not tags_to_add:
            raise GearExecutionError("No tags to add provided")
        if not config_file_path:
            raise GearExecutionError("No scheduler gear config file specified")

        scheduler_gear = GearInfo.load_from_file(config_file_path)
        if not scheduler_gear:
            raise GearExecutionError(
                f'Error(s) in reading scheduler gear configs file - {config_file_path}'
            )

        return PrescreeningVisitor(
            client=client,
            file_input=file_input,  # type: ignore
            accepted_modules=[
                x.strip().lower() for x in accepted_modules.split(',')
            ],
            tags_to_add=[x.strip().lower() for x in tags_to_add.split(',')],
            scheduler_gear=scheduler_gear)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the Prescreening app."""
        run(proxy=self.proxy,
            file_input=self.__file_input,
            accepted_modules=self.__accepted_modules,
            tags_to_add=self.__tags_to_add,
            scheduler_gear=self.__scheduler_gear)


def main():
    """Main method for PrescreeningVisitor.

    Prescreens the input file.
    """

    GearEngine.create_with_parameter_store().run(gear_type=PrescreeningVisitor)


if __name__ == "__main__":
    main()
