"""Defines ADD DETAIL computation."""

import logging
from typing import Any, Dict, List, TextIO

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import ErrorWriter, missing_header_error

log = logging.getLogger(__name__)


class JSONWriterVisitor(CSVVisitor):
    """Visitor to write the row as JSON."""

    def __init__(self, error_writer: ErrorWriter) -> None:
        self.__error_writer = error_writer

    def visit_header(self, header: List[str]) -> bool:
        """Prepares the visitor to process rows using the given header columns.

        If the header doesn't have `naccid`, `module`, `visitnum` or `formver`
        returns an error.

        Args:
          header: the list of header names
        Returns:
          True if there a column header is missing. False, otherwise
        """
        if 'module' not in header and 'formver' not in header:
            self.__error_writer.write(missing_header_error())
            return False

        # TODO: get transformations for module+formver

        # TODO: perhaps these should be determined by template file
        if 'visitnum' not in header and 'visitdate' not in header:
            self.__error_writer.write(missing_header_error())
            return False

        if 'naccid' not in header:
            self.__error_writer.write(missing_header_error())
            return False

        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        # TODO: do any transformations on row
        # TODO: construct file name
        # TODO: write file (needs context?)

        return True


def run(*, input_file: TextIO, proxy: FlywheelProxy, error_writer: ErrorWriter) -> bool:
    """Reads records from the input file and transforms each into a JSON
    object.

    Args:
      input_file: the input file
      proxy: Flywheel proxy object
      error_writer: the writer for error output
    """

    return read_csv(input_file=input_file,
                    error_writer=error_writer,
                    visitor=JSONWriterVisitor(error_writer=error_writer))
