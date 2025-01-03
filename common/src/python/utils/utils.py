"""Utility functions."""

import json
import logging
from typing import Any, Dict, List, Optional

from flywheel.file_spec import FileSpec
from flywheel.models.file_entry import FileEntry
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from outputs.outputs import convert_json_to_csv_stream

log = logging.getLogger(__name__)


def is_duplicate_record(record1: str,
                        record2: str,
                        content_type: Optional[str] = None) -> bool:
    """Check whether the two records are identical.

    Args:
        record1: First record
        record2: Second record

    Returns:
        True if a duplicate detected, else false
    """

    if not content_type or content_type != 'application/json':
        return (record1 == record2)

    try:
        dict1 = sorted(json.loads(record1).items())
        dict2 = sorted(json.loads(record2).items())
        return (dict1 == dict2)
    except json.JSONDecodeError as error:
        log.warning('Error in converting records to JSON format - %s', error)
        return False

    # TODO: Handle other content types


def update_file_info_metadata(file: FileEntry,
                              input_record: Dict[str, Any],
                              modality: str = 'Form') -> bool:
    """Set file modality and info.forms.json metadata.

    Args:
        file: Flywheel file object
        input_record: input visit data
        modality: file modality (defaults to Form)

    Returns:
        True if metadata update is successful
    """

    # remove empty fields
    non_empty_fields = {k: v for k, v in input_record.items() if v is not None}
    info = {"forms": {"json": non_empty_fields}}

    try:
        file.update(modality=modality)
        file.update_info(info)
    except ApiException as error:
        log.error('Error in setting file %s metadata - %s', file.name, error)
        return False

    return True


def update_qc_error_metadata(error_log_name: str,
                             destination_prj: ProjectAdaptor, gear_name: str,
                             state: str, errors: List[Dict[str, Any]],
                             fieldnames: List[str]) -> bool:
    """Update error log file and store error metadata in file.info.qc.

    Args:
        error_log_name: error log file name
        destination_prj: Flywheel project adaptor
        gear_name: gear that generated errors
        state: gear execution status [PASS|FAIL|NA]
        errors: list of error objects, expected to be JSON dicts
        fieldnames: list of error metadata fields (keys for the dict)

    Returns:
        bool: True if metadata update is successful, else False
    """

    header = True
    contents = ''

    current_log = destination_prj.get_file(error_log_name)
    # append to existing error details if any
    if current_log:
        contents = current_log.read() + '\n'
        header = False

    if errors:
        contents += convert_json_to_csv_stream(data=errors,
                                               fieldnames=fieldnames,
                                               header=header).getvalue()

    error_file_spec = FileSpec(name=error_log_name,
                               contents=contents,
                               content_type='text')
    try:
        destination_prj.upload_file(error_file_spec)
        destination_prj.reload()
        new_file = destination_prj.get_file(error_log_name)
    except ApiException as error:
        log.error(f'Failed to upload file {error_log_name} to '
                  f'{destination_prj.group}/{destination_prj.label}: {error}')
        return False

    try:
        info = {
            "qc": {
                gear_name: {
                    "validation": {
                        "state": state.upper(),
                        "data": errors
                    }
                }
            }
        }
        new_file.update_info(info)
    except ApiException as error:
        log.error('Error in setting QC metadata in file %s - %s',
                  error_log_name, error)
        return False

    return True
