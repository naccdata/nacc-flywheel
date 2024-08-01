"""Entry script for Form QC Coordinator."""

import logging

from typing import Any, Optional

from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_adaptor.subject_adaptor import SubjectAdaptor
from gear_execution.gear_execution import (ClientWrapper, GearBotClient,
                                           GearEngine, GearExecutionError,
                                           GearExecutionEnvironment)
from form_qc_coordinator_app.main import run
from inputs.parameter_store import ParameterStore

log = logging.getLogger(__name__)


class FormQCCoordinator(GearExecutionEnvironment):
    """The gear execution visitor for the form-qc-coordinator."""

    def __init__(self,
                 *,
                 client: ClientWrapper,
                 module: str,
                 sort_by: str,
                 check_all: bool = False):
        """
        Args:
            client: Flywheel SDK client wrapper
            module: module to be evaluated (eg. UDSv4, LBDv3, ...)
            sort_by: field name to sort the participant visits
            check_all: re-evaluate all visits for the module/participant
        """
        self._module = module
        self._sort_by = sort_by
        self._check_all = check_all
        super().__init__(client=client)

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'FormQCCoordinator':
        """Creates a gear execution object, loads gear context.

        Args:
            context: The gear context.
            parameter_store: The parameter store
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        assert parameter_store, "Parameter store expected"
        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)
        module = context.config.get('module', 'UDSv4')
        sort_by = context.config.get('sort_by', 'visitdate')
        check_all = context.config.get('check_all', False)

        return FormQCCoordinator(client=client,
                                 module=module,
                                 sort_by=sort_by,
                                 check_all=check_all)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the form-qc-coordinator app.

        Args:
            context: the gear execution context
        """
        try:
            dest_container: Any = context.get_destination_container()
        except ApiException as error:
            raise GearExecutionError(
                f'Cannot find destination container: {error}') from error

        if dest_container.container_type != 'subject':
            raise GearExecutionError(
                'This gear only applies to subject level - '
                'invalid gear destination type '
                f'{dest_container.container_type}')

        run(gear_context=context,
            client_wrapper=self.client,
            proxy=self.proxy,
            subject=SubjectAdaptor(dest_container),
            module=self._module,
            sort_by=self._sort_by,
            check_all=self._check_all)


def main():
    """Main method for Form QC Coordinator."""

    GearEngine.create_with_parameter_store().run(gear_type=FormQCCoordinator)


if __name__ == "__main__":
    main()
