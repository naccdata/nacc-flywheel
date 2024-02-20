"""Classes and methods for connecting to REDCap."""
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

import requests
from inputs.parameter_store import REDCapReportParameters
from requests import Response


class REDCapConnection:
    """Class managing the connection to a REDCap project.

    Provides a post method to adapting classes. See `ProjectReader`
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

    def post_request(self,
                     *,
                     data: Dict[str, str],
                     result_format: Optional[str] = None,
                     return_format: str = 'json') -> Any:
        """Posts a request to the REDCap project with the given data object.

        Returns:
          The response from posting the request.

        Raises:
          REDCapConnectionException if there is an error connecting to the
          specified project
        """
        data.update({'token': self.__token, 'returnFormat': return_format})
        if result_format:
            data['format'] = result_format
        try:
            response = requests.post(self.__url, data=data)
        except requests.exceptions.SSLError as error:
            raise REDCapConnectionError(
                message=f"SSL error connecting to {self.__url}") from error

        return response

    def request_json_value(self, *, data: Dict[str, str], message: str) -> Any:
        """Posts a request to the REDCap project with the given data object
        expecting a JSON value.

        Returns:
          The object for the JSON value.

        Raises:
          REDCapConnectionException if the response has an error.
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
            message = "cannot get project XML"
            raise REDCapConnectionError(
                message=error_message(message=message, response=response))

        return response.text


class REDCapReportConnection(REDCapConnection):
    """Defines a REDCap connection meant for reading a particular report."""

    def __init__(self, *, token: str, url: str, report_id: str) -> None:
        super().__init__(token=token, url=url)
        self.report_id = report_id

    @classmethod
    def create_from(
            cls,
            parameters: REDCapReportParameters) -> 'REDCapReportConnection':
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
        return self.request_json_value(
            data={
                'content': 'report',
                'report_id': str(self.report_id),
                'csvDelimiter': '',
                'rawOrLabel': 'raw',
                'rawOrLabelHeaders': 'raw',
                'exportCheckboxLabel': 'false'
            },
            message="pulling user report from NACC Directory")


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
