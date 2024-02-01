"""Defines ADD DETAIL computation."""

import logging
from typing import Any, Dict, List, TextIO

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import ErrorWriter

log = logging.getLogger(__name__)


class JSONWriterVisitor(CSVVisitor):
    """Visitor to write the row as JSON."""

    def __init__(self) -> None:
        super().__init__()

    def visit_header(self, header: List[str]) -> bool:
        """Prepares the visitor to process rows using the given
        header columns.
        
        If the header doesn't have `naccid`, `module`, `visitnum` or `formver`
        returns an error.
        
        Args:
          header: the list of header names
        Returns: 
          True if there a column header is missing. False, otherwise
        """
    
        #if all(column_name in header for column_name in ['naccid', 'module', 'visitnum', 'formver']):
        # TODO: check expected fields in header
        # ['naccid', 'module', 'visitnum', 'formver']

        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        # TODO: do any transformations on row
        # TODO: construct file name
        # TODO: write file (needs context?)

        return False


def run(*, proxy: FlywheelProxy, csv_file: TextIO,
        error_writer: ErrorWriter) -> bool:
    """Runs ADD DETAIL process.

    Args:
      proxy: the proxy for the Flywheel instance
      file: flywheel file path
    """

    return read_csv(input_file=csv_file,
                    error_writer=error_writer,
                    visitor=JSONWriterVisitor())
