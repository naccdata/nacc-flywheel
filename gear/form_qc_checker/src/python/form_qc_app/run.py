"""The entry point for the form-qc-check gear."""

import logging
import sys
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
    InputFileWrapper,
)
from inputs.context_parser import get_config
from inputs.parameter_store import ParameterError, ParameterStore
from redcap.redcap_connection import (
    REDCapConnectionError,
    REDCapReportConnection,
)
from s3.s3_client import S3BucketReader

from form_qc_app.main import run

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


class FormQCCheckerVisitor(GearExecutionEnvironment):
    """The gear execution visitor for the form-qc-checker app."""

    def __init__(self, client: ClientWrapper, file_input: InputFileWrapper,
                 redcap_con: REDCapReportConnection,
                 s3_client: S3BucketReader):
        """
        Args:
            client: Flywheel SDK client wrapper
            file_input: Gear input file wrapper
            redcap_con: REDCap project for NACC QC checks
            s3_client: boto3 client for QC rules S3 bucket
        """
        super().__init__(client=client)
        self.__file_input = file_input
        self.__redcap_con = redcap_con
        self.__s3_client = s3_client

    @classmethod
    def create(
            cls, context: GearToolkitContext,
            parameter_store: Optional[ParameterStore]
    ) -> 'FormQCCheckerVisitor':
        """Creates a form-qc-checker execution visitor.

        Args:
          context: the gear context
          parameter_store: the parameter store
        Raises:
          GearExecutionError if any error occurred while parsing gear configs
        """
        assert parameter_store, "Parameter store expected"

        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)
        file_input = InputFileWrapper.create(input_name='form_data_file',
                                             context=context)

        rules_s3_bucket: str = get_config(gear_context=context,
                                          key='rules_s3_bucket',
                                          default='nacc-qc-rules')
        qc_checks_db_path: str = get_config(gear_context=context,
                                            key='qc_checks_db_path',
                                            default='/redcap/aws/qcchecks')

        try:
            redcap_params = parameter_store.get_redcap_report_parameters(
                param_path=qc_checks_db_path)
        except ParameterError as error:
            raise GearExecutionError(f'Parameter error: {error}') from error

        s3_client = S3BucketReader.create_from_environment(rules_s3_bucket)
        if not s3_client:
            raise GearExecutionError(
                f'Unable to access S3 bucket {rules_s3_bucket}')

        try:
            redcap_con = REDCapReportConnection.create_from(redcap_params)
        except REDCapConnectionError as error:
            raise GearExecutionError(error)

        return FormQCCheckerVisitor(client=client,
                                    file_input=file_input,
                                    redcap_con=redcap_con,
                                    s3_client=s3_client)

    def run(self, context: GearToolkitContext):
        """Runs the form-qc-checker app.

        Args:
            context: the gear execution context
        """

        assert context, 'Gear context required'

        run(client_wrapper=self.client,
            input_wrapper=self.__file_input,
            s3_client=self.__s3_client,
            gear_context=context,
            redcap_connection=self.__redcap_con)


def main():
    """Load necessary environment variables, create Flywheel, S3 connections,
    invoke QC app."""

    GearEngine.create_with_parameter_store().run(
        gear_type=FormQCCheckerVisitor)


if __name__ == "__main__":
    main()
