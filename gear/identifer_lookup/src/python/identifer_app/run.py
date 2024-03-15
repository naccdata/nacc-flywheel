"""Entrypoint script for the identifer lookup app."""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from centers.center_group import CenterError, CenterGroup
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from identifer_app.main import run
from identifiers.database import create_session
from identifiers.identifiers_repository import IdentifierRepository
from identifiers.model import Identifier
from inputs.context_parser import ConfigParseError, get_config
from inputs.parameter_store import (ParameterError, ParameterStore,
                                    RDSParameters)
from outputs.errors import ListErrorWriter

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
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


def get_adcid(proxy: FlywheelProxy, file_id: str) -> Optional[int]:
    """Get the adcid of the center group that owns the file.

    Args:
      proxy: the flwheel proxy object
      file_id: the ID for the file
    Returns:
      the ADCID for the center
    """
    file = proxy.get_file(file_id)
    group_id = file.parents.group
    groups = proxy.find_groups(group_id)
    center = CenterGroup.create_from_group(group=groups[0], proxy=proxy)
    return center.adcid


# pylint: disable=(too-many-locals)
def main():
    """The Identifiers Lookup gear reads a CSV file with rows for participants
    at a single ADRC, and having a PTID for the participant. The gear looks up
    the corresponding NACCID, and creates a new CSV file with the same
    contents, but with a new column for NACCID.

    Writes errors to a CSV file compatible with Flywheel error UI.
    """

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        apikey_path_prefix = gear_context.config.get("apikey_path_prefix",
                                                     "/prod/flywheel/gearbot")
        log.info('Running gearbot with API key from %s/apikey', apikey_path_prefix)
        try:
            parameter_store = ParameterStore.create_from_environment()
            dry_run = gear_context.config.get("dry_run", False)
            proxy = FlywheelProxy(client=Client(
                parameter_store.get_api_key(path_prefix=apikey_path_prefix)),
                                  dry_run=dry_run)
            rds_parameters = parameter_store.get_rds_parameters(
                param_path=get_config(gear_context=gear_context,
                                      key='rds_parameter_path'))
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)

        file_input = gear_context.get_input('input_file')
        if not file_input:
            log.error('Missing input file')
            sys.exit(1)

        try:
            file_id = file_input['object']['file_id']
            adcid = get_adcid(proxy=proxy, file_id=file_id)
        except CenterError as error:
            log.error(
                'Unable to determine center ID for parent group of file: %s',
                error.message)
            sys.exit(1)
        assert adcid, "expect adcid unless exception thrown"

        identifiers = get_identifiers(rds_parameters=rds_parameters,
                                      adcid=adcid)
        if not identifiers:
            log.error('Unable to load center participant IDs')
            sys.exit(1)

        filename = f"{file_input['location']['name']}-identifier"
        input_path = Path(file_input['location']['path'])
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            with gear_context.open_output(f'{filename}.csv',
                                          mode='w',
                                          encoding='utf-8') as out_file:
                error_writer = ListErrorWriter(container_id=file_id)
                errors = run(input_file=csv_file,
                             identifiers=identifiers,
                             output_file=out_file,
                             error_writer=error_writer)
                gear_context.metadata.add_qc_result(
                    file_input,
                    name="validation",
                    state="FAIL" if errors else "PASS",
                    data={'data': error_writer.errors()})

    if __name__ == "__main__":
        main()
