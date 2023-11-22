"""Main function for running template push process."""
import logging
import sys

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from fw_client import FWClient
from inputs.context_parser import get_api_key
from inputs.templates import get_template_projects
from template_app.main import run

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    """Main method to copy template projects to center projects.

    Arguments are taken from the gear context.
    Arguments are
      * admin_group: the name of the admin group in the instance
        default is `nacc`
      * dry_run: whether to run as a dry run, default is False
      * new_only: whether to only run on groups tagged as new

    Gear pushes contents from the template projects in the admin group.
    These projects are expected to be named `<datatype>-<stage>-template`,
    where `datatype` is one of the datatypes that occur in the project file,
    and `stage` is one of 'accepted', 'ingest' or 'retrospective'.
    (These are pipeline stages that can be created for the project)
    """

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        client = gear_context.client
        if not client:
            log.error('No Flywheel connection. Check API key configuration.')
            sys.exit(1)

        # Need fw-client because the SDK doesn't properly implement ViewerApp type
        # used for copying viewer apps from template projects.
        api_key = get_api_key(gear_context)
        fw_client = FWClient(api_key=api_key, client_name="push-template")

        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=client,
                                       fw_client=fw_client,
                                       dry_run=dry_run)

        admin_group_name = gear_context.config.get('admin_group', 'nacc')
        groups = flywheel_proxy.find_groups(admin_group_name)
        if not groups:
            log.warning("Admin group %s not found", admin_group_name)
            sys.exit(1)

        new_only = gear_context.config.get("new_only", False)
        template_map = get_template_projects(group=groups[0],
                                             proxy=flywheel_proxy)
        run(proxy=flywheel_proxy,
            center_tag_pattern=r'adcid-\d+',
            new_only=new_only,
            template_map=template_map)


if __name__ == "__main__":
    main()
