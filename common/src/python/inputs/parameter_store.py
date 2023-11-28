"""Module for getting proxy object for AWS SSM parameter store object."""
import logging
from typing import TypedDict

from inputs.environment import get_environment_variable
from ssm_parameter_store import EC2ParameterStore

log = logging.getLogger(__name__)


class REDCapReportParameters(TypedDict):
    """Dictionary type for parameters needed to access a REDCap report."""
    url: str
    token: str
    reportid: str


class S3Parameters(TypedDict):
    """Dictionary type for parameters to access an S3 bucket."""
    accesskey: str
    secretkey: str
    region: str
    bucket: str


class ParameterError(Exception):
    """Error class for errors that occur when reading parameters."""


class ParameterStore:
    """Wrapper class for parameter store to pull particular parameters."""

    def __init__(self, parameter_store: EC2ParameterStore) -> None:
        self.__store = parameter_store

    def get_api_key(self) -> str:
        """Returns the GearBot API key."""
        parameter_name = 'apikey'
        parameter_path = f'/prod/flywheel/gearbot/{parameter_name}'
        parameter = self.__store.get_parameter(parameter_path, decrypt=True)
        apikey = parameter.get(parameter_name)
        if not apikey:
            raise ParameterError("No API Key found")

        return apikey

    def get_redcap_report_connection(
            self, param_path: str) -> REDCapReportParameters:
        """Pulls URL and Token for REDCap project from SSM parameter store.

        Args:
        store: the parameter store object
        """
        parameters = self.__store.get_parameters_by_path(path=param_path)
        url = parameters.get('url')
        token = parameters.get('token')
        report_id = parameters.get('reportid')
        if not url or not token or not report_id:
            raise ParameterError(
                f"Missing REDCap report parameters at {param_path}")

        return {'reportid': report_id, 'token': token, 'url': url}

    def get_s3_parameters(self, param_path: str) -> S3Parameters:
        """Pulls S3 access credentials from the SSM parameter store at the
        given path.

        Args:
          param_path: the path in the parameter store
        Returns:
          the S3 credentials stored at the parameter path
        Raises:
          ParameterError if any of the credentials are missing
        """
        parameters = self.__store.get_parameters_by_path(path=param_path)
        access_key = parameters.get('accesskey')
        secret_key = parameters.get('secretkey')
        region = parameters.get('region')
        bucket_name = parameters.get('bucket')
        if not access_key or not secret_key or not region or not bucket_name:
            raise ParameterError(
                f'Missing S3 bucket parameters at {param_path}')

        return {
            'accesskey': access_key,
            'bucket': bucket_name,
            'region': region,
            'secretkey': secret_key
        }

    @classmethod
    def create_from_environment(cls) -> 'ParameterStore':
        """Gets a proxy object for the parameter store if AWS credentials are
        set. Expects AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID, and
        AWS_DEFAULT_REGION.

        Returns:
            parameter store object if credentials are valid, and None otherwise
        """
        secret_key = get_environment_variable('AWS_SECRET_ACCESS_KEY')
        access_id = get_environment_variable('AWS_ACCESS_KEY_ID')
        region = get_environment_variable('AWS_DEFAULT_REGION')
        if not secret_key or not access_id or not region:
            raise ParameterError("Environment variables not found")

        return ParameterStore(
            EC2ParameterStore(aws_access_key_id=access_id,
                              aws_secret_access_key=secret_key,
                              region_name=region))
