"""Classes and methods for connecting to REDCap via API."""
import json
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

import requests
from inputs.parameter_store import REDCapParameters, REDCapReportParameters
from requests import Response


class REDCapSuperUserConnection:
    """REDCap connection using super API token.

    Can only be used to create projects, other API methods doesn't work
    for super token.
    """

    def __init__(self, *, token: str, url: str) -> None:
        """Initializes a REDCap connection using the super API token and URL.

        Args:
            token: Super API token for the REDCap project.
            url: URL of REDCap instance
        """
        self.__token = token
        self.__url = url

    @property
    def url(self) -> str:
        """REDCap API URL."""
        return self.__url

    @classmethod
    def create_from(
            cls, parameters: REDCapParameters) -> 'REDCapSuperUserConnection':
        """Creates a REDCap connection with given parameters.

        Args:
          parameters: the parameters
        Returns:
          the connection using the parameters
        """
        return REDCapSuperUserConnection(token=parameters['token'],
                                         url=parameters['url'])

    def create_project(self,
                       *,
                       title: str,
                       purpose: Optional[int] = 4,
                       project_xml: Optional[str] = None) -> str:
        """Creates a new REDCap project using the super API token.

        Args:
            title: Title of the REDCap project
            purpose (optional): Project purpose, default 4 (Operational Support)
            project_xml (optional): REDCap XML template, defaults to None.

        Returns:
            str: REDCap API token for the created project

        Raises:
          REDCapConnectionError if the response has an error
        """
        properties = {"project_title": title, "purpose": purpose}
        data = json.dumps([properties])

        fields = {
            'token': self.__token,
            'content': 'project',
            'format': 'json',
            'data': data,
        }
        if project_xml:
            fields['odm'] = project_xml

        try:
            response = requests.post(self.__url, data=fields)
        except (requests.exceptions.SSLError,
                requests.exceptions.ConnectionError) as error:
            raise REDCapConnectionError(
                message=f"Error connecting to {self.__url} - {error}"
            ) from error

        if not response.ok:
            raise REDCapConnectionError(message=error_message(
                message='creating project', response=response))

        return response.text


class REDCapConnection:
    """Class managing the API requests to a REDCap project.

    Provides a post method to adapting classes. See
    `REDCapReportConnection`
    """

    def __init__(self, *, token: str, url: str) -> None:
        """Initializes a REDCap connection using the given project token and
        URL.

        Args:
          token: API token for the REDCap project.
          url: URL of REDCap instance
        """
        self.__token = token
        self.__url = url

    @classmethod
    def create_from(cls, parameters: REDCapParameters) -> 'REDCapConnection':
        """Creates a REDCap connection with given parameters.

        Args:
          parameters: REDCap parameters object with token and url

        Returns:
          the connection using the parameters
        """
        return REDCapConnection(token=parameters['token'],
                                url=parameters['url'])

    def post_request(self,
                     *,
                     data: Dict[str, str],
                     result_format: Optional[str] = None,
                     error_format: str = 'json') -> Any:
        """Posts a request to the REDCap project with the given data object.

        Returns:
          The response from posting the request.

        Raises:
          REDCapConnectionError if there is an error connecting to the
          specified project
        """
        data.update({'token': self.__token, 'returnFormat': error_format})
        if result_format:
            data['format'] = result_format
        try:
            response = requests.post(self.__url, data=data)
        except (requests.exceptions.SSLError,
                requests.exceptions.ConnectionError) as error:
            raise REDCapConnectionError(
                message=f"Error connecting to {self.__url} - {error}"
            ) from error

        return response

    def request_json_value(self, *, data: Dict[str, str], message: str) -> Any:
        """Posts a request to the REDCap project with the given data object
        expecting a JSON value.

        Returns:
          The object for the JSON value.

        Raises:
          REDCapConnectionError if the response has an error.
        """
        response = self.post_request(data=data, result_format='json')
        if not response.ok:
            raise REDCapConnectionError(
                message=error_message(message=message, response=response))
        try:
            return response.json()
        except JSONDecodeError as error:
            raise REDCapConnectionError(message=message) from error

    def request_text_value(self,
                           *,
                           data: Dict[str, str],
                           result_format: Optional[str] = None,
                           message: str) -> str:
        """Posts a request to the REDCap project with the given data object
        expecting a text value.

        Returns:
          The text string for the returned value.

        Raises:
          REDCapConnectionError if the response has an error.
        """
        response = self.post_request(data=data, result_format=result_format)
        if not response.ok:
            raise REDCapConnectionError(
                message=error_message(message=message, response=response))

        return response.text

    def __export_field_names(self) -> List[Dict[str, str]]:
        """Get the export field names for the project variables.

        Returns:
            The list of field names (JSON objects) with info

        Raises:
          REDCapConnectionError if the response has an error
        """

        message = "exporting list of field names"
        data = {
            'content': 'exportFieldNames',
        }

        return self.request_json_value(data=data, message=message)

    def __export_project_info(self) -> Dict[str, Any]:
        """Export the basic attributes of the project.

        Returns:
            Project attributes as JSON object

        Raises:
          REDCapConnectionError if the response has an error
        """

        message = "exporting project info"
        data = {'content': 'project'}

        return self.request_json_value(data=data, message=message)


class REDCapReportConnection(REDCapConnection):
    """Defines a REDCap connection meant for reading a particular report."""

    def __init__(self, *, token: str, url: str, report_id: str) -> None:
        super().__init__(token=token, url=url)
        self.report_id = report_id

    @classmethod
    def create_from(
        cls,
        parameters: REDCapReportParameters  # type: ignore[override]
    ) -> 'REDCapReportConnection':
        """Creates a REDCap connection with report parameters.

        Args:
          parameters: the parameters
        Returns:
          the connection using the parameters
        """
        return REDCapReportConnection(token=parameters['token'],
                                      url=parameters['url'],
                                      report_id=parameters['reportid'])

    def get_report_records(self) -> List[Dict[str, str]]:
        """Gets the report from the REDCap connection.

        Returns:
          list of records from the report
        """
        message = f"pulling report id {self.report_id}"
        data = {
            'content': 'report',
            'report_id': str(self.report_id),
            'csvDelimiter': '',
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false'
        }
        return self.request_json_value(data=data, message=message)


def error_message(*, message: str, response: Response) -> str:
    """Build an error message from the given message and HTTP response.

    Returns:
      The error string
    """
    return (f"Error: {message}\nHTTP Error:{response.status_code} "
            f"{response.reason}: {response.text}")


class REDCapConnectionError(Exception):
    """Exception class representing error connecting to a REDCap project."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def __str__(self) -> str:
        return self.message

    @property
    def message(self):
        """The error message."""
        return self._message
