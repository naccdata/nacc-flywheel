"""Entry script for REDCap Project Info Management."""

import logging
import sys

from centers.center_group import REDCapProjectInput
from centers.nacc_group import NACCGroup
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.yaml import YAMLReadError, load_from_stream
from pydantic import ValidationError
from redcap_info_app.main import run

log = logging.getLogger(__name__)


def main():
    """Main method for REDCap Project Info Management."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        gear_context.log_config()

        client = gear_context.client
        if not client:
            log.error('No Flywheel connection. Check API key configuration.')
            sys.exit(1)
        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=client, dry_run=dry_run)

        admin_group_id = gear_context.config.get("admin_group", "nacc")
        admin_group = NACCGroup.create(proxy=flywheel_proxy,
                                       group_id=admin_group_id)

        input_file_path = gear_context.get_input_path('input_file')
        if not input_file_path:
            log.error('No input file provided')
            sys.exit(1)

        try:
            with open(input_file_path, 'r', encoding='utf-8 ') as input_file:
                object_list = load_from_stream(input_file)
        except YAMLReadError as error:
            log.error('No REDCap project info read from input: %s', error)
            sys.exit(1)

        if not object_list:
            log.error('No REDCap project info read from input file')
            sys.exit(1)

        project_list = []
        for project_object in object_list:
            try:
                project_list.append(
                    REDCapProjectInput.model_validate(project_object))
            except ValidationError as error:
                log.error('Invalid REDCap project info: %s', error)
                continue

        if not project_list:
            log.error('No valid REDCap project info read from input file')
            sys.exit(1)

        run(project_list=project_list, admin_group=admin_group)


if __name__ == "__main__":
    main()
