"""Defines REDCap to Flywheel Transfer."""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, TextIO

import pandas as pd
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from flywheel_gear_toolkit import GearToolkitContext
from redcap.redcap_connection import (REDCapConnectionError,
                                      REDCapReportConnection)

log = logging.getLogger(__name__)


def upload_to_flywheel(visits: List[Dict[str, Any]], output_file: TextIO):
    """Convert the visits details to CSV format and upload to Flywheel.

    Args:
        visits (List[Dict[str, str]]): List of new/updated visits
        output_file (TextIO): output file created in Flywheel ingest project
    """

    input_df = pd.DataFrame(visits)
    # drop REDCap specific columns
    output_df = input_df.drop([
        'redcap_event_name', 'redcap_repeat_instrument',
        'redcap_repeat_instance', 'upld_ready___1'
    ],
                              axis=1)
    output_df.to_csv(path_or_buf=output_file, index=False, doublequote=False)


def reset_upload_checkbox(redcap_con: REDCapReportConnection,
                          visits: List[Dict[str, str]], timestamp: datetime):
    """Reset the upload checkboxes in REDCap records.

    Args:
        redcap_con (REDCapReportConnection): API connection to REDCap project
        visits (List[Dict[str, str]]): List of new/updated visits
        timestamp (datetime): Upload timestamp
    """
    updates = []
    for visit in visits:
        update = {}
        update['ptid'] = visit['ptid']
        update['redcap_event_name'] = visit['redcap_event_name']
        update['redcap_repeat_instance'] = visit['redcap_repeat_instance']
        update['upld_ready___1'] = '0'
        update['upld_time'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        updates.append(update)

    try:
        num_updated = redcap_con.import_records(json.dumps(updates))
        log.info('Number of updated records: %s', num_updated)
    except REDCapConnectionError as error:
        log.error(error.message)
        sys.exit(1)


def run(*, gear_context: GearToolkitContext, fw_prj_adaptor: ProjectAdaptor,
        redcap_con: REDCapReportConnection, redcap_pid: str):
    """Download new/updated records from REDCap and upload to Flywheel as a CSV
    file.

    Args:
        fw_prj_adaptor: Flywheel project to transfer data
        redcap_con: API connection to REDCap project
        redcap_pid: REDCap project id
    """

    try:
        records_list = redcap_con.get_report_records()
    except REDCapConnectionError as error:
        log.error(error.message)
        sys.exit(1)

    if len(records_list) == 0:
        log.info(
            'No new/updated visits found in REDCap project '
            '%s for Flywheel project %s/%s', redcap_pid, fw_prj_adaptor.group,
            fw_prj_adaptor.label)
        sys.exit(0)

    timestamp = datetime.now()
    file_name = 'udsv4_' + timestamp.strftime('%Y-%m-%d-%H%M%S') + '.csv'
    with gear_context.open_output(file_name, mode='w',
                                  encoding='utf-8') as output_file:
        upload_to_flywheel(records_list, output_file)
    reset_upload_checkbox(redcap_con, records_list, timestamp)
