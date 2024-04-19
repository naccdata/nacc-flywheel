"""Defines Identifier Provisioning."""

import logging
from typing import Any, Dict, List, TextIO

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import ErrorWriter

log = logging.getLogger(__name__)


class ProvisioningVisitor(CSVVisitor):
    """A CSV Visitor class for processing participant enrollment and transfer
    forms."""

    def __init__(self, error_writer: ErrorWriter) -> None:
        self.__error_writer = error_writer

    def visit_header(self, header: List[str]) -> bool:
        """Prepares visitor to work with CSV file with given header.
        
        Args:
          header: the list of header names
        Returns:
          True if something. False otherwise
        """
        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Provisions a NACCID for the NACCID and PTID.
        
        If not a transfer, checks that the center already has a participant
        with PTID.
        And, checks whether demographics match any existing participant.
        In both case is an error.
        
        If is a transfer, BLAH
        
        Args:
          row: the dictionary for the CSV row (DictReader)
          line_num: the line number of the row
        Returns:
          True if a NACCID is provisioned without error, False otherwise
        """
        # if not a transfer, and PTID already has a NACCID => error
        # if demographics match existing participant => error
        # otherwise, create new NACCID
        return False


def run(*, input_file: TextIO, error_writer: ErrorWriter):
    """Runs identifier provisioning process.

    Args:
      input_file: the data input stream
      error_writer: the error output writer
    """
    return read_csv(input_file=input_file,
                    error_writer=error_writer,
                    visitor=ProvisioningVisitor(error_writer=error_writer))
