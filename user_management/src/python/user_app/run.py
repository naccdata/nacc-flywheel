"""The run script for the user management gear."""

import logging
import sys
from io import StringIO
from typing import Any, List, Optional

from admin.users import get_admin_users
from flywheel import Client, Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.api_key import get_api_key
from inputs.context_parser import parse_config
from inputs.parameter_store import get_parameter_store
from inputs.yaml import get_object_lists_from_stream
from user_app.main import run

log = logging.getLogger(__name__)


def read_file(source: Project, user_filename: str) -> Optional[List[Any]]:
    """Reads user objects from YAML user file in the source project.

    Args:
      source: the project where user file is located
      user_filename: the name of the user file
    Returns:
      List of user objects
    """
    file_bytes = source.read_file(user_filename)
    user_docs = get_object_lists_from_stream(
        StringIO(file_bytes.decode('utf-8')), user_filename)
    if not user_docs or not user_docs[0]:
        return None

    return user_docs[0]


def main() -> None:
    """Main method to manage users."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        context_args = parse_config(gear_context=gear_context)
        admin_group_name = context_args['admin_group']
        source_label = gear_context.config.get('source')
        if not source_label:
            log.error('Incomplete configuration, no source label')
            sys.exit(1)

        dry_run = context_args['dry_run']
        user_filename = gear_context.config.get('user_file')
        if not user_filename:
            log.error('Incomplete configuration, no file name given')
            sys.exit(1)

    parameter_store = get_parameter_store()
    if not parameter_store:
        log.error('Unable to connect to parameter store')
        sys.exit(1)

    api_key = get_api_key(parameter_store)
    if not api_key:
        log.error('No API key found. Check API key configuration')
        sys.exit(1)

    flywheel_proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

    groups = flywheel_proxy.find_groups(admin_group_name)
    if not groups:
        log.warning("Admin group %s not found", admin_group_name)
        sys.exit(1)

    source = flywheel_proxy.get_project(group=groups[0],
                                        project_label=source_label)
    if not source:
        log.error('No project %s in admin group %s, cannot upload file %s',
                  source_label, admin_group_name, user_filename)
        sys.exit(1)

    user_list = read_file(source=source, user_filename=user_filename)
    if not user_list:
        log.error('No users read from file %s in %s/%s', user_filename,
                  admin_group_name, source_label)
        sys.exit(1)

    admin_users = get_admin_users(flywheel_proxy=flywheel_proxy,
                                  group_name=admin_group_name)
    admin_set = {user.id for user in admin_users if user.id}

    run(proxy=flywheel_proxy, user_list=user_list, skip_list=admin_set)


if __name__ == "__main__":
    main()
