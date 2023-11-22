"""Script to pull directory information and convert to file expected by the
user management gear."""
import logging
import sys

from directory_app.main import run
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.api_key import get_api_key
from inputs.parameter_store import get_parameter_store
from redcap.redcap_connection import (REDCapConnectionError,
                                      get_report_connection)

log = logging.getLogger(__name__)


def main() -> None:
    """Main method for directory pull.

    Expects information needed for access to the user access report from
    the NACC directory on REDCap, and api key for flywheel. These must
    be given as environment variables.
    """

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        destination_label = gear_context.config.get('destination')
        if not destination_label:
            log.error('Incomplete configuration, no destination label')
            sys.exit(1)

        param_path = gear_context.config.get('parameter_path')
        if not param_path:
            log.error('Incomplete configuration, no directory report path')
            sys.exit(1)

        user_filename = gear_context.config.get('user_file')
        if not user_filename:
            log.error('Incomplete configuration, no output filename given')
            sys.exit(1)

        parameter_store = get_parameter_store()
        if not parameter_store:
            log.error('Unable to connect to parameter store')
            sys.exit(1)

        directory_proxy = get_report_connection(store=parameter_store,
                                                param_path=param_path)
        if not directory_proxy:
            log.error('Unable to connect to REDCap directory project')
            sys.exit(1)

        api_key = get_api_key(parameter_store)
        if not api_key:
            log.error('No API key found. Check API key configuration')
            sys.exit(1)

        try:
            user_report = directory_proxy.get_report_records()
        except REDCapConnectionError as error:
            log.error('Failed to pull users from directory: %s', error.error)
            sys.exit(1)

        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

        admin_group_name = gear_context.config.get('admin_group', 'nacc')
        groups = flywheel_proxy.find_groups(admin_group_name)
        if not groups:
            log.warning("Admin group %s not found", admin_group_name)
            sys.exit(1)

        destination = flywheel_proxy.get_project(group=groups[0],
                                                project_label=destination_label)
        if not destination:
            log.error('No admin group %s, cannot upload file %s', admin_group_name,
                    user_filename)
            sys.exit(1)

        run(user_report=user_report,
            user_filename=user_filename,
            project=destination,
            dry_run=dry_run)


if __name__ == "__main__":
    main()
