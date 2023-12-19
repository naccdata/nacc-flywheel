"""Entrypoint script for the identifer lookup app."""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from centers.center_group import CenterGroup
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
from outputs.errors import ErrorWriter

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
        if not center_identifiers:
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
    group = file.parents.group
    center = CenterGroup(group=group, proxy=proxy)
    return center.center_id()


def main():
    """Describe gear detail here."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        try:
            parameter_store = ParameterStore.create_from_environment()
            dry_run = gear_context.config.get("dry_run", False)
            proxy = FlywheelProxy(client=Client(parameter_store.get_api_key()),
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

        file_id = file_input['object']['file_id']
        adcid = get_adcid(proxy=proxy, file_id=file_id)
        if not adcid:
            log.error('Unable to determine center ID')
            sys.exit(1)

        identifiers = get_identifiers(rds_parameters=rds_parameters,
                                      adcid=adcid)
        if not identifiers:
            log.error('Unable to load center participant IDs')
            sys.exit(1)

        input_path = Path(file_input['location']['path'])
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            with gear_context.open_output('updated_input_file',
                                          mode='w',
                                          encoding='utf-8') as out_file:
                with gear_context.open_output('error_file',
                                              mode='w',
                                              encoding='utf-8') as err_file:
                    errors = run(input_file=csv_file,
                                 identifiers=identifiers,
                                 output_file=out_file,
                                 error_writer=ErrorWriter(
                                     stream=err_file, container_id=file_id))

                    gear_context.metadata.add_qc_result(
                        file_input, "valid_identifiers",
                        "FAIL" if errors else "PASS")

    if __name__ == "__main__":
        main()
