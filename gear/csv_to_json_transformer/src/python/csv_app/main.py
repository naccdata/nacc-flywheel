"""Defines ADD DETAIL computation."""

import logging
from typing import Any, Dict, List, TextIO

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import ErrorWriter

log = logging.getLogger(__name__)


class JSONWriter(CSVVisitor):
    """Visitor to write the row as JSON."""

    def __init__(self) -> None:
        super().__init__()

    def add_header(self, header: List[str]) -> bool:
        # TODO: check expected fields in header
        return False

    def visit(self, row: Dict[str, Any], line_num: int) -> bool:
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

    return read_csv(input_file=csv_file, error_writer=error_writer)
