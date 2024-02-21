"""Defines REDCap to Flywheel Transfer."""
import csv
import io
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List

from flywheel import FileSpec
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from redcap.redcap_connection import (REDCapConnectionError,
                                      REDCapReportConnection)

log = logging.getLogger(__name__)


def upload_to_flywheel(fw_prj_adaptor: ProjectAdaptor,
                       visits: List[Dict[str, str]], timestamp: datetime):
    """Convert the visits details to CSV format and upload to Flywheel.

    Args:
        fw_prj_adaptor (ProjectAdaptor): Flywheel project to transfer data
        visits (List[Dict[str, str]]): List of new/updated visits
        timestamp (datetime): Upload timestamp
    """
    contents = io.StringIO()
    fields = visits[0].keys()
    writer = csv.DictWriter(contents, fieldnames=fields)
    writer.writeheader()
    writer.writerows(visits)

    file_name = 'udsv4_' + timestamp.strftime('%Y-%m-%d-%H%M%S') + '.csv'
    file_spec = FileSpec(name=file_name,
                         contents=contents.getvalue(),
                         content_type='text/csv')

    fw_prj_adaptor.upload_file(file_spec)  # TODO - catch upload errors


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


def run(*, fw_prj_adaptor: ProjectAdaptor, redcap_con: REDCapReportConnection,
        redcap_pid: str):
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
    upload_to_flywheel(fw_prj_adaptor, records_list, timestamp)
    reset_upload_checkbox(redcap_con, records_list, timestamp)
