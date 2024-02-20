"""Script to pull directory information and convert to file expected by the
user management gear."""
import logging
import sys

from directory_app.main import run
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.configuration import ConfigurationError, get_group, get_project
from inputs.context_parser import ConfigParseError, get_config
from inputs.parameter_store import ParameterError, ParameterStore
from redcap.redcap_connection import (REDCapConnectionError,
                                      REDCapReportConnection)

log = logging.getLogger(__name__)


def main() -> None:
    """Main method for directory pull.

    Expects information needed for access to the user access report from
    the NACC directory on REDCap, and api key for flywheel. These must
    be given as environment variables.
    """

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        try:
            parameter_store = ParameterStore.create_from_environment()
            api_key = parameter_store.get_api_key()

            param_path: str = get_config(gear_context=gear_context,
                                         key='parameter_path')
            report_parameters = parameter_store.get_redcap_report_connection(
                param_path=param_path)
            directory_proxy = REDCapReportConnection.create_from(
                report_parameters)
            user_report = directory_proxy.get_report_records()
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)
        except REDCapConnectionError as error:
            log.error('Failed to pull users from directory: %s', error.message)
            sys.exit(1)

        dry_run = gear_context.config.get("dry_run", False)
        flywheel_proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

        try:
            admin_group = get_group(context=gear_context,
                                    proxy=flywheel_proxy,
                                    key='admin_group',
                                    default='nacc')
            destination = get_project(context=gear_context,
                                      group=admin_group,
                                      project_key='destination')
            user_filename: str = get_config(gear_context=gear_context,
                                            key='user_file')
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)
        except ConfigurationError as error:
            log.error('Unable to save directory file: %s', error)
            sys.exit(1)

        run(user_report=user_report,
            user_filename=user_filename,
            project=destination,
            dry_run=dry_run)


if __name__ == "__main__":
    main()
