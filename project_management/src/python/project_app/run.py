"""Reads a YAML file with project info.

project - name of project
centers - array of centers
    center-id - "ADC" ID of center (protected info)
    name - name of center
    is-active - whether center is active, has users if True
datatypes - array of datatype names (form, dicom)
published - boolean indicating whether data is to be published
"""
import logging
import sys

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.configuration import ConfigurationError, get_group
from inputs.yaml import YAMLReadError, get_object_lists
from project_app.main import run

log = logging.getLogger(__name__)


def main():
    """Main method to create project from the adrc_program.yaml file.

    Uses command line argument `gear` to indicate whether being run as a gear.
    If running as a gear, the arguments are taken from the gear context.
    Otherwise, arguments are taken from the command line.

    Arguments are
      * admin_group: the name of the admin group in the instance
        default is `nacc`
      * dry_run: whether to run as a dry run, default is False
      * the project file

    Gear rules are taken from template projects in the admin group.
    These projects are expected to be named `<datatype>-<stage>-template`,
    where `datatype` is one of the datatypes that occur in the project file,
    and `stage` is one of 'accepted', 'ingest' or 'retrospective'.
    (These are pipeline stages that can be created for the project)
    """

    filename = 'project_file'
    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        client = gear_context.client
        if not client:
            log.error('No Flywheel connection. Check API key configuration.')
            sys.exit(1)
        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=client, dry_run=dry_run)

        project_file = gear_context.get_input_path(filename)

        try:
            project_list = get_object_lists(project_file)
        except YAMLReadError as error:
            log.error('Unable to read YAML file %s: %s', project_file, error)
            sys.exit(1)

        admin_access = []
        try:
            admin_group = get_group(context=gear_context,
                                    proxy=flywheel_proxy,
                                    key='admin_group',
                                    default='nacc')
            admin_access = admin_group.get_user_access()
        except ConfigurationError as error:
            log.warning("Unable to load admin users: %s", error)

        new_only = gear_context.config.get("new_only", False)
        run(proxy=flywheel_proxy,
            project_list=project_list,
            admin_access=admin_access,
            role_names=['curate', 'upload'],
            new_only=new_only)


if __name__ == "__main__":
    main()
