"""Methods to read and process a CSV file using a row visitor."""

import abc
from abc import ABC, abstractmethod
from csv import DictReader, Error, Sniffer
from typing import Any, Dict, List, Optional, TextIO, Tuple

from outputs.errors import (
    ErrorWriter,
    empty_file_error,
    malformed_file_error,
    missing_header_error,
)


class CSVVisitor(ABC):
    """Abstract class for a visitor for row in a CSV file."""

    @abstractmethod
    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visit the dictionary for a row (per DictReader).

        Args:
          row: the dictionary for a row from a CSV file
        Returns:
          True if the row was processed without error, False otherwise
        """
        return True

    @abstractmethod
    def visit_header(self, header: List[str]) -> bool:
        """Add the header.

        Args:
          header: list of header names
        Returns:
          True if the header has all required fields, False otherwise
        """
        return True


def read_csv(input_file: TextIO, error_writer: ErrorWriter,
             visitor: CSVVisitor) -> bool:
    """Reads CSV file and applies the visitor to each row.

    Args:
      input_file: the input stream for the CSV file
      error_writer: the ErrorWriter for the input file
      visitor: the visitor
    Returns:
      True if the input file was processed without error, False otherwise
    """
    sniffer = Sniffer()
    csv_sample = input_file.read(1024)
    if not csv_sample:
        error_writer.write(empty_file_error())
        return False

    try:
        has_header = sniffer.has_header(csv_sample)
    except Error as error:
        error_writer.write(malformed_file_error(str(error)))
        return False

    if not has_header:
        error_writer.write(missing_header_error())
        return False

    input_file.seek(0)
    detected_dialect = sniffer.sniff(csv_sample, delimiters=',')
    reader = DictReader(input_file, dialect=detected_dialect)
    assert reader.fieldnames, "File has header, reader should have fieldnames"

    success = visitor.visit_header(list(reader.fieldnames))
    if not success:
        return False

    for record in reader:
        row_success = visitor.visit_row(record, line_num=reader.line_num)
        success = row_success and success

    return success


# pylint: disable=(too-few-public-methods)
class RowValidator(abc.ABC):
    """Abstract class for a RowValidator."""

    @abc.abstractmethod
    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks the row passes the validation criteria of the implementing
        class.

        Args:
            row: the dictionary for the input row
        Returns:
            True if the validator check is true, False otherwise.
        """


# pylint: disable=(too-few-public-methods)
class AggregateRowValidator(RowValidator):
    """Row validator for running more than one validator."""

    def __init__(self,
                 validators: Optional[List[RowValidator]] = None) -> None:
        if validators:
            self.__validators = validators
        else:
            self.__validators = []

    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks the row against each of the validators.

        Args:
            row: the dictionary for the input row
        Returns:
            True if all the validator checks are true, False otherwise
        """
        return all(
            validator.check(row, line_number)
            for validator in self.__validators)


def split_csv_by_key(
        input_filepath: str,
        header_key: str,
        delimiter: str = ',') -> Tuple[Dict[str, object], List[str]]:
    """Splits an input CSV by some header key.

    Args:
        input_filepath: The input CSV to split on
        header_key: The name fo the header column to split by
        delimiter: The CSV's delimiter; defaults to ','

    Returns:
        dict: The split data, keyed by the header key value to (JSON-formatted)
            rows that correspond to it
        list[str]: The list of headers
    """
    split_data = {}
    headers = None
    with open(input_filepath, 'r') as csvfile:
        reader = DictReader(csvfile, delimiter=delimiter)
        headers = reader.fieldnames

        if not headers:
            raise ValueError(
                f"No headers found in input CSV: {input_filepath}")

        if header_key not in headers:
            raise ValueError(
                f"Specified header key '{header_key}' not found " +
                f"in input CSV headers: {input_filepath}")

        for row in reader:
            adcid = int(row[header_key])
            if adcid not in split_data:
                split_data[adcid] = []

            split_data[adcid].append(row)

    return split_data, headers
