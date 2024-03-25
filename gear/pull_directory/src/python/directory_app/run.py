"""Script to pull directory information and convert to file expected by the
user management gear."""
import logging
import sys
from typing import Optional

from directory_app.main import run
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, ContextClient,
                                           GearExecutionEngine,
                                           GearExecutionError,
                                           GearExecutionVisitor)
from inputs.parameter_store import ParameterError, ParameterStore
from redcap.redcap_connection import (REDCapConnectionError,
                                      REDCapReportConnection)
from yaml.representer import RepresenterError

log = logging.getLogger(__name__)


class DirectoryPullVisitor(GearExecutionVisitor):
    """Defines the directory pull gear."""

    def __init__(self, client: ClientWrapper, user_filename: str,
                 yaml_text: str):
        self.__client = client
        self.__user_filename = user_filename
        self.__yaml_text = yaml_text

    @classmethod
    def create(
            cls, context: GearToolkitContext,
            parameter_store: Optional[ParameterStore]
    ) -> 'DirectoryPullVisitor':
        """Creates directory pull execution visitor.

        Args:
          context: the gear context
          parameter_store: the parameter store
        Returns:
          the DirectoryPullVisitor
        Raises:
          GearExecutionError if the config or parameter path are missing values
        """
        assert parameter_store, "Parameter store expected"

        client = ContextClient.create(context)
        param_path = context.config.get('parameter_path')
        if not param_path:
            raise GearExecutionError("No parameter path")

        try:
            report_parameters = parameter_store.get_redcap_report_connection(
                param_path=param_path)
        except ParameterError as error:
            raise GearExecutionError(f'Parameter error: {error}') from error

        try:
            directory_proxy = REDCapReportConnection.create_from(
                report_parameters)
            user_report = directory_proxy.get_report_records()
        except REDCapConnectionError as error:
            raise GearExecutionError(
                f'Failed to pull users from directory: {error.message}'
            ) from error

        user_filename = context.config.get('user_file')
        if not user_filename:
            raise GearExecutionError("No user file name provided")

        try:
            yaml_text = run(user_report=user_report)
        except RepresenterError as error:
            raise GearExecutionError("Error: can't create YAML for file"
                                     f"{user_filename}: {error}") from error

        return DirectoryPullVisitor(client=client,
                                    user_filename=user_filename,
                                    yaml_text=yaml_text)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the directory pull gear.

        Args:
            engine (GearExecutionEngine): The gear execution engine.
        """
        assert context, 'Gear context required'
        assert self.__user_filename, 'User filename required'

        if self.__client.dry_run:
            log.info('Would write user entries to file %s on %s %s',
                     self.__user_filename, context.destination['type'],
                     context.destination['id'])
            return

        with context.open_output(self.__user_filename,
                                 mode='w',
                                 encoding='utf-8') as out_file:
            out_file.write(self.__yaml_text)


def main() -> None:
    """Main method for directory pull.

    Expects information needed for access to the user access report from
    the NACC directory on REDCap, and api key for flywheel. These must
    be given as environment variables.
    """

    try:
        parameter_store = ParameterStore.create_from_environment()
    except ParameterError as error:
        log.error('Unable to create Parameter Store: %s', error)
        sys.exit(1)

    engine = GearExecutionEngine(parameter_store=parameter_store)
    try:
        engine.run(visitor_type=DirectoryPullVisitor)
    except GearExecutionError as error:
        log.error('Error: %s', error)
        sys.exit(1)


if __name__ == "__main__":
    main()
