"""Entry script for Identifier Provisioning."""

import logging
import sys
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, GearBotClient,
                                           GearExecutionEngine,
                                           GearExecutionError,
                                           GearExecutionVisitor,
                                           InputFileWrapper)
from inputs.parameter_store import (ParameterError, ParameterStore,
                                    RDSParameters)

log = logging.getLogger(__name__)


class IdentifierProvisioningVisitor(GearExecutionVisitor):
    """Execution visitor for NACCID provisioning gear."""

    def __init__(self, client: ClientWrapper, admin_id: str,
                 file_input: InputFileWrapper,
                 rds_parameters: RDSParameters) -> None:
        self.__client = client
        self.__admin_id = admin_id
        self.__file_input = file_input
        self.__rds_parameters = rds_parameters

    @classmethod
    def create(
        cls, context: GearToolkitContext,
        parameter_store: Optional[ParameterStore]
    ) -> 'IdentifierProvisioningVisitor':
        assert parameter_store, "Parameter store expected"

        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)
        file_input = InputFileWrapper.create(input_name='input_file',
                                             context=context)

        rds_param_path = context.config.get('rds_parameter_path')
        if not rds_param_path:
            raise GearExecutionError('No value for rds_parameter_path')

        try:
            rds_parameters = parameter_store.get_rds_parameters(
                param_path=rds_param_path)
        except ParameterError as error:
            raise GearExecutionError(f'Parameter error: {error}') from error
        admin_id = context.config.get("admin_group", "nacc")

        return IdentifierProvisioningVisitor(client=client,
                                             admin_id=admin_id,
                                             file_input=file_input,
                                             rds_parameters=rds_parameters)

    def run(self, gear: 'GearExecutionEngine') -> None:
        pass


def main():
    """Main method for Identifier Provisioning."""

    try:
        parameter_store = ParameterStore.create_from_environment()
    except ParameterError as error:
        log.error('Unable to create Parameter Store: %s', error)
        sys.exit(1)

    engine = GearExecutionEngine(parameter_store=parameter_store)

    try:
        engine.run(visitor_type=IdentifierProvisioningVisitor)
    except GearExecutionError as error:
        log.error('Error: %s', error)
        sys.exit(1)

    if __name__ == "__main__":
        main()


if __name__ == "__main__":
    main()
