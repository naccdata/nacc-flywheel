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
from identifiers.identifiers_lambda_repository import (
    IdentifiersLambdaRepository, IdentifiersMode)
from inputs.parameter_store import ParameterStore
from lambdas.lambda_function import LambdaClient, create_lambda_client
from outputs.errors import ListErrorWriter

log = logging.getLogger(__name__)


class IdentifierProvisioningVisitor(GearExecutionEnvironment):
    """Execution visitor for NACCID provisioning gear."""

    # pylint: disable=(too-many-arguments)
    def __init__(self, client: ClientWrapper, admin_id: str,
                 file_input: InputFileWrapper, form_name: str,
                 identifiers_mode: IdentifiersMode) -> None:
        self.__client = client
        self.__admin_id = admin_id
        self.__file_input = file_input
        self.__form_name = form_name
        self.__identifiers_mode: IdentifiersMode = identifiers_mode

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
        admin_id = context.config.get("admin_group", "nacc")
        mode = context.config.get("identifiers_mode", "dev")
        form_name = context.config.get("form_name", "ptenrlv1")

        return IdentifierProvisioningVisitor(client=client,
                                             admin_id=admin_id,
                                             file_input=file_input,
                                             identifiers_mode=mode,
                                             form_name=form_name)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the identifier provisioning app.

        Args:
          context: the gear execution context
        """

        assert context, 'Gear context required'

        identifiers_repo = IdentifiersLambdaRepository(
            client=LambdaClient(client=create_lambda_client()),
            mode=self.__identifiers_mode)

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
            errors = run(input_file=csv_file,
                         form_name=self.__form_name,
                         error_writer=error_writer,
                         repo=identifiers_repo)
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
