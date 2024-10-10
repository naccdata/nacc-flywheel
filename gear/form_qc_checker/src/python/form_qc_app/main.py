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
from typing import Any, Dict, Literal, Mapping, Optional

from flywheel import Project
from flywheel.rest import ApiException
from flywheel_adaptor.subject_adaptor import (
    SubjectAdaptor,
    SubjectError,
    VisitInfo,
)
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearExecutionError,
    InputFileWrapper,
)
from nacc_form_validator.quality_check import (
    QualityCheck,
    QualityCheckException,
)
from outputs.errors import (
    JSONLocation,
    ListErrorWriter,
    empty_field_error,
    empty_file_error,
    malformed_file_error,
    missing_header_error,
    previous_visit_failed_error,
    system_error,
    unknown_field_error,
)
from redcap.redcap_connection import REDCapReportConnection
from s3.s3_client import S3BucketReader

from form_qc_app.csv_visitor import FormQCCSVVisitor, read_first_data_row
from form_qc_app.error_info import ErrorComposer, ErrorStore, REDCapErrorStore
from form_qc_app.flywheel_datastore import FlywheelDatastore
from form_qc_app.parser import Keys, Parser, ParserException

log = logging.getLogger(__name__)

FailedStatus = Literal['NONE', 'SAME', 'DIFFERENT']


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


def validate_json_input(
        *, input_data: Dict[str, str], pk_field: str, module_field: str,
        date_field: str, project: Project,
        error_writer: ListErrorWriter) -> Optional[SubjectAdaptor]:
    """Validate the JSON input file for a visit. Check whether all required
    fields are present in the input data. Check whether primary key matches
    with the Flywheel subject label in the project.

    Args:
        input_data: visit data to validate
        pk_field: variable name of the primary key field
        module_field: variable name of the module field
        date_field: variable name of the visit date field
        project: Flywheel project container
        error_writer: error writer object to output error metadata

    Returns:
        SubjectAdaptor(optional): returns SubjectAdaptor for this visit or None
    """

    if not input_data:
        error_writer.write(empty_file_error())
        return None

    if pk_field not in input_data or input_data[pk_field] == '':
        error_writer.write(empty_field_error(pk_field))
        return None

    if module_field not in input_data or input_data[module_field] == '':
        error_writer.write(empty_field_error(module_field))
        return None

    if date_field not in input_data or input_data[date_field] == '':
        error_writer.write(empty_field_error(date_field))
        return None

    subject_lbl = input_data[pk_field]
    subject = project.subjects.find_first(f'label={subject_lbl}')
    if not subject:
        message = f'Failed to retrieve subject {subject_lbl} in project {project.label}'
        log.error(message)
        error_writer.write(
            system_error(message, JSONLocation(key_path=pk_field)))
        return None

    return SubjectAdaptor(subject)


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


def has_failed_visits(*, module: str, visitdate: str, file_id: str,
                      filename: str, subject: SubjectAdaptor,
                      error_writer: ListErrorWriter) -> FailedStatus:
    """Check whether the participant has any failed previous visits.

    Args:
        module: module name (Flywheel acqusition label)
        visitdate: visit date for the current visit
        file_id: Flywheel file id
        filename: visit file name
        subject: Flywheel subject adaptor for the participant
        error_writer: error writer object to output error metadata

    Raises:
        GearExecutionError: If any error occurs while checking for previous visits

    Returns:
        FailedStatus: Literal['NONE', 'SAME', 'DIFFERENT']
    """
    try:
        failed_visit = subject.get_last_failed_visit(module)
    except SubjectError as error:
        raise GearExecutionError from error

    if failed_visit:
        same_file = (failed_visit.file_id and failed_visit.file_id
                     == file_id) or (failed_visit.filename == filename)
        # if failed visit date is same as current visit date
        if failed_visit.visitdate == visitdate:
            # check whether it is the same file
            if same_file:
                return 'SAME'
            else:
                raise GearExecutionError(
                    'Two different files exists with same visit date '
                    f'{visitdate} for subject {subject.label} module {module} - '
                    f'{failed_visit.filename} and {filename}')

        # same file but the visit date is different from previously recorded value
        if same_file:
            log.warning(
                'In {subject.label}/{module}, visit date updated from %s to %s',
                failed_visit.visitdate, visitdate)
            return 'SAME'

        # has a failed previous visit
        if failed_visit.visitdate < visitdate:
            error_writer.write(
                previous_visit_failed_error(failed_visit.filename))
            return 'DIFFERENT'

    return 'NONE'


def process_json_file(
    *,
    input_data: Dict[str, str],
    date_field: str,
    input_wrapper: InputFileWrapper,
    subject_adaptor: SubjectAdaptor,
    qual_check: QualityCheck,
    error_store: ErrorStore,
    error_writer: ListErrorWriter,
    codes_map: Optional[Dict[str, Dict]] = None,
) -> bool:
    """Process input JSON file for a participant visit.

    Args:
        input_data: input data record for the visit
        date_field: variable name for visit date field
        input_wrapper: input file wrapper
        subject_adaptor: Flywheel subject adaptor for participant
        qual_check: NACC data quality checker object
        error_store: database connection to retrieve NACC QC chek info
        error_writer: error writer object to output error metadata
        codes_map(optional): schema to map NACC QC checks to validation errors

    Returns:
        bool: True if the file passed validation
    """
    valid = False
    # check whether there are any pending visits for this participant/module
    failed_visit = has_failed_visits(module=input_data[Keys.MODULE],
                                     visitdate=input_data[date_field],
                                     file_id=input_wrapper.file_id,
                                     filename=input_wrapper.filename,
                                     subject=subject_adaptor,
                                     error_writer=error_writer)
    # if there are no failed visits or last failed visit is the current visit
    # run error checks on visit file
    if failed_visit in ['NONE', 'SAME']:
        valid = process_data_record(record=input_data,
                                    qual_check=qual_check,
                                    error_store=error_store,
                                    error_writer=error_writer,
                                    codes_map=codes_map)

        module = input_data[Keys.MODULE]
        if not valid:
            visit_info = VisitInfo(filename=input_wrapper.filename,
                                   file_id=input_wrapper.file_id,
                                   visitdate=input_data[date_field])
            subject_adaptor.set_last_failed_visit(module, visit_info)
        # reset failed visit metadta in Flyhweel
        elif failed_visit == 'SAME':
            subject_adaptor.reset_last_failed_visit(module)

    return valid


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
    *,
    s3_client: S3BucketReader,
    input_data: dict[str, Any],
    filename: str,
    error_writer: ListErrorWriter,
    strict: bool = True
) -> tuple[Dict[str, Mapping], Optional[Dict[str, Dict]]]:
    """Download QC rule definitions and error code mappings from S3 bucket.

    Args:
        s3_client: S3 client
        input_data: input data record
        filename: input file name,
        error_writer: error writer object to output error metadata
        strict (optional): Validation mode, defaults to True.

    Raises:
        GearExecutionError: if error occurred while loading schemas

    Returns:
        rule definition schema, code mapping schema (optional)
    """

    # For CSV input, assumes all the records belong to the same module
    module: Optional[str]
    if Keys.MODULE in input_data and input_data[Keys.MODULE]:
        module = str(input_data[Keys.MODULE]).upper()
    else:
        module = get_module_name_from_file_suffix(filename)

    if not module:
        raise GearExecutionError(
            f'Failed to extract module information from file {filename}')

    s3_prefix = module
    if Keys.PACKET in input_data and input_data[Keys.PACKET]:
        packet = str(input_data[Keys.PACKET]).upper()
        s3_prefix = f'{s3_prefix}/{packet}'

    parser = Parser(s3_client, strict=strict)
    try:
        optional_forms = parser.get_optional_forms_submission_status(
            input_data=input_data,
            module=module,
            packet=packet,
            error_writer=error_writer)
        schema = parser.download_rule_definitions(f'{s3_prefix}/rules/',
                                                  optional_forms)
    except ParserException as error:
        raise GearExecutionError(error) from error

    try:
        codes_map: Optional[Dict[str,
                                 Dict]] = parser.download_rule_definitions(
                                     f'{s3_prefix}/codes/',
                                     optional_forms)  # type: ignore
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
        module = match.group(1).upper()

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

    project = proxy.get_project_by_id(file.parents.project)
    if not project:
        raise GearExecutionError(
            f'Failed to find the project with ID {file.parents.project}')

    legacy_label = gear_context.config.get('legacy_project_label',
                                           Keys.LEGACY_PRJ_LABEL)
    pk_field = (gear_context.config.get('primary_key', Keys.NACCID)).lower()
    date_field = (gear_context.config.get('date_field',
                                          Keys.DATE_COLUMN)).lower()
    error_writer = ListErrorWriter(container_id=file_id,
                                   fw_path=proxy.get_lookup_path(file))
    input_path = Path(input_wrapper.filepath)
    valid = False
    try:
        with open(input_path, mode='r', encoding='utf-8') as file_obj:
            if file_type == 'json':
                try:
                    input_data = json.load(file_obj)
                    subject_adaptor = validate_json_input(
                        input_data=input_data,
                        pk_field=pk_field,
                        module_field=Keys.MODULE,
                        date_field=date_field,
                        project=project,
                        error_writer=error_writer)
                    if not subject_adaptor:
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
                strict = gear_context.config.get("strict_mode", True)

                # Note: Optional forms check is not implemented for CSV files
                # Currently only enrollment module is submitted as a CSV file,
                # and does not require optional forms check.
                # Need to change the way we load rule definitions if we
                # have to support optional forms chek for CSV inputs.
                schema, codes_map = load_rule_definition_schemas(
                    s3_client=s3_client,
                    input_data=input_data,
                    filename=input_wrapper.filename,
                    error_writer=error_writer,
                    strict=strict)

                datastore = FlywheelDatastore(proxy=proxy,
                                              group_id=file.parents.group,
                                              project=project,
                                              legacy_label=legacy_label)

                error_store = REDCapErrorStore(redcap_con=redcap_connection)

                try:
                    qual_check = QualityCheck(pk_field, schema, strict,
                                              datastore)
                except QualityCheckException as error:
                    raise GearExecutionError(
                        f'Failed to initialize QC module: {error}') from error

                if file_type == 'json':
                    valid = process_json_file(
                        input_data=input_data,
                        date_field=date_field,
                        input_wrapper=input_wrapper,
                        subject_adaptor=subject_adaptor,  # type: ignore
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
