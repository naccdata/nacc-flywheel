"""Methods to read and process a CSV file using a row visitor."""

from abc import ABC, abstractmethod
from csv import DictReader, Sniffer
from typing import Any, Dict, List, TextIO

from outputs.errors import ErrorWriter, empty_file_error, missing_header_error


class CSVVisitor(ABC):
    """Abstract class for a visitor for row in a CSV file."""

    @abstractmethod
    def visit(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visit the dictionary for a row (per DictReader).

        Args:
          row: the dictionary for a row from a CSV file
        Returns:
          True if an error was encountered, False otherwise
        """
        return False

    @abstractmethod
    def add_header(self, header: List[str]) -> bool:
        """Add the header.

        Args:
          header: list of header names
        Returns:
          True if the header is missing any required fields, False otherwise
        """
        return False


def read_csv(input_file: TextIO, error_writer: ErrorWriter,
             visitor: CSVVisitor) -> bool:
    """Reads CSV file and applies the visitor to each row.

    Args:
      input_file: the input stream for the CSV file
      error_writer: the ErrorWriter for the input file
      visitor: the visitor
    Returns:
      True if the input file has an error, False otherwise
    """
    sniffer = Sniffer()
    csv_sample = input_file.read(1024)
    if not csv_sample:
        error_writer.write(empty_file_error())
        return True

    if not sniffer.has_header(csv_sample):
        error_writer.write(missing_header_error())
        return True

    input_file.seek(0)
    detected_dialect = sniffer.sniff(csv_sample, delimiters=',')
    reader = DictReader(input_file, dialect=detected_dialect)
    assert reader.fieldnames, "File has header, reader should have fieldnames"

    error_found = visitor.add_header(list(reader.fieldnames))
    if error_found:
        return True

    error_found = False
    for record in reader:
        error_found = visitor.visit(record, line_num=reader.line_num)

    return error_found
