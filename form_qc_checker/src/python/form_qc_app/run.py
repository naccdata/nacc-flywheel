"""ADD DETAIL HERE"""

import logging
import sys
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

from flywheel_gear_toolkit import GearToolkitContext
from inputs.context_parser import parse_config
from inputs.api_key import get_api_key
from inputs.parameter_store import get_parameter_store
from form_qc_app.main import run
from s3.s3_client import get_s3_client


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

def main():
    """Describe gear detail here"""

    filename = 'form_data_file'
    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        context_args = parse_config(gear_context=gear_context,
                                    filename=filename)
        dry_run = context_args['dry_run']
        parameter_path = gear_context.config.get('parameter_path')
        if not parameter_path:
            log.error('Incomplete configuration, no QC rule parameter path')
            sys.exit(1)

        input_file = context_args[filename] # gets the file name
        if not input_file:
            log.error('No input file given')
            sys.exit(1)


    parameter_store = get_parameter_store()
    if not parameter_store:
        log.error('Unable to connect to parameter store')
        sys.exit(1)

    api_key = get_api_key(parameter_store)
    if not api_key:
        log.error('No API key found. Check API key configuration')
        sys.exit(1)

    proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

    s3_client = get_s3_client(store=parameter_store, param_path=parameter_path)
    if not s3_client:
        log.error('Unable to connect to S3')


    run(proxy=proxy,
        s3_client=s3_client)

    if __name__ == "__main__":
        main()
