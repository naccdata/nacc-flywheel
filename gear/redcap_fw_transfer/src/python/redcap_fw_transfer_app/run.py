"""Entry script for REDCap to Flywheel Transfer."""

import logging
import sys

from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from flywheel_gear_toolkit import GearToolkitContext
from inputs.context_parser import ConfigParseError, get_config
from inputs.parameter_store import ParameterError, ParameterStore
from redcap.redcap_connection import REDCapReportConnection
from redcap_fw_transfer_app.main import run

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def get_destination_project_id(destination: dict, fw_client: Client) -> str:
    """Find the flywheel project id of the destination project.

    Args:
        destination (dict): gear_context.destination
        fw_client (Client): Flywheel SDK client

    Returns:
        str: project id
    """

    if not destination or 'type' not in destination or 'id' not in destination:
        log.error('Gear destination not set, specify the destination project')
        sys.exit(1)

    dest_type = destination.get('type')
    dest_id = destination.get('id')
    if dest_type == 'project':
        project_id = dest_id
    elif dest_type in ('session', 'acquisition'):
        getter = getattr(fw_client, f'get_{dest_type}')
        dest_container = getter(dest_id)
        project_id = dest_container.parents.get('project')
    else:
        log.error('Invalid gear destination %s', destination)
        sys.exit(1)

    return str(project_id)


# pylint: disable=(too-many-locals)
def main():
    """Main method for REDCap to Flywheel Transfer."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        gear_context.log_config()

        default_client = gear_context.client
        if not default_client:
            log.error('Flywheel client required to confirm gearbot access')
            sys.exit(1)

        path_prefix = gear_context.config.get("apikey_path_prefix",
                                              "/prod/flywheel/gearbot")
        log.info('Running gearbot with API key from %s/apikey', path_prefix)
        try:
            parameter_store = ParameterStore.create_from_environment()

            api_key = parameter_store.get_api_key(path_prefix=path_prefix)

            param_path = str(
                get_config(gear_context=gear_context, key='parameter_path'))
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)

        host = gear_context.client.api_client.configuration.host # type: ignore
        if api_key.split(':')[0] not in host:
            log.error('Gearbot API key does not match host')
            sys.exit(1)

        fw_client = Client(api_key)

        project_id = get_destination_project_id(gear_context.destination,
                                                fw_client)

        dry_run = gear_context.config.get("dry_run", False)
        fw_proxy = FlywheelProxy(fw_client, dry_run=dry_run)
        fw_project = fw_client.get_project(project_id)
        prj_adaptor = ProjectAdaptor(project=fw_project, proxy=fw_proxy)
        redcap_prj_id = prj_adaptor.get_custom_project_info(
            'redcap_project_id')
        if not redcap_prj_id:
            log.error('redcap_project_id not defined for project: %s/%s',
                      prj_adaptor.group, prj_adaptor.label)
            sys.exit(1)

        if not param_path.endswith('/'):
            param_path += '/'
        param_path += 'pid_' + redcap_prj_id
        log.info(param_path)

        try:
            report_parameters = parameter_store.get_redcap_report_connection(
                param_path=param_path)

        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)

        redcap_connection = REDCapReportConnection.create_from(
            report_parameters)

        run(gear_context=gear_context,
            fw_prj_adaptor=prj_adaptor,
            redcap_con=redcap_connection,
            redcap_pid=redcap_prj_id)


if __name__ == "__main__":
    main()
