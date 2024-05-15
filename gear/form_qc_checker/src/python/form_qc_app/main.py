"""Defines functions to carry out the data quality checks for the input form
data file.

Uses nacc-form-validator (https://github.com/naccdata/nacc-form-
validator) for validating the inputs.
"""

import json
import logging
import re
from csv import DictReader
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from form_qc_app.csv_visitor import FormQCCSVVisitor, read_first_data_row
from form_qc_app.error_info import ErrorComposer, ErrorStore, REDCapErrorStore
from form_qc_app.flywheel_datastore import FlywheelDatastore
from form_qc_app.parser import Keys, Parser, ParserException
from gear_execution.gear_execution import (ClientWrapper, GearExecutionError,
                                           InputFileWrapper)
from outputs.errors import (ListErrorWriter, empty_field_error,
                            empty_file_error, malformed_file_error,
                            missing_header_error, unknown_field_error)
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


def validate_input_file_type(mimetype: str) -> Optional[str]:
    """Check whether the input file type is accepted.

    Args:
        mimetype: input file mimetype

    Returns:
        Optional[str]: If accepted file type, return the type, else None
    """
    if not mimetype:
        return None

    mimetype = mimetype.lower()
    if mimetype.find('json') != -1:
        return 'json'

    if mimetype.find('csv') != -1:
        return 'csv'

    return None


def validate_required_keys(*, keys: List[str], data: Dict[str, str],
                           error_writer: ListErrorWriter) -> bool:
    """Check whether all required keys are present in the input file.

    Args:
        keys: list of keys to validate
        data: input data to validate
        error_writer: error writer object to output error metadata

    Returns:
        bool: returns True if all keys are present in data
    """

    if not data:
        error_writer.write(empty_file_error())
        return False

    present = True
    for key in keys:
        if key not in data or data[key] == '':
            error_writer.write(empty_field_error(key))
            present = False

    return present


def compose_error_metadata(*, sys_failure: bool, error_composer: ErrorComposer,
                           error_tree: Optional[Dict[str, Any]],
                           codes_map: Optional[Dict[str, Dict]],
                           line_number: Optional[int]):
    """Compose error metadata using validation errors and error code mapping.

    Args:
        sys_failure: True if any system errors occurred during validation
        error_composer: class to compose error metadata
        error_tree: dict like object containing validation error details
        codes_map: schema to map NACC QC check info to validation errors
        line_number: line # in CSV file if the record is from CSV
    """
    if sys_failure:
        error_composer.compose_system_errors_metadata(line_number)
    elif codes_map and error_tree is not None:
        error_composer.compose_detailed_error_metadata(error_tree=error_tree,
                                                       err_code_map=codes_map,
                                                       line_number=line_number)
    else:
        error_composer.compose_minimal_error_metadata(line_number)


def process_csv_file(*, csv_reader: DictReader, qual_check: QualityCheck,
                     error_store: ErrorStore, error_writer: ListErrorWriter,
                     codes_map: Optional[Dict[str, Dict]]) -> bool:
    """Read the csv file and validate each record using nacc-form-validator
    library (https://github.com/naccdata/nacc-form-validator)

    Note: Assumes the CSV headers are validated and correct at this point.

    Args:
        csv_reader: CSV DictReader object
        qual_check: NACC data quality checker object
        error_store: database connection to retrieve NACC QC chek info
        error_writer: error writer object to output error metadata
        codes_map: schema to map NACC QC check info to validation errors

    Returns:
        bool: True if all records passed NACC data quality checks, else False
    """

    if not csv_reader.fieldnames:
        error_writer.write(missing_header_error())
        return False

    unknown_fields = set(csv_reader.fieldnames).difference(
        set(qual_check.schema.keys()))

    if unknown_fields:
        for unknown_field in unknown_fields:
            error_writer.write(unknown_field_error(unknown_field))
        return False

    passed_all = True
    for row in csv_reader:
        if not process_data_record(record=row,
                                   qual_check=qual_check,
                                   error_store=error_store,
                                   error_writer=error_writer,
                                   codes_map=codes_map,
                                   line_number=csv_reader.line_num - 1):
            passed_all = False

    return passed_all


def process_data_record(*,
                        record: Dict[str, str],
                        qual_check: QualityCheck,
                        error_store: ErrorStore,
                        error_writer: ListErrorWriter,
                        codes_map: Optional[Dict[str, Dict]] = None,
                        line_number: Optional[int] = None) -> bool:
    """Validate the data record using nacc-form-validator library
    (https://github.com/naccdata/nacc-form-validator)

    Args:
        record: input data record
        qual_check: NACC data quality checker object
        error_store: database connection to retrieve NACC QC chek info
        error_writer: error writer object to output error metadata
        codes_map(optional): schema to map NACC QC checks to validation errors
        line_number (optional): line # in CSV file if the record is from CSV

    Returns:
        bool: True if record passed NACC data quality checks, else False
    """

    valid, sys_failure, dict_errors, error_tree = qual_check.validate_record(
        record)

    if not valid:
        error_messages = qual_check.validator.get_error_messages()
        error_composer = ErrorComposer(input_data=record,
                                       error_store=error_store,
                                       dict_errors=dict_errors,
                                       error_messages=error_messages,
                                       error_writer=error_writer)
        compose_error_metadata(
            sys_failure=sys_failure,
            error_composer=error_composer,
            error_tree=error_tree,  # type: ignore
            codes_map=codes_map,
            line_number=line_number)

    return valid


def load_rule_definition_schemas(
        s3_client: S3BucketReader, input_data: dict[str, Any],
        filename: str) -> tuple[Dict[str, Mapping], Optional[Dict[str, Dict]]]:
    """Download QC rule definitions and error code mappings from S3 bucket.

    Args:
        s3_client: S3 client
        input_data: input data record
        filename: input file name

    Raises:
        GearExecutionError: if error occurred while loading schemas

    Returns:
        rule definition schema, code mapping schema (optional)
    """

    # For CSV input, assumes all the records belong to the same module
    if Keys.MODULE in input_data and input_data[Keys.MODULE]:
        module = str(input_data[Keys.MODULE])
    else:
        module = get_module_name_from_file_suffix(filename)

    if not module:
        raise GearExecutionError(
            f'Failed to extract module information from file {filename}')

    s3_prefix = module.upper()
    if Keys.PACKET in input_data and input_data[Keys.PACKET]:
        s3_prefix = f'{s3_prefix}/{str(input_data[Keys.PACKET]).upper()}'

    parser = Parser(s3_client)
    try:
        schema = parser.download_rule_definitions(f'{s3_prefix}/rules/')
    except ParserException as error:
        raise GearExecutionError(error) from error

    try:
        codes_map: Optional[Dict[str,
                                 Dict]] = parser.download_rule_definitions(
                                     f'{s3_prefix}/codes/')  # type: ignore
    # TODO - validate code mapping schema
    except ParserException as error:
        log.warning(error)
        codes_map = None

    if codes_map:
        diff_keys = set(schema.keys()) ^ (codes_map.keys())
        if diff_keys:
            raise GearExecutionError(
                'Rule definitions and codes definitions does not match, '
                f'list of fields missing in one of the schemas: {diff_keys}')
    return schema, codes_map


def get_module_name_from_file_suffix(filename: str) -> Optional[str]:
    """Get the module name from CSV file suffix.

    Args:
        filename: input file name

    Returns:
        Optional[str]: module name
    """
    module = None
    pattern = '^.*-([a-z]+v[0-9])\\.csv$'
    if match := re.search(pattern, filename, re.IGNORECASE):
        module = match.group(1)

    return module


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

    file_type = validate_input_file_type(input_wrapper.file_type)
    if not file_type:
        raise GearExecutionError(
            f'Unsupported input file type {input_wrapper.file_type}')

    file_id = input_wrapper.file_id
    proxy = client_wrapper.get_proxy()
    try:
        file = proxy.get_file(file_id)
    except ApiException as error:
        raise GearExecutionError(
            f'Failed to find the input file: {error}') from error

    pk_field = (gear_context.config.get('primary_key', Keys.NACCID)).lower()
    error_writer = ListErrorWriter(container_id=file_id,
                                   fw_path=proxy.get_lookup_path(file))
    input_path = Path(input_wrapper.filepath)
    valid = False
    try:
        with open(input_path, mode='r', encoding='utf-8') as file_obj:
            if file_type == 'json':
                try:
                    input_data = json.load(file_obj)
                    if not validate_required_keys(keys=[pk_field, Keys.MODULE],
                                                  data=input_data,
                                                  error_writer=error_writer):
                        input_data = None
                except (JSONDecodeError, TypeError) as error:
                    error_writer.write(malformed_file_error(str(error)))
                    input_data = None
            else:
                csv_visitor = FormQCCSVVisitor(pk_field=pk_field,
                                               error_writer=error_writer)
                input_data = read_first_data_row(input_file=file_obj,
                                                 error_writer=error_writer,
                                                 visitor=csv_visitor)

            if input_data:
                schema, codes_map = load_rule_definition_schemas(
                    s3_client=s3_client,
                    input_data=input_data,
                    filename=input_wrapper.filename)

                datastore = FlywheelDatastore(client_wrapper.client,
                                              file.parents.group,
                                              file.parents.project)

                error_store = REDCapErrorStore(redcap_con=redcap_connection)

                strict = gear_context.config.get("strict_mode", True)
                try:
                    qual_check = QualityCheck(pk_field, schema, strict,
                                              datastore)
                except QualityCheckException as error:
                    raise GearExecutionError(
                        f'Failed to initialize QC module: {error}') from error

                if file_type == 'json':
                    valid = process_data_record(record=input_data,
                                                qual_check=qual_check,
                                                error_store=error_store,
                                                error_writer=error_writer,
                                                codes_map=codes_map)
                else:
                    csv_reader = DictReader(
                        file_obj, dialect=csv_visitor.dialect)  # type: ignore
                    valid = process_csv_file(csv_reader=csv_reader,
                                             qual_check=qual_check,
                                             error_store=error_store,
                                             error_writer=error_writer,
                                             codes_map=codes_map)
    except FileNotFoundError as error:
        raise GearExecutionError(
            f'Failed to read the input file: {error}') from error

    update_file_metadata(gear_context=gear_context,
                         file_input=input_wrapper.file_input,
                         qc_status=valid,
                         error_writer=error_writer)
