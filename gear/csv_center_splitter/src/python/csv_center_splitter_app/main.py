"""Defines csv_center_splitter."""

import csv
import io
import logging

from flywheel import FileSpec
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from projects.project_mamper import build_project_map
from outputs.outputs import CSVWriter

log = logging.getLogger(__name__)

def run(*,
        proxy: FlywheelProxy,
        input_filepath: str,
        adcid_key: str,
        target_project: str,
        delimiter: str = ','):
    """Runs the CSV Center Splitter. Splits an input CSV by ADCID and uploads
    to each center's target project.
    
    Args:
        proxy: the proxy for the Flywheel instance
        input_filepath: The input CSV to split on
        adcid_key: The name of the header column the ADCID is listed under
        target_project: The FW target project to write results to
    """
    # split the input CSV by ADCID
    split_data = {}
    headers = None
    with open(input_filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        headers = reader.fieldnames

        if adcid_key not in headers:
            raise ValueError(f"Specified ADCID key '{adcid_key}' not found "
                             + f"in input CSV headers: {input_filepath}")

        for row in reader:
            adcid = row[adcid_index]
            if adcid not in split_data:
                split_data[adcid] = []

            split_data[adcid].append(row)

    # build project map from ADCID to FW project for upload
    project_map = build_project_map(proxy,
                                    destination_label=target_project)

    # make sure all expected projects are there before upload
    missing_projects = []
    for adcid in split_data.keys():
        if f'adcid-{adcid}' not in project_map:
            missing_projects.append(adcid)

    if missing_projects:
        raise ValueError(f"Missing {target_project} projects for the following "
                         + f"ADCIDs: {missing_projects}")

    # write results to each center's project
    for adcid, data in split_data.items():
        project = project_map[f'adcid-{adcid}']

        contents = io.StringIO()
        writer = CSVWriter(contents, headers)
        writer.write(row) for row in data

        file_spec = FileSpec(name=input_filepath,  # TODO - check if it should be the same filename
                             contents=contents,
                             content_type='csv')
