"""Entry script for Identifier Provisioning."""

import logging
import sys

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (GearBotExecutionVisitor,
                                           GearExecutionEngine,
                                           GearExecutionError)
from inputs.parameter_store import ParameterError, ParameterStore

log = logging.getLogger(__name__)


class IdentifierProvisioningVisitor(GearBotExecutionVisitor):
    """Execution visitor for NACCID provisioning gear."""

    def visit_context(self, context: GearToolkitContext) -> None:
        super().visit_context(context)
        self.rds_param_path = context.config.get('rds_parameter_path')
        if not self.rds_param_path:
            raise GearExecutionError('No value for rds_parameter_path')

        self.file_input = context.get_input('input_file')
        if not self.file_input:
            raise GearExecutionError('Missing input file')

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """Visits the parameter store and loads the RDS parameters.

        Args:
            parameter_store: the parameter store object
        """
        super().visit_parameter_store(parameter_store)
        assert self.rds_param_path, 'RDS parameter path required'
        try:
            self.rds_parameters = parameter_store.get_rds_parameters(
                param_path=self.rds_param_path)
        except ParameterError as error:
            raise GearExecutionError(f'Parameter error: {error}') from error

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
        engine.execute(IdentifierLookupVisitor())
    except GearExecutionError as error:
        log.error('Error: %s', error)
        sys.exit(1)

    if __name__ == "__main__":
        main()


if __name__ == "__main__":
    main()
