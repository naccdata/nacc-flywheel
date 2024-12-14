"""Module to handle downloading error check CSVs from S3."""
import logging
from typing import Any, Dict, List

from inputs.csv_reader import CSVVisitor
from outputs.errors import (
    ListErrorWriter,
    empty_field_error,
    missing_field_error,
    unexpected_value_error,
)

from .utils import ErrorCheckKey

log = logging.getLogger(__name__)


class ErrorCheckCSVVisitor(CSVVisitor):
    """Visitor for an Error Check CSV file."""

    # error_no, do_in_redcap, in_prev_versions,
    # questions, and any other extra headers ignored
    REQUIRED_HEADERS = ("error_code", "error_type", "form_name", "packet",
                        "var_name", "check_type", "test_name", "short_desc",
                        "full_desc", "test_logic", "comp_forms", "comp_vars")

    ALLOWED_EMPTY_FIELDS = ("comp_forms", "comp_vars")

    def __init__(self, key: ErrorCheckKey,
                 error_writer: ListErrorWriter) -> None:
        """Initializer."""
        self.__key = key
        self.__error_writer = error_writer
        self.__validated_error_checks = []

    @property
    def error_writer(self) -> ListErrorWriter:
        """Get the error writer.

        Returns:
            The ListErrorWriter.
        """
        return self.__error_writer

    @property
    def validated_error_checks(self) -> List[Dict[str, Any]]:
        """Get the validated error checks.

        Returns:
            The running list of error checks.
        """
        return self.__validated_error_checks

    def visit_header(self, header: List[str]) -> bool:
        """Adds the header, and asserts all required fields are present.

        Args:
          header: list of header names
        Returns:
          True if the header has all required fields, False otherwise
        """
        valid = True
        for h in self.REQUIRED_HEADERS:
            if h not in header:
                # in the case of the enrollment form, packet is
                # set to None and allowed to be missing
                if h == 'packet' and self.__key.packet is None:
                    continue
                self.__error_writer.write(missing_field_error(h))
                valid = False

        return valid

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visit the dictionary for a row (per DictReader). Ensure the row
        matches the expected form/packet and fields and data is filled for all
        files.

        Args:
          row: the dictionary for a row from a CSV file
          line_num: The line number of the row
        Returns:
          True if the row was processed without error, False otherwise
        """
        error = None
        for field, value in row.items():
            if (not value and field not in self.ALLOWED_EMPTY_FIELDS
                    and field in self.REQUIRED_HEADERS):
                error = empty_field_error(field=field, line=line_num)
                self.__error_writer.write(error)

        if row.get('form_name') != self.__key.form_name:
            error = unexpected_value_error(field='form_name',
                                           value=row.get('form_name'),
                                           expected=self.__key.form_name,
                                           line=line_num)
            self.__error_writer.write(error)

        if not row.get('error_code').startswith(self.__key.form_name):
            error = unexpected_value_error(field='error_code',
                                           value=row.get('error_code'),
                                           expected="error_code to start " +
                                           "with form_name",
                                           line=line_num)
            self.__error_writer.write(error)

        # check packet is consistent
        if self.__key.packet:
            visit_type = self.__key.get_visit_type()
            if visit_type not in row.get('error_code', ''):
                error = unexpected_value_error(field='error_code',
                                               value=row.get('error_code'),
                                               expected="error_code to have " +
                                               visit_type,
                                               line=line_num)
                self.__error_writer.write(error)

            if row.get('packet') != self.__key.packet:
                error = unexpected_value_error('packet', row.get('packet'),
                                               self.__key.packet, line_num)
                self.__error_writer.write(error)

        if self.__error_writer.errors():
            return False

        # only import items in REQUIRED_HEADERS
        upload_row = {
            field: row[field]
            for field in self.REQUIRED_HEADERS if field in row
        }
        self.__validated_error_checks.append(upload_row)
        return True
