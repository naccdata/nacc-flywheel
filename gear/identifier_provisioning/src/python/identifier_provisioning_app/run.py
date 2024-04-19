"""Entry script for Identifier Provisioning."""

import logging
from pathlib import Path
from typing import Optional

from centers.nacc_group import NACCGroup
from flywheel_adaptor.flywheel_proxy import FlywheelError
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, GearBotClient,
                                           GearEngine,
                                           GearExecutionEnvironment,
                                           GearExecutionError,
                                           InputFileWrapper)
from identifier_provisioning_app.main import run
from inputs.parameter_store import (ParameterError, ParameterStore,
                                    RDSParameters)
from outputs.errors import ListErrorWriter

log = logging.getLogger(__name__)


class IdentifierProvisioningVisitor(GearExecutionEnvironment):
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

    def run(self, context: GearToolkitContext) -> None:
        """Runs the identifier provisioning app.

        Args:
          context: the gear execution context
        """
        assert context, 'Gear context required'

        proxy = self.__client.get_proxy()
        try:
            admin_group = NACCGroup.create(proxy=proxy,
                                           group_id=self.__admin_id)
        except FlywheelError as error:
            raise GearExecutionError(str(error)) from error

        file_id = self.__file_input.file_id
        group_id = proxy.get_file_group(file_id)
        adcid = admin_group.get_adcid(group_id)
        if not adcid:
            raise GearExecutionError('Unable to determine center ID for file')

        input_path = Path(self.__file_input.filepath)
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            error_writer = ListErrorWriter(container_id=file_id,
                                           fw_path=proxy.get_lookup_path(
                                               proxy.get_file(file_id)))
            errors = run(input_file=csv_file, error_writer=error_writer)
            context.metadata.add_qc_result(self.__file_input.file_input,
                                           name="validation",
                                           state="FAIL" if errors else "PASS",
                                           data=error_writer.errors())


def main():
    """Main method for Identifier Provisioning."""

    GearEngine.create_with_parameter_store().run(
        gear_type=IdentifierProvisioningVisitor)


if __name__ == "__main__":
    main()
