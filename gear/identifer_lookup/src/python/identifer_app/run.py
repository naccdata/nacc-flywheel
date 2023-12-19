"""ADD DETAIL HERE."""

import logging
import sys
from pathlib import Path

from centers.center_group import CenterGroup
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from identifer_app.main import run
from identifiers.identifiers_repository import IdentifierRepository
from inputs.context_parser import ConfigParseError, get_config
from inputs.parameter_store import ParameterError, ParameterStore
from outputs.errors import ErrorWriter

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    """Describe gear detail here."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        try:
            rds_param_path = get_config(gear_context=gear_context,
                                        key='rds_parameter_path')
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)

        try:
            parameter_store = ParameterStore.create_from_environment()
            api_key = parameter_store.get_api_key()
            rds_parameters = parameter_store.get_rds_parameters(
                param_path=rds_param_path)
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)

        dry_run = gear_context.config.get("dry_run", False)
        proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

        file_input = gear_context.get_input('input_file')
        if not file_input:
            log.error('Missing input file')
            sys.exit(1)

        # get the ADCID
        parent = gear_context.get_container_from_ref(file_input['hierarchy'])
        # TODO: should this confirm that parent is a project?
        group = proxy.find_group(parent.group)
        assert group
        center = CenterGroup(group=group.fw_group, proxy=proxy)
        adcid = center.center_id()
        if not adcid:
            log.error('Unable to determine center ID')
            sys.exit(1)

        identifiers_repo = IdentifierRepository.create_from(rds_parameters)
        center_identifiers = identifiers_repo.list(adc_id=adcid)
        identifiers = {
            identifier.ptid: identifier
            for identifier in center_identifiers
        }

        input_path = Path(file_input['location']['path'])
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            with gear_context.open_output('updated_input_file',
                                          mode='w',
                                          encoding='utf-8') as out_file:
                with gear_context.open_output('error_file',
                                              mode='w',
                                              encoding='utf-8') as err_file:
                    # TODO: check flywheel_path and container_id are correct
                    errors = run(input_file=csv_file,
                                 identifiers=identifiers,
                                 output_file=out_file,
                                 error_writer=ErrorWriter(
                                     stream=err_file,
                                     flywheel_path='dummy-flywheel-path',
                                     container_id=file_input['file_id']))

                    gear_context.metadata.add_qc_result(
                        file_input, "valid_identifiers",
                        "FAIL" if errors else "PASS")

    if __name__ == "__main__":
        main()
