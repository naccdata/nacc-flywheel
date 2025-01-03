"""Defines the NACCID lookup computation."""

import logging
from typing import Any, Dict, List, Optional, TextIO

from enrollment.enrollment_transfer import CenterValidator
from gear_execution.gear_execution import GearExecutionError
from identifiers.identifiers_repository import (
    IdentifierRepository,
    IdentifierRepositoryError,
)
from identifiers.model import IdentifierObject
from inputs.csv_reader import CSVVisitor, read_csv
from keys.keys import FieldNames
from outputs.errors import (
    ErrorWriter,
    identifier_error,
    missing_field_error,
)
from outputs.outputs import CSVWriter

log = logging.getLogger(__name__)


class NACCIDLookupVisitor(CSVVisitor):
    """A CSV Visitor class for adding a NACCID to the rows of a CSV input.

    Requires the input CSV has a PTID column, and all rows represent
    data from same ADRC (have the same ADCID).
    """

    def __init__(self, *, adcid: int, identifiers: Dict[str, IdentifierObject],
                 output_file: TextIO, module_name: str,
                 error_writer: ErrorWriter) -> None:
        """
        Args:
            adcid: ADCID for the center
            identifiers: the map from PTID to Identifier object
            output_file: the data output stream
            module_name: the module name for the form
            error_writer: the error output writer
        """
        self.__identifiers = identifiers
        self.__output_file = output_file
        self.__error_writer = error_writer
        self.__module_name = module_name
        self.__header: Optional[List[str]] = None
        self.__writer: Optional[CSVWriter] = None
        self.__validator = CenterValidator(center_id=adcid,
                                           error_writer=error_writer)

    def __get_writer(self):
        """Returns the writer for the CSV output.

        Manages whether writer has been initialized. Requires that
        header has been set.
        """
        if not self.__writer:
            assert self.__header, "Header must be set before visiting any rows"
            self.__writer = CSVWriter(stream=self.__output_file,
                                      fieldnames=self.__header)

        return self.__writer

    def visit_header(self, header: List[str]) -> bool:
        """Prepares the visitor to write a CSV file with the given header.

        If the header doesn't have `ptid` or `adcid`, returns an error.

        Args:
          header: the list of header names
        Returns:
          True if `ptid` occurs in the header, False otherwise
        """
        expected_columns = {FieldNames.PTID, FieldNames.ADCID}
        if not set(expected_columns).issubset(set(header)):
            self.__error_writer.write(missing_field_error(expected_columns))
            return False

        self.__header = header
        self.__header.append(FieldNames.NACCID)
        self.__header.append(FieldNames.MODULE)

        return True

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Finds the NACCID for the row from the PTID, and outputs a row to a
        CSV file with the NACCID inserted.

        If the NACCID isn't found for a row, an error is written to the error
        file.

        Args:
          row: the dictionary from the CSV row (DictReader)
          line_num: the line number of the row
        Returns:
          True if there is a NACCID for the PTID, False otherwise
        """

        if not self.__validator.check(row=row, line_number=line_num):
            return False

        identifier = self.__identifiers.get(row[FieldNames.PTID])
        if not identifier:
            self.__error_writer.write(
                identifier_error(line=line_num, value=row[FieldNames.PTID]))
            return False

        row[FieldNames.NACCID] = identifier.naccid
        row[FieldNames.MODULE] = self.__module_name

        writer = self.__get_writer()
        writer.write(row)

        return True


class CenterLookupVisitor(CSVVisitor):
    """Defines a CSV visitor class for adding ADCID, PTID to the rows of CSV
    input.

    Requires the input CSV has a NACCID column
    """

    def __init__(self, *, identifiers_repo: IdentifierRepository,
                 output_file: TextIO, error_writer: ErrorWriter) -> None:
        self.__identifiers_repo = identifiers_repo
        self.__output_file = output_file
        self.__error_writer = error_writer
        self.__writer: Optional[CSVWriter] = None
        self.__header: Optional[List[str]] = None

    def __get_writer(self):
        """Returns the writer for the CSV output.

        Manages whether writer has been initialized. Requires that
        header has been set.
        """
        if not self.__writer:
            assert self.__header, "Header must be set before visiting any rows"
            self.__writer = CSVWriter(stream=self.__output_file,
                                      fieldnames=self.__header)

        return self.__writer

    def visit_header(self, header: List[str]) -> bool:
        """Prepares the visitor to write a CSV file with the given header.

        If the header doesn't have `naccid`, returns an error.

        Args:
          header: the list of header names
        Returns:
          True if `naccid` occurs in the header, False otherwise
        """
        expected_columns = {FieldNames.NACCID}
        if not set(expected_columns).issubset(set(header)):
            self.__error_writer.write(missing_field_error(expected_columns))
            return False

        self.__header = header
        self.__header.append(FieldNames.ADCID)

        return True

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Finds the ADCID, PTID for the row from the NACCID, and outputs a row
        to a CSV file with the ADCID and PTID inserted.

        If the ADCID, PTID are not found for a row, an error is written to the
        error file.

        Args:
          row: the dictionary from the CSV row (DictReader)
          line_num: the line number of the row
        Returns
          True if there is a ADCID, PTID for the NACCID. False otherwise.
        Raises:
          GearExecutionError if the identifiers repository raises an error
        """

        try:
            identifier = self.__identifiers_repo.get(
                naccid=row[FieldNames.NACCID])
        except IdentifierRepositoryError as error:
            raise GearExecutionError(error) from error

        if not identifier:
            self.__error_writer.write(
                identifier_error(line=line_num, value=row[FieldNames.NACCID]))
            return False

        row[FieldNames.ADCID] = identifier.adcid
        row[FieldNames.PTID] = identifier.ptid

        writer = self.__get_writer()
        writer.write(row)

        return True


def run(*, input_file: TextIO, lookup_visitor: CSVVisitor,
        error_writer: ErrorWriter) -> bool:
    """Reads participant records from the input CSV file, finds the NACCID for
    each row from the ADCID and PTID, and outputs a CSV file with the NACCID
    inserted.

    If the NACCID isn't found for a row, an error is written to the error file.

    Note: this function assumes that the ADCID for each row is the same, and
    that the ADCID corresponds to the ID for the group where the file is
    located.
    The identifiers map should at least include Identifiers objects with this
    ADCID.

    Args:
      input_file: the data input stream
      lookup_visitor: the CSVVisitor for identifier lookup
      error_writer: the error output writer
    Returns:
      True if there were IDs with no corresponding NACCID
    """

    return read_csv(input_file=input_file,
                    error_writer=error_writer,
                    visitor=lookup_visitor)
