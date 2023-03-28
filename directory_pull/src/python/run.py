"""Script to pull directory information and convert to file expected by the
user management gear."""
import logging
import sys

from inputs.environment import get_api_key, get_environment_variable
from redcap.nacc_directory import UserDirectoryEntry
from redcap.redcap_connection import REDCapConnection, REDCapConnectionError

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def main() -> None:
    """Main method for directory pull.

    Expects several information needed for access to user access report
    from directory on REDCap, and api key for flywheel. These must be
    given as environment variables.
    """
    api_key = get_api_key()
    if not api_key:
        log.error('No API key: expecting FW_API_KEY to be set')
        sys.exit(1)

    url_variable = 'NACC_DIRECTORY_URL'
    directory_url = get_environment_variable(url_variable)
    if not directory_url:
        log.error('No URL: expecting %s to be set', url_variable)
        sys.exit(1)

    token_variable = 'NACC_DIRECTORY_TOKEN'
    directory_token = get_environment_variable(token_variable)
    if not directory_token:
        log.error('No project token: expecting %s to be set', token_variable)
        sys.exit(1)

    report_id_variable = 'USER_REPORT_ID'
    user_report_id = get_environment_variable(report_id_variable)
    if not user_report_id:
        log.error('No report ID: expecting %s to be set', report_id_variable)
        sys.exit(1)

    directory_proxy = REDCapConnection(token=directory_token,
                                       url=directory_url)

    try:
        user_report = directory_proxy.request_json_value(
            data={
                'token': directory_token,
                'content': 'report',
                'format': 'json',
                'report_id': str(user_report_id),
                'csvDelimiter': '',
                'rawOrLabel': 'raw',
                'rawOrLabelHeaders': 'raw',
                'exportCheckboxLabel': 'false',
                'returnFormat': 'json'
            },
            message="pulling user report from NACC Directory")
    except REDCapConnectionError as error:
        log.error('Failed to pull users from directory: %s', error.error)
        sys.exit(1)

    user_entries = []
    for user_record in user_report:
        entry = UserDirectoryEntry.create_from_record(user_record)
        if entry:
            user_entries.append(entry)
