"""ADD DETAIL HERE"""

import logging
import sys
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

from flywheel_gear_toolkit import GearToolkitContext
from csv_app.main import run


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

def main():
    """Gear main method to transform CSV where row is participant data to
    set of JSON files, one per participant.
    """

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        client = gear_context.client
        if not client:
            log.error('No Flywheel connection. Check API key configuration.')
            sys.exit(1)
        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=client, dry_run=dry_run)

        csv_file = gear_context.get_input_path('csv_file')


    run(proxy=flywheel_proxy,
        file=csv_file)

    if __name__ == "__main__":
        main()
