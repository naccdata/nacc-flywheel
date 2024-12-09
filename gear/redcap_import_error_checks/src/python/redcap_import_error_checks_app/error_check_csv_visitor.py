"""
Module to handle downloading error check CSVs from S3
"""
import logging
from typing import Any, Dict, List

from inputs.csv_reader import CSVVisitor
from outputs.errors import (
    ListErrorWriter,
    invalid_row_error,
    missing_field_error,
)

log = logging.getLogger(__name__)


class ErrorCheckCSVVisitor(CSVVisitor):
    """Visitor for an Error Check CSV file."""

    # error_no, do_in_redcap, in_prev_versions,
    # questions, and any other extra headers ignored
    REQUIRED_HEADERS = (
        "error_code",
        "error_type",
        "form_name",
        "packet",
        "var_name",
        "check_type",
        "test_name",
        "short_desc",
        "full_desc",
        "test_logic",
        "comp_forms",
        "comp_vars"
    )

    ALLOWED_EMPTY_FIELDS = (
        "comp_forms",
        "comp_vars"
    )

    def __init__(self,
                 form_name: str,
                 packet: str,
                 error_writer: ListErrorWriter) -> None:
        """Initializer."""
        self.__form_name = form_name
        self.__packet = packet
        self.__error_writer = error_writer
        self.__error_checks = []

    @property
    def error_writer(self) -> ListErrorWriter:
        """Get the error writer.

        Returns:
            The ListErrorWriter.
        """
        return self.__error_writer

    @property
    def error_checks(self) -> List[Dict[str, Any]]:
        """Get the error checks.

        Returns:
            The running list of error checks.
        """
        return self.__error_checks

    def visit_header(self, header: List[str]) -> bool:
        """Adds the header, and asserts all required fields
        are present.

        Args:
          header: list of header names
        Returns:
          True if the header has all required fields, False otherwise
        """
        valid = True
        for h in self.REQUIRED_HEADERS:
            if h not in header:
                self.__error_writer.write(missing_field_error(h))
                valid = False

        return valid

    def _write_row_error(self, msg: str, line_num: int) -> bool:
        """Generate the FileError and log/write to error writer.

        Args:
            msg: The error message
            line_num: The line number of the row the failure occured on.
        Returns:
            False
        """
        error = invalid_row_error(msg, line_num)
        log.error(error.message)
        self.__error_writer.write(error)
        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visit the dictionary for a row (per DictReader).
        Ensure the row matches the expected form/packet and fields and
        data is filled for all files.

        Args:
          row: the dictionary for a row from a CSV file
          line_num: The line number of the row
        Returns:
          True if the row was processed without error, False otherwise
        """
        valid = True
        for field, value in row.items():
            if (not value and
                field not in self.ALLOWED_EMPTY_FIELDS and
                field in self.REQUIRED_HEADERS):
                valid = self._write_row_error(f"{field} cannot be empty",
                                              line_num)

        if row['form_name'] != self.__form_name:
            valid = self._write_row_error("form_name does not match expected form name "
                                          + self.__form_name, line_num)
        if row['packet'] != self.__packet:
            valid = self._write_row_error("packet does not match expected packet "
                                      + self.__packet, line_num)

        # only import items in REQUIRED_HEADERS
        if valid:
            upload_row = {field: row[field] for field in self.REQUIRED_HEADERS}
            self.__error_checks.append(upload_row)

        return valid
