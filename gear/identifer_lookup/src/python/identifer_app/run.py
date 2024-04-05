"""Entrypoint script for the identifer lookup app."""

import logging
from pathlib import Path
from typing import Dict, Optional

from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, GearBotClient,
                                           GearEngine,
                                           GearExecutionEnvironment,
                                           GearExecutionError,
                                           InputFileWrapper)
from identifer_app.main import run
from identifiers.database import create_session
from identifiers.identifiers_repository import IdentifierRepository
from identifiers.model import Identifier
from inputs.parameter_store import (ParameterError, ParameterStore,
                                    RDSParameters)
from outputs.errors import ListErrorWriter

log = logging.getLogger(__name__)


def get_identifiers(rds_parameters: RDSParameters,
                    adcid: int) -> Dict[str, Identifier]:
    """Gets all of the Identifier objects from the identifier database using
    the RDSParameters.

    Args:
      rds_parameters: the credentials for RDS MySQL with identifiers database
      adcid: the center ID
    Returns:
      the dictionary mapping from PTID to Identifier object
    """
    identifiers = {}
    identifers_session = create_session(rds_parameters)
    with identifers_session as session:
        identifiers_repo = IdentifierRepository(session)
        center_identifiers = identifiers_repo.list(adc_id=adcid)
        if center_identifiers:
            # pylint: disable=(not-an-iterable)
            identifiers = {
                identifier.ptid: identifier
                for identifier in center_identifiers
            }

    return identifiers


class IdentifierLookupVisitor(GearExecutionEnvironment):
    """The gear execution visitor for the identifier lookup app."""

    def __init__(self, client: ClientWrapper, admin_id: str,
                 file_input: InputFileWrapper, rds_parameters: RDSParameters):
        self.__admin_id = admin_id
        self.__client = client
        self.__file_input = file_input
        self.rds_parameters = rds_parameters

    @classmethod
    def create(
        cls, context: GearToolkitContext,
        parameter_store: Optional[ParameterStore]
    ) -> 'IdentifierLookupVisitor':
        """Creates an identifier lookup execution visitor.

        Args:
          context: the gear context
          parameter_store: the parameter store
        Raises:
          GearExecutionError if rds parameter path is not set
        """
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

        return IdentifierLookupVisitor(client=client,
                                       admin_id=admin_id,
                                       file_input=file_input,
                                       rds_parameters=rds_parameters)

    def run(self, context: GearToolkitContext):
        """Runs the identifier lookup app.

        Args:
            context: the gear execution context
        """

        assert context, 'Gear context required'

        proxy = self.__client.get_proxy()
        admin_group = NACCGroup.create(proxy=proxy, group_id=self.__admin_id)

        file_id = self.__file_input.file_id
        group_id = proxy.get_file_group(file_id)
        adcid = admin_group.get_adcid(group_id)
        if not adcid:
            raise GearExecutionError('Unable to determine center ID for file')

        identifiers = get_identifiers(rds_parameters=self.rds_parameters,
                                      adcid=adcid)
        if not identifiers:
            raise GearExecutionError('Unable to load center participant IDs')

        filename = f"{self.__file_input.filename}-identifier"
        input_path = Path(self.__file_input.filepath)
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            with context.open_output(f'{filename}.csv',
                                     mode='w',
                                     encoding='utf-8') as out_file:
                error_writer = ListErrorWriter(container_id=file_id,
                                               fw_path=proxy.get_lookup_path(
                                                   proxy.get_file(file_id)))
                errors = run(input_file=csv_file,
                             identifiers=identifiers,
                             output_file=out_file,
                             error_writer=error_writer)
                context.metadata.add_qc_result(
                    self.__file_input.file_input,
                    name="validation",
                    state="FAIL" if errors else "PASS",
                    data=error_writer.errors())


def main():
    """The Identifiers Lookup gear reads a CSV file with rows for participants
    at a single ADRC, and having a PTID for the participant. The gear looks up
    the corresponding NACCID, and creates a new CSV file with the same
    contents, but with a new column for NACCID.

    Writes errors to a CSV file compatible with Flywheel error UI.
    """

    GearEngine.create_with_parameter_store().run(
        gear_type=IdentifierLookupVisitor)


if __name__ == "__main__":
    main()
