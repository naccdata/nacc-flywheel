"""Defines csv_center_splitter."""
import io
import logging

from flywheel import FileSpec
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from inputs.csv_reader import split_csv_by_key
from outputs.outputs import CSVWriter
from projects.project_mapper import build_project_map

log = logging.getLogger(__name__)

def run(*,
        proxy: FlywheelProxy,
        input_filepath: str,
        input_filename: str,
        adcid_key: str,
        target_project: str,
        delimiter: str = ','):
    """Runs the CSV Center Splitter. Splits an input CSV by ADCID and uploads
    to each center's target project.

    Args:
        proxy: the proxy for the Flywheel instance
        input_filepath: The input CSV to split on
        input_filename: The name of the input CSV, used to build the filename
            for split files
        adcid_key: The name of the header column the ADCID is listed under
        target_project: The FW target project to write results to
        delimiter: The CSV's delimiter; defaults to ','
    """
    # split CSV by ADCID key
    split_data, headers = split_csv_by_key(input_filepath=input_filepath,
                                           header_key=adcid_key,
                                           delimiter=delimiter)

    # build project map from ADCID to FW project for upload
    project_map = build_project_map(proxy=proxy,
                                    destination_label=target_project,
                                    centers=list(split_data.keys()))

    if not project_map:
        raise ValueError(f"No {target_project} projects found")

    # make sure all expected projects are there before upload
    missing_projects = []
    for adcid in split_data:
        if f'adcid-{adcid}' not in project_map:
            missing_projects.append(adcid)

    if missing_projects:
        raise ValueError(
            f"Missing {target_project} projects for the following " +
            f"ADCIDs: {missing_projects}")

    log.info("Writing split results for each ADCID...")

    # write results to each center's project
    for adcid, data in split_data.items():
        project = project_map[f'adcid-{adcid}']

        contents = io.StringIO()
        writer = CSVWriter(contents, headers)
        for row in data:
            writer.write(row)

        contents = contents.getvalue()
        filename = f'{adcid}_{input_filename}'
        file_spec = FileSpec(name=filename,
                             contents=contents,
                             content_type='text/csv',
                             size=len(contents))

        log.info(
            f"Uploading {filename} for ADCID {adcid}, project ID {project.id}")
        project.upload_file(file_spec)
