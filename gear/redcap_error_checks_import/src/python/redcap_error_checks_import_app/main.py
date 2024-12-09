"""Defines REDCap Import Error Checks."""
import json
import logging
from io import StringIO
from typing import Dict, List

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import GearExecutionError
from inputs.csv_reader import read_csv
from outputs.errors import ListErrorWriter
from redcap.redcap_connection import (
    REDCapConnection,
    REDCapConnectionError,
)
from s3.s3_client import S3BucketReader

from .error_check_loader import ErrorCheckCSVVisitor

log = logging.getLogger(__name__)


def load_error_check_csv(key: str,
                         file: Dict[str, Dict],
                         error_writer: ListErrorWriter) -> List[Dict, str]:
    """Load the error check CSV.

    Args:
        key: The S3 key to the file
        file: The S3 file object
        error_writer: the ListErrorWriter to write errors to
    Returns:
        List of the validated and read in error checks.
    """
    # parse expected key structure
    # MODULE / FORM_VER / PACKET / files
    # filename expected to be
    # form_<FORM_NAME>_<packet>_error_checks_<type>.csv
    key_parts = key.split('/')
    if key_parts != 4:
        raise ValueError("Expected files to be under "
                         + "MODULE / FORM_VER / PACKET / filename")

    module, form_ver, packet, filename = key_parts
    form_name = filename.split('_')[1]

    visitor = ErrorCheckCSVVisitor(form_name=form_name,
                                   packet=packet,
                                   error_writer=error_writer)

    data = StringIO(file['Body'].read().decode('utf-8'))
    success = read_csv(input_file=data,
                       error_writer=error_writer,
                       visitor=visitor)

    if not success:
        log.error(f"Error occured while reading from {key}")
        return None

    if not visitor.error_checks:
        log.error(f"No error checks found in {key}; invalid file?")
        return None

    return visitor.error_checks


def run(*,
        proxy: FlywheelProxy,
        s3_bucket: S3BucketReader,
        redcap_connection: REDCapConnection,
        fail_fast: bool = False
        ):
    """Runs the REDCAP Error Checks import process.

    Args:
        proxy: the proxy for the Flywheel instance
        s3_bucket: The S3BucketReader
        redcap_connection: The REDCapConnection
        fail_fast: Whether or not to fail fast on error
    """
    bucket = s3_bucket.bucket_name
    file_objects = s3_bucket.read_directory(bucket)

    error_writer = ListErrorWriter(container_id="TODO",
                                   fw_path="TODO")

    for key, file in file_objects.items():
        # Load from files from S3
        log.info(f"Loading error checks from {bucket}/{key}...")
        error_checks = load_error_check_csv(bucket, key, file,
                                            error_writer)

        if not error_checks:
            if fail_fast:
                log.error("fail_fast set to True, halting execution")
                return
            else:
                log.info("Errors encountered, continuing to next file")
                continue

        # Upload to REDCap
        log.info("Importing error checks to REDCap...")
        # import each record in JSON format
        try:
            redcap_conn = redcap_connection
            num_records = redcap_conn.import_records(json.dumps(error_checks),
                                                     data_format='json')
            log.info(f"Imported {num_records} from {bucket}/{key}")
        except REDCapConnectionError as error:
            raise GearExecutionError(error.message) from error

        log.info(f"Successfully imported {bucket}/{key}!")
