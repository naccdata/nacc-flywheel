"""Script to pull directory information and convert to file expected by the
user management gear."""
import logging
import sys
from typing import Optional

import flywheel
from directory_app.main import run
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.api_key import get_api_key
from inputs.context_parser import parse_config
from inputs.parameter_store import get_parameter_store
from redcap.redcap_connection import (REDCapConnectionError,
                                      get_report_connection)

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def main() -> None:
    """Main method for directory pull.

    Expects information needed for access to the user access report from
    the NACC directory on REDCap, and api key for flywheel. These must
    be given as environment variables.
    """

    filename = 'user_file'
    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        context_args = parse_config(gear_context=gear_context,
                                    filename=filename)
        admin_group_name = context_args['admin_group']
        project_name = gear_context.config.get('admin_project',
                                               'project-admin')
        param_path = gear_context.config.get(
            'param_path', '/prod/flywheel/gearbot/naccdirectory')
        dry_run = context_args['dry_run']
        user_filename = context_args[filename]

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

    flywheel_proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

    admin_project = get_admin_project(proxy=flywheel_proxy,
                                      group_name=admin_group_name,
                                      project_name=project_name)
    if not admin_project:
        log.error('No admin group %s, cannot upload file %s', admin_group_name,
                  user_filename)
        sys.exit(1)

    run(user_report=user_report,
        user_filename=user_filename,
        project=admin_project,
        dry_run=dry_run)


def get_admin_project(*, proxy: FlywheelProxy, group_name: str,
                      project_name: str) -> Optional[flywheel.Project]:
    """Gets the admin project from the admin group.

    Args:
      admin_group_name: the name of the admin group
      dry_run: whether to do a dry run on FW operations
      api_key: the FW API key
    """

    admin_group = None
    groups = proxy.find_groups(group_name)
    if not groups:
        log.error("Admin group %s not found", group_name)
        return None

    admin_group = groups[0]

    admin_project = proxy.get_project(group=admin_group,
                                      project_label=project_name)
    if not admin_project:
        log.error('Unable to access admin project: %s', project_name)
        return None

    return admin_project


if __name__ == "__main__":
    main()
