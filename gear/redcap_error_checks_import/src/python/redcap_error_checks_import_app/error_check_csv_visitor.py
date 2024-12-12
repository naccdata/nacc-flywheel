"""
Module to handle downloading error check CSVs from S3
"""
import logging
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from inputs.csv_reader import CSVVisitor
from outputs.errors import (
    ListErrorWriter,
    empty_field_error,
    missing_field_error,
    unexpected_value_error,
)

log = logging.getLogger(__name__)


class ErrorCheckKey(BaseModel):
    """Pydantic model for the error check key, which expects to be
    of the form
        CSV / MODULE / FORM_VER / PACKET / form_<FORM_NAME>_<PACKET>_error_checks_<type>.csv
    except for ENRL, which is of the form
        CSV / MODULE / FORM_VER / naccid-enrollment-form_error_checks_<type>.csv
    """

    full_path: str
    csv: str
    module: str
    form_ver: str
    filename: str
    form_name: str
    packet: Optional[str] = None

    @classmethod
    def create_from_key(cls, key: str) -> BaseModel:
        """Create ErrorCheckKey from key.

        Args:
            key: The S3 key
        Returns:
            instantiated  ErrorCheckKey
        """
        key_parts = key.split('/')
        assert key_parts[0] == 'CSV', "Expected CSV at top level of S3 key"

        if len(key_parts) == 5:
            module = key_parts[1]
            filename = key_parts[4]
            form_name = filename.split('_')[1]
            if form_name == 'header':
                form_name = f'{module.lower()}_header'

            return ErrorCheckKey(full_path=key,
                                 csv=key_parts[0],
                                 module=module,
                                 form_ver=key_parts[2],
                                 packet=key_parts[3],
                                 filename=filename,
                                 form_name=form_name)
        elif len(key_parts) == 4:
            module = key_parts[1]
            assert module == 'ENROLL'
            filename = key_parts[3]
            form_name = 'enrl'
            return ErrorCheckKey(full_path=key,
                                 csv=key_parts[0],
                                 module=module,
                                 form_ver=key_parts[2],
                                 filename=filename,
                                 form_name=form_name)

        raise ValueError(f"Cannot parse ErrorCheckKey components from {key}; "
                         + "Expected to be of the form "
                         + "CSV / MODULE / FORM_VER / PACKET / filename")


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
                 key: ErrorCheckKey,
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
                # in the case of the enrollment form, packet is
                # set to None and allowed to be missing
                if h == 'packet' and self.__key.packet is None:
                    continue
                self.__error_writer.write(missing_field_error(h))
                valid = False

        return valid

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
        # ignore completely empty lines
        # TODO: should clean up CSVs to not have empty lines so we don't need
        #       to do this
        if all([not x for x in row.values()]):
            return True

        error = None
        for field, value in row.items():
            if (not value and
                field not in self.ALLOWED_EMPTY_FIELDS and
                field in self.REQUIRED_HEADERS):
                error = empty_field_error(field=field,
                                          line=line_num)
                self.__error_writer.write(error)

        if row.get('form_name', None) != self.__key.form_name:
            error = unexpected_value_error(field='form_name',
                                           value=row.get('form_name', None),
                                           expected=self.__key.form_name,
                                           line=line_num)
            self.__error_writer.write(error)

        if not row.get('error_code', None).startswith(self.__key.form_name):
            error = unexpected_value_error(field='error_code',
                                           value=row.get('error_code', None),
                                           expected="Start with form_name",
                                           line=line_num)
            self.__error_writer.write(error)

        if row.get('packet', None) != self.__key.packet:
            error = unexpected_value_error('packet',
                                           row.get('packet', None),
                                           self.__key.packet,
                                           line_num)
            self.__error_writer.write(error)

        if self.__error_writer.errors():
            return False

        # only import items in REQUIRED_HEADERS
        upload_row = {field: row[field] for field in self.REQUIRED_HEADERS
                      if field in row}
        self.__validated_error_checks.append(upload_row)
        return True