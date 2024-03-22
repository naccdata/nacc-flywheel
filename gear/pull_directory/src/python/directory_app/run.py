"""Script to pull directory information and convert to file expected by the
user management gear."""
import logging
import sys

from directory_app.main import run
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (GearContextVisitor,
                                           GearExecutionEngine,
                                           GearExecutionError)
from inputs.parameter_store import ParameterError, ParameterStore
from redcap.redcap_connection import (REDCapConnectionError,
                                      REDCapReportConnection)
from yaml.representer import RepresenterError

log = logging.getLogger(__name__)


class DirectoryPullVisitor(GearContextVisitor):
    """Defines the directory pull gear."""

    def __init__(self):
        super().__init__()
        self.param_path = None
        self.user_filename = None
        self.report_parameters = None
        self.yaml_text = None

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visit the GearToolkitContext and set the parameter path and user
        filename.

        Args:
            context (GearToolkitContext): The gear context.
        """
        self.param_path = context.config.get('parameter_path')
        self.user_filename = context.config.get('user_file')

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """Visits the parameter store to retrieve report parameters and user
        reports.

        Args:
            parameter_store (ParameterStore): The parameter store object.

        Raises:
            GearExecutionError: If there is an error retrieving report
            parameters or user reports.

        Returns:
            None
        """
        assert self.param_path, 'Parameter path required'
        try:
            report_parameters = parameter_store.get_redcap_report_connection(
                param_path=self.param_path)
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
        try:
            self.yaml_text = run(user_report=user_report)
        except RepresenterError as error:
            raise GearExecutionError(
                "Error: can't create YAML for file"
                f"{self.user_filename}: {error}") from error

    def run(self, engine: GearExecutionEngine) -> None:
        """Runs the directory pull gear.

        Args:
            engine (GearExecutionEngine): The gear execution engine.
        """
        assert engine.context, 'Gear context required'
        assert self.user_filename, 'User filename required'

        if self.dry_run:
            log.info('Would write user entries to file %s on %s %s',
                     self.user_filename, engine.context.destination['type'],
                     engine.context.destination['id'])
            return

        with engine.context.open_output(self.user_filename,
                                        mode='w',
                                        encoding='utf-8') as out_file:
            out_file.write(self.yaml_text)


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
        engine.execute(DirectoryPullVisitor())
    except GearExecutionError as error:
        log.error('Error: %s', error)
        sys.exit(1)


if __name__ == "__main__":
    main()
