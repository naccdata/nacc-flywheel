"""Defines Refresh REDCap Download URLs."""

import logging
import json
from redcap.redcap_connection import REDCapConnection
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)

def refresh_url(project, redcap_con, subject_label='',reader_email=''):

    print(f'refreshing urls for subject: {subject_label} and reader: {reader_email}')
    
    subject = project.subjects.find_one(f'label={subject_label}')

    session = subject.sessions()[0]

    acquisition = session.acquisitions()[0]

    for file in acquisition.files:
        if file.name.endswith('.zip'):
            dicom_file = file

    file_download_url = acquisition.get_file_download_url(dicom_file.name)

    print(f'file_download_url: {file_download_url}')

    record = {
        'record_id' : f'{reader_email}-{subject_label}',
        'download_link' : file_download_url
    }

    record_str = json.dumps([record])

    #print(record_str)

    response = redcap_con.import_records(record_str)

    return response

def run(*,
        proxy: FlywheelProxy, redcap_con):
    """Runs ADD DETAIL process.
    
    Args:
      proxy: the proxy for the Flywheel instance
    """


    #subject_label = 'calibration004'
    #reader_email = 'djpeters@uw.edu'

    project_id='66df6928917dfee283a2769b'
    project = proxy.get_project_by_id(project_id)

    #print(redcap_con.export_field_names())

    print(redcap_con.export_records())

    existing_records=redcap_con.export_records()

    for record in existing_records:

        print(record)

        response = refresh_url(project, redcap_con,
                               subject_label=record['subject'],
                               reader_email=record['reader_email'])
        print(response)

    print('hello world')

    pass
