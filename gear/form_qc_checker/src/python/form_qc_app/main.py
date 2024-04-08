"""Defines functions to carry out the data quality checks for the input form
data file.

Uses nacc-form-validator (https://github.com/naccdata/nacc-form-
validator) for validating the inputs.
"""

import json
import logging
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional

from flywheel_gear_toolkit import GearToolkitContext
from form_qc_app.error_info import ErrorComposer, REDCapErrorStore
from form_qc_app.flywheel_datastore import FlywheelDatastore
from form_qc_app.parser import Keys, Parser, ParserException
from gear_execution.gear_execution import (ClientWrapper, GearExecutionError,
                                           InputFileWrapper)
from outputs.errors import ListErrorWriter
from redcap.redcap_connection import REDCapReportConnection
from s3.s3_client import S3BucketReader
from validator.quality_check import QualityCheck, QualityCheckException

log = logging.getLogger(__name__)


def update_file_metadata(*, gear_context: GearToolkitContext,
                         file_input: Dict[str, Dict[str, Any]],
                         qc_status: bool, error_writer: ListErrorWriter):
    """Write error details to input file metadata and add gear tag.

    Args:
        gear_context: Flywheel gear context
        file_input: file input object from gear context
        qc_status: QC check passed or failed
        error_writer: error output writer
    """

    status_str = "PASS" if qc_status else "FAIL"
    tag = gear_context.config.get('tag', 'form-qc-checker')
    current_tags = gear_context.get_input_file_object_value(
        'form_data_file', 'tags')
    fail_tag = f'{tag}-FAIL'
    pass_tag = f'{tag}-PASS'
    new_tag = f'{tag}-{status_str}'

    if current_tags:
        if fail_tag in current_tags:
            current_tags.remove(fail_tag)
        if pass_tag in current_tags:
            current_tags.remove(pass_tag)
        current_tags.append(new_tag)
    else:
        current_tags = [new_tag]

    gear_context.metadata.add_qc_result(file_input,
                                        name='validation',
                                        state=status_str,
                                        data=error_writer.errors())

    gear_context.metadata.update_file(file_input, tags=current_tags)

    file_name = file_input['location']['name']
    log.info('QC check status for file %s : %s', file_name, status_str)


def validate_required_keys(*, keys: List[str], data: Dict[str, str]) -> bool:
    """Check whether all required keys are present in the input file.

    Args:
        keys: list of keys to validate
        data: input data to validate

    Returns:
        bool: returns True if all keys are present in data
    """

    if not data:
        log.error('Empty input file')
        return False

    present = True
    for key in keys:
        if key not in data:
            log.error('Missing required field %s in input data', key)
            present = False

    return present


def compose_error_metadata(
    *,
    sys_failure: bool,
    error_composer: ErrorComposer,
    error_tree: Optional[Dict[str, Any]],
    codes_map: Optional[Dict[str, Dict]],
):
    """Compose error metadata using validation errors and error code mapping.

    Args:
        sys_failure: True if any system errors occurred during validation
        error_compose: class to compose error metadata
        error_tree: dict like object containing validation error details
        codes_map: schema to map NACC QC check info to validation errors
    """
    if sys_failure:
        error_composer.compose_system_errors_metadata()
    elif codes_map and error_tree is not None:
        error_composer.compose_detailed_error_metadata(error_tree=error_tree,
                                                       err_code_map=codes_map)
    else:
        error_composer.compose_minimal_error_metadata()


# pylint: disable=(too-many-locals)
def run(*,
        client_wrapper: ClientWrapper,
        input_wrapper: InputFileWrapper,
        s3_client: S3BucketReader,
        gear_context: GearToolkitContext,
        redcap_connection: Optional[REDCapReportConnection] = None):
    """Starts QC process for form data input file. Load rule definitions from
    S3, read input data file, runs data validation, generate error report.

    Args:
        client_wrapper: Flywheel SDK client wrapper
        input_wrapper: Gear input file wrapper
        s3_client: boto3 client for QC rules S3 bucket
        gear_context: Flywheel gear context
        redcap_connection (Optional): REDCap project for NACC QC checks

    Raises:
          GearExecutionError if any problem occurrs while validating input file
    """

    if not input_wrapper.file_input:
        raise GearExecutionError('form_data_file input not found')

    file_id = input_wrapper.file_id

    proxy = client_wrapper.get_proxy()
    file = proxy.get_file(file_id)

    try:
        with gear_context.open_input('form_data_file', 'r',
                                     encoding='utf-8') as form_file:
            form_data = json.load(form_file)
    except (FileNotFoundError, JSONDecodeError, TypeError,
            ValueError) as error:
        raise GearExecutionError(
            'Failed to read the input file: {error}') from error

    pk_field = (gear_context.config.get('primary_key', Keys.NACCID)).lower()
    keys = [pk_field, Keys.MODULE]
    if not validate_required_keys(keys=keys, data=form_data):
        raise GearExecutionError('Missing required fields in the input data')

    s3_prefix = form_data[Keys.MODULE]
    if Keys.PACKET in form_data:
        s3_prefix = f'{s3_prefix}/{form_data[Keys.PACKET]}'

    parser = Parser(s3_client)
    try:
        schema = parser.download_rule_definitions(f'{s3_prefix}/rules/')
    except ParserException as error:
        raise GearExecutionError(error) from error

    try:
        codes_map: Optional[Dict[str,
                                 Dict]] = parser.download_rule_definitions(
                                     f'{s3_prefix}/codes/')  # type: ignore
    # TODO - validate code mapping schema and compare with error check schema
    except ParserException as error:
        log.warning(error)
        codes_map = None

    datastore = FlywheelDatastore(client_wrapper.client, file.parents.group,
                                  file.parents.project)

    error_store = REDCapErrorStore(redcap_con=redcap_connection)

    strict = gear_context.config.get("strict_mode", True)
    try:
        qual_check = QualityCheck(pk_field, schema, strict, datastore)
    except QualityCheckException as error:
        raise GearExecutionError(
            f'Failed to initialize QC module: {error}') from error

    valid, sys_failure, dict_errors, error_tree = qual_check.validate_record(
        form_data)

    error_writer = ListErrorWriter(container_id=file_id,
                                   fw_path=proxy.get_lookup_path(file))
    if not valid:
        error_messages = qual_check.validator.get_error_messages()
        error_composer = ErrorComposer(input_data=form_data,
                                       error_store=error_store,
                                       dict_errors=dict_errors,
                                       error_messages=error_messages,
                                       error_writer=error_writer)
        compose_error_metadata(
            sys_failure=sys_failure,
            error_composer=error_composer,
            error_tree=error_tree,  # type: ignore
            codes_map=codes_map)

    update_file_metadata(gear_context=gear_context,
                         file_input=input_wrapper.file_input,
                         qc_status=valid,
                         error_writer=error_writer)
