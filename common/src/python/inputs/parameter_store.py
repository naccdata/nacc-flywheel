"""Module for getting proxy object for AWS SSM parameter store object."""
import logging

from botocore.exceptions import ClientError, ParamValidationError
from inputs.environment import get_environment_variable
from pydantic import TypeAdapter, ValidationError
from ssm_parameter_store import EC2ParameterStore
from typing_extensions import Type, TypedDict, TypeVar

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


class RDSParameters(TypedDict):
    """Dictionary type for parameters to access MySQL RDS."""
    host: str
    user: str
    password: str


class ParameterError(Exception):
    """Error class for errors that occur when reading parameters."""


# TODO: remove type ignore when using python 3.12 or above
P = TypeVar('P', bound=TypedDict)  # type: ignore


class ParameterStore:
    """Wrapper class for parameter store to pull particular parameters."""

    def __init__(self, parameter_store: EC2ParameterStore) -> None:
        self.__store = parameter_store

    def get_parameters(self, *, param_type: Type[P], parameter_path: str) -> P:
        """Pulls the parameters at the path and checks that they match the
        given TypedDict.

        Args:
          type: the subclass of TypedDict
          parameter_path: the path in the parameter store
        Returns:
          the dictionary of parameters
        Raises:
          ParameterError if the parameters don't match the type
        """
        parameters = self.__store.get_parameters_by_path(path=parameter_path)
        type_adapter = TypeAdapter(param_type)
        try:
            return type_adapter.validate_python(parameters)
        except ValidationError as error:
            raise ParameterError(
                f"Incorrect parameters at {parameter_path}: {error}"
            ) from error

    # pylint disable=(line-to-long)
    def get_api_key(self, path_prefix: str) -> str:
        """Returns the GearBot API key.

        Args:
          path_prefix: the prefix for the parameter path
        Returns:
          the GearBot API key
        Raises:
          ParameterError: if the API key is not found
        """
        parameter_name = 'apikey'
        parameter_path = f'{path_prefix}/{parameter_name}'
        try:
            parameter = self.__store.get_parameter(parameter_path,
                                                   decrypt=True)

        except self.__store.client.exceptions.ParameterNotFound as error:  # type: ignore
            raise ParameterError("No API Key found") from error

        apikey = parameter.get(parameter_name)
        if not apikey:
            raise ParameterError("No API Key found")

        return apikey

    def get_redcap_project_prameters(self, *, base_path: str, pid: int,
                                     report_id: int) -> REDCapReportParameters:
        """Pulls URL and Token for the respective REDCap project from SSM
        parameter store.

        Args:
          base_path: base path in the parameter store
          pid: REDCap project ID
          report_id: REDCap report ID
        Returns:
          the REDCap credentials stored at the parameter path
        Raises:
          ParameterError if any of the credentials are missing
        """

        if not base_path.endswith('/'):
            base_path += '/'

        param_path = base_path + 'pid_' + str(pid)
        try:
            prj_params = self.__store.get_parameters_by_path(param_path,
                                                             decrypt=True)
        except (ClientError, ParamValidationError) as error:
            raise ParameterError(
                f"Failed to retrieve parameters at {param_path}") from error

        if (not prj_params or 'url' not in prj_params
                or 'token' not in prj_params):
            raise ParameterError(f"Incorrect parameters at {param_path}")

        url = prj_params.get('url')
        token = prj_params.get('token')

        if not url or not token:
            raise ParameterError(f"Incorrect parameters at {param_path}")

        return REDCapReportParameters(url=url,
                                      token=token,
                                      reportid=str(report_id))

    def get_redcap_report_parameters(
            self, param_path: str) -> REDCapReportParameters:
        """Pulls URL, Token, and ReportID for REDCap report from SSM parameter
        store.

        Args:
          param_path: the path in the parameter store
        Returns:
          the REDCap report credentials stored at the parameter path
        Raises:
          ParameterError if any of the credentials are missing
        """
        return self.get_parameters(param_type=REDCapReportParameters,
                                   parameter_path=param_path)

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
        return self.get_parameters(param_type=S3Parameters,
                                   parameter_path=param_path)

    def get_rds_parameters(self, param_path: str) -> RDSParameters:
        """Pulls RDS parameters from the SSM parameter store at the given path.

        Args:
          param_path: the path in the parameter store
        Returns:
          the RDS credentials stored at the parameter path
        Raises:
          ParameterError if any of the credentials are missing
        """
        return self.get_parameters(param_type=RDSParameters,
                                   parameter_path=param_path)

    @classmethod
    def create_from_environment(cls) -> 'ParameterStore':
        """Gets a proxy object for the parameter store if AWS credentials are
        set. Expects AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID, and
        AWS_DEFAULT_REGION.

        Returns:
            parameter store object if credentials are valid, and None otherwise
        Raises:
            ParameterError if any of the environment variables are missing
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
