"""Defines ADD DETAIL computation."""

import logging
from typing import Any, Dict, List, TextIO

from flywheel import Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from inputs.csv_reader import CSVVisitor, read_csv
from keys.keys import FieldNames
from outputs.errors import ListErrorWriter, empty_field_error, missing_field_error

from csv_app.transformer import RecordTransformer
from csv_app.uploader import JSONUploader

log = logging.getLogger(__name__)


class JSONWriterVisitor(CSVVisitor):
    """Visitor to write the row as JSON."""

    def __init__(self, *, req_fields: List[str],
                 transformer: RecordTransformer,
                 transformed_records: Dict[str, List[Dict[str, Any]]],
                 error_writer: ListErrorWriter) -> None:
        self.__transformer = transformer
        self.__req_fields = req_fields
        self.__transformed = transformed_records
        self.__error_writer = error_writer

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
        """Apply necessary transformations on the given data row.

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

        success = self.__transformer.transform_record(row, line_num)
        if success:
            subject_lbl = row[FieldNames.NACCID]
            visits = self.__transformed.get(subject_lbl)
            if not visits:
                visits = []
                self.__transformed[subject_lbl] = visits
            visits.append(row)

        return success


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
    admin_adaptor = ProjectAdaptor(project=project, proxy=proxy)

    req_fields_list = [
        FieldNames.NACCID, FieldNames.MODULE, FieldNames.VISITNUM,
        FieldNames.DATE_COLUMN
    ]

    transformer = RecordTransformer(admin_project=admin_adaptor,
                                    error_writer=error_writer)

    transformed_records: Dict[str, List[Dict[str, Any]]] = {}
    result = read_csv(input_file=input_file,
                      error_writer=error_writer,
                      visitor=JSONWriterVisitor(
                          req_fields=req_fields_list,
                          transformer=transformer,
                          transformed_records=transformed_records,
                          error_writer=error_writer))

    if not len(transformed_records) > 0:
        return result

    uploader = JSONUploader(project=project_adaptor)
    upload_status = uploader.upload_visits(transformed_records)
    if not upload_status:
        notify_upload_errors()

    return result and upload_status
