"""ADD DETAIL HERE"""

import logging
import sys
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

from flywheel_gear_toolkit import GearToolkitContext
from inputs.context_parser import ConfigParseError, get_config
from identifer_app.main import run
from inputs.parameter_store import ParameterError, ParameterStore


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

def main():
    """Describe gear detail here"""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        try:
            s3_param_path = get_config(gear_context=gear_context,
                                       key='s3_param_path')
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)

        try:
            parameter_store = ParameterStore.create_from_environment()
            api_key = parameter_store.get_api_key()
            s3_parameters = parameter_store.get_s3_parameters(
                param_path=s3_param_path)
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)

        dry_run = gear_context.config.get("dry_run", False)
        proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

        input_file = gear_context.get_input_path('input_file')

    run(proxy=proxy,
        file=input_file)

    if __name__ == "__main__":
        main()
