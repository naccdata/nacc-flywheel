"""Entrypoint script for the csv-to-json transformer app."""

import logging
import sys
from pathlib import Path

from csv_app.main import run
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from outputs.errors import ErrorWriter

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    """Gear main method to transform CSV where row is participant data to set
    of JSON files, one per participant."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        client = gear_context.client
        if not client:
            log.error('No Flywheel connection. Check API key configuration.')
            sys.exit(1)
        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=client, dry_run=dry_run)

        file_input = gear_context.get_input('input_file')
        file_id = file_input['object']['file_id']
        filename = gear_context.get_input_filename('csv_file')
        input_path = Path(gear_context.get_input_path('csv_file'))
        with open(input_path, mode='r', encoding='utf-8') as csv_file:
            with gear_context.open_output(f'{filename}-error.csv') as err_file:
                success = run(proxy=flywheel_proxy,
                    csv_file=csv_file,
                    error_writer=ErrorWriter(stream=err_file,
                                             container_id=file_id))

    if __name__ == "__main__":
        main()
