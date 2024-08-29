"""Defines REDCap to Flywheel Transfer."""

import json
import logging
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, TextIO

import pandas as pd
from flywheel import Project
from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import GearExecutionError
from redcap.redcap_connection import REDCapConnectionError, REDCapReportConnection

log = logging.getLogger(__name__)


def upload_to_flywheel(visits: List[Dict[str, Any]], output_file: TextIO,
                       extra_fields: List[str]):
    """Convert the visits details to CSV format and upload to Flywheel.

    Args:
        visits: List of new/updated visits
        output_file: output file created in the Flywheel ingest project
        extra_fields: list of extra fields to be dropped before upload

    Raises:
        GearExecutionError if CSV upload fails
    """

    input_df = pd.DataFrame(visits)

    # drop any extra columns that are not part of the module schema
    if extra_fields:
        output_df = input_df.drop(labels=extra_fields, axis=1, errors='ignore')

    try:
        output_df.to_csv(path_or_buf=output_file,
                         index=False,
                         doublequote=False)
    except Exception as error:
        raise GearExecutionError(
            f'Problem occurred while writing CSV: {error}') from error


def reset_upload_checkbox(redcap_con: REDCapReportConnection,
                          visits: List[Dict[str, str]], timestamp: datetime):
    """Reset the upload checkboxes in REDCap records.

    Args:
        redcap_con: API connection to REDCap project
        visits: List of new/updated visits
        timestamp: Upload timestamp

    Raises:
        GearExecutionError if failed to update REDCap records
    """

    updates = []

    for visit in visits:
        update = {}
        update[redcap_con.primary_key_field] = visit[
            redcap_con.primary_key_field]
        if redcap_con.has_repeating_instruments_or_events():
            update['redcap_event_name'] = visit['redcap_event_name']
            update['redcap_repeat_instance'] = visit['redcap_repeat_instance']
        update['upld_ready___1'] = '0'
        update['upld_time'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        updates.append(update)

    try:
        num_updated = redcap_con.import_records(json.dumps(updates))
        log.info('Number of updated records: %s', num_updated)
    except REDCapConnectionError as error:
        raise GearExecutionError(error.message) from error


def validate_redcap_report(redcap_con: REDCapReportConnection,
                           record: Dict[str, str],
                           schema: Dict[str, Any]) -> List[str]:
    """Check whether the required fields included in the report.

    Args:
        redcap_con: API connection to REDCap project
        record: sample record from the report
        schema: expected schema for the module

    Returns:
        List(str): list of extra fields included in the record that are
            not in the schema for the module (if any)
    Raises:
        GearExecutionError if required fields are missing in the report
    """

    if redcap_con.primary_key_field not in record:
        raise GearExecutionError(
            f'Primary key {redcap_con.primary_key_field} not included '
            f'in project {redcap_con.pid} report {redcap_con.report_id}')

    if redcap_con.has_repeating_instruments_or_events():
        if ('redcap_event_name' not in record
                or 'redcap_repeat_instance' not in record):
            raise GearExecutionError(
                f'REDCap repeating instance fields not included '
                f'in project {redcap_con.pid} report {redcap_con.report_id}')

    extra_fields = set(record.keys()).difference(set(schema.keys()))
    return list(extra_fields)


def run(*, gear_context: GearToolkitContext,
        redcap_con: REDCapReportConnection, redcap_pid: str, module: str,
        fw_group: str, fw_project: Project):
    """Download new/updated records from REDCap and upload to Flywheel as a CSV
    file.

    Args:
        fw_prj_adaptor: Flywheel project to transfer data
        redcap_con: API connection to REDCap project
        redcap_pid: REDCap project id
        module: Forms module
        fw_group: Flywheel group id
        fw_project: Flywheel project container

    Raises:
        GearExecutionError if any problem occurs during the transfer
    """

    try:
        records_list = redcap_con.get_report_records()
    except REDCapConnectionError as error:
        raise GearExecutionError(error.message) from error

    if len(records_list) == 0:
        log.info(
            'No new/updated visits found in REDCap project pid=%s module=%s '
            'for Flywheel project %s/%s', redcap_pid, module, fw_group,
            fw_project.label)
        return

    schema_file = module.lower() + '-schema.json'
    try:
        schema = json.loads(fw_project.read_file(schema_file))
    except (ApiException, JSONDecodeError) as error:
        raise GearExecutionError(
            f'Failed to read schema file {schema_file}: {error}') from error

    if 'definitions' not in schema:
        raise GearExecutionError(
            f'Field definitions not found in schema file {schema_file}')

    extra_fields = validate_redcap_report(redcap_con, records_list[0],
                                          schema['definitions'])

    timestamp = datetime.now()
    file_name = 'redcapingest-' + timestamp.strftime(
        '%Y%m%d-%H%M%S') + '-' + module + '.csv'

    with gear_context.open_output(file_name, mode='w',
                                  encoding='utf-8') as output_file:
        upload_to_flywheel(records_list, output_file, extra_fields)

    reset_upload_checkbox(redcap_con, records_list, timestamp)
