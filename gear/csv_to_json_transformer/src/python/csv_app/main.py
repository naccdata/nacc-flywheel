"""Defines ADD DETAIL computation."""

import logging
from typing import Any, Dict, List, Optional, TextIO, Tuple

from flywheel import Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from inputs.csv_reader import CSVVisitor, read_csv
from keys.keys import FieldNames
from outputs.errors import ListErrorWriter, empty_field_error, missing_field_error

from csv_app.transformer import JSONTransformer

log = logging.getLogger(__name__)


class JSONWriterVisitor(CSVVisitor):
    """Visitor to write the row as JSON."""

    def __init__(self, *, req_fields: List[str], transformer: JSONTransformer,
                 error_writer: ListErrorWriter) -> None:
        self.__transformer = transformer
        self.__req_fields = req_fields
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

        return self.__transformer.transform_record(row, line_num)


def run(*, input_file: TextIO, proxy: FlywheelProxy, project: Project,
        error_writer: ListErrorWriter,
        required_fields: Optional[str]) -> Tuple[bool, bool]:
    """Reads records from the input file and transforms each into a JSON file.
    Uploads the JSON file to the respective aquisition in Flywheel.

    Args:
        input_file: the input file
        proxy: Flywheel proxy object
        project: Flyhweel project container
        error_writer: the writer for error output
        required_fields(optional): list of required fields
    Returns:
        Tuple[bool, bool]: Transformation successful, System errors occurred
    """

    project_adaptor = ProjectAdaptor(project=project, proxy=proxy)

    if required_fields:
        req_fields_list = required_fields.split(",")
    else:
        req_fields_list = [
            FieldNames.NACCID, FieldNames.MODULE, FieldNames.VISITNUM,
            FieldNames.DATE_COLUMN
        ]

    transformer = JSONTransformer(project=project_adaptor,
                                  error_writer=error_writer)

    result = read_csv(input_file=input_file,
                      error_writer=error_writer,
                      visitor=JSONWriterVisitor(req_fields=req_fields_list,
                                                transformer=transformer,
                                                error_writer=error_writer))

    # Create and upload pending visits files for each participant
    # These files will trigger the form-qc-coordinator gear
    result = result and transformer.upload_pending_visits_file()

    return result, transformer.system_errors
