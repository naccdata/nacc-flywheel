"""ADD DETAIL HERE"""

import logging
import sys
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

from flywheel_gear_toolkit import GearToolkitContext
from inputs.context_parser import ConfigParseError, get_config, parse_config
from inputs.api_key import get_api_key
from inputs.parameter_store import ParameterError, ParameterStore, get_parameter_store
from form_qc_app.main import run
from s3.s3_client import S3BucketReader, get_s3_client


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

def main():
    """Describe gear detail here"""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        try:
            parameter_store = ParameterStore.create_from_environment()
            api_key = parameter_store.get_api_key()

            s3_param_path = get_config(gear_context=gear_context,
                                       key='parameter_path')
            s3_parameters = parameter_store.get_s3_parameters(
                param_path=s3_param_path)
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)
            
        dry_run = gear_context.config.get("dry_run", False)
        proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

        s3_client = S3BucketReader.create_from(s3_parameters)

        form_file = gear_context.get_input_path('form_data_file')



    run(proxy=proxy,
        s3_client=s3_client,
        form_file=form_file)

    if __name__ == "__main__":
        main()
