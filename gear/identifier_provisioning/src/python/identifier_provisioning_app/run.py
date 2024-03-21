"""Entry script for Identifier Provisioning."""

import logging
import sys

from flywheel_gear_toolkit import GearToolkitContext
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from identifier_provisioning_app.main import run
from inputs.yaml import YAMLReadError, get_object_lists

log = logging.getLogger(__name__)

def main():
    """Main method for Identifier Provisioning."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        input_file = gear_context.get_input_path('input_file') 
        try:
            object_list = get_object_lists(input_file)
        except YAMLReadError as error:
            log.error('No objects read from input: %s', error)
            sys.exit(1)

        if not object_list:
            log.error('No objects read from input file')
            sys.exit(1)

        client = gear_context.client
        if not client:
            log.error('No Flywheel connection. Check API key configuration.')
            sys.exit(1)
        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=client, dry_run=dry_run)

        new_only = gear_context.config.get("new_only", False)
        run(proxy=flywheel_proxy,
            object_list=object_list,
            new_only=new_only)

if __name__ == "__main__":
    main()
