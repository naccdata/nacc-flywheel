"""Defines CSV to JSON transformations."""

import logging
from typing import Any, Dict, List, Optional, TextIO

from flywheel import Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from gear_execution.gear_execution import GearExecutionError
from inputs.csv_reader import CSVVisitor, read_csv
from keys.keys import FieldNames
from outputs.errors import (
    ListErrorWriter,
    empty_field_error,
    missing_field_error,
    unexpected_value_error,
)

from csv_app.transformer import LBDTransformer, RecordTransformer, UDSTransformer
from csv_app.uploader import JSONUploader

log = logging.getLogger(__name__)

module_transformers = {'UDS': UDSTransformer, 'LBD': LBDTransformer}


class CSVTransformVisitor(CSVVisitor):
    """Class to transform a participant visit CSV record."""

    def __init__(self, *, req_fields: List[str],
                 transformed_records: Dict[str, List[Dict[str, Any]]],
                 error_writer: ListErrorWriter,
                 admin_project: ProjectAdaptor) -> None:
        self.__req_fields = req_fields
        self.__transformed = transformed_records
        self.__error_writer = error_writer
        self.__admin_project = admin_project
        self.__module = None
        self.__transformer: Optional[RecordTransformer] = None

    @property
    def module(self) -> Optional[str]:
        """Returns the detected module for the CSV file."""
        return self.__module

    def visit_header(self, header: List[str]) -> bool:
        """Prepares the visitor to process rows using the given header columns.
        If the header doesn't have required fields writes an error.

        Args:
          header: the list of header names

        Returns:
          True if the header has all required fields, False otherwise
        """

        found_all = True
        for field in self.__req_fields:
            if field not in header:
                found_all = False
                self.__error_writer.write(missing_field_error(field))

        return found_all

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Apply necessary transformations on the given data row. Assumes all
        records in the CSV file belongs to the same module.

        Args:
          row: the dictionary for a row from a CSV file
          line_num: line number in the CSV file

        Returns:
          True if the row was processed without error, False otherwise
        """

        found_all = True
        for field in self.__req_fields:
            if field not in row or not row[field]:
                found_all = False
                self.__error_writer.write(empty_field_error(field, line_num))

        if not found_all:
            return False

        # Set module
        # Assumes all records in the CSV file belongs to the same module.
        if not self.module:
            self.__module = row[FieldNames.MODULE].upper()
        else:  # Check for same module
            row_module = row[FieldNames.MODULE].upper()
            if self.module != row_module:
                self.__error_writer.write(
                    unexpected_value_error(field=FieldNames.MODULE,
                                           value=row_module,
                                           expected=self.module,
                                           line=line_num))
                return False

        # Set transformer for the module
        if not self.__transformer:
            transformer_type = module_transformers.get(
                self.module)  # type: ignore
            if not transformer_type:
                log.info('No module specific transformations defined for %s',
                         self.module)
                transformer_type = RecordTransformer

            self.__transformer = transformer_type(
                self.__admin_project, self.__error_writer,
                'transformation-schemas.json')

        transformed_row = self.__transformer.transform(row, line_num)
        if transformed_row:
            subject_lbl = transformed_row[FieldNames.NACCID]
            visits = self.__transformed.get(subject_lbl)
            if not visits:
                visits = []
                self.__transformed[subject_lbl] = visits
            visits.append(transformed_row)

        return bool(transformed_row)


def notify_upload_errors():
    # TODO: send an email to nacc_dev@uw.edu
    pass


def run(*, input_file: TextIO, proxy: FlywheelProxy, project: Project,
        admin_project: Project, error_writer: ListErrorWriter) -> bool:
    """Reads records from the input file and transforms each into a JSON file.
    Uploads the JSON file to the respective aquisition in Flywheel.

    Args:
        input_file: the input file
        proxy: Flywheel proxy object
        project: Flyhweel project container
        admin_project: Flywheel admin_project container
        error_writer: the writer for error output
    Returns:
        bool: True if transformation/upload successful
    """

    project_adaptor = ProjectAdaptor(project=project, proxy=proxy)
    admin_adaptor = ProjectAdaptor(project=admin_project, proxy=proxy)

    req_fields_list = [
        FieldNames.NACCID, FieldNames.MODULE, FieldNames.VISITNUM,
        FieldNames.DATE_COLUMN
    ]

    transformed_records: Dict[str, List[Dict[str, Any]]] = {}
    visitor = CSVTransformVisitor(req_fields=req_fields_list,
                                  transformed_records=transformed_records,
                                  error_writer=error_writer,
                                  admin_project=admin_adaptor)
    result = read_csv(input_file=input_file,
                      error_writer=error_writer,
                      visitor=visitor)

    if not visitor.module:
        raise GearExecutionError(
            'Module information not found in the input file')

    if not len(transformed_records) > 0:
        return result

    uploader = JSONUploader(project=project_adaptor, module=visitor.module)
    upload_status = uploader.upload_visits(transformed_records)
    if not upload_status:
        notify_upload_errors()

    return result and upload_status
