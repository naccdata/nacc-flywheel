"""Defines the APOE Transformer."""
import logging

from typing import Any, Dict, List, TextIO

from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import (
    ListErrorWriter,
    invalid_row_error,
    missing_field_error,
)
from outputs.outputs import write_csv_to_project

log = logging.getLogger(__name__)


def transform_apoe(a1: str, a2: str) -> int:
    """Transforms the APOE genotype encoding from NCRAD to NACC.

    Args:
        a1: APOE loci 1
        a2: APOE loci 2
    Returns:
        int: The APOE NACC encoding
    """
    a1 = a1.strip().upper()
    a2 = a2.strip().upper()

    if a1 == "E3" and a2 == "E3":
        return 1
    elif a1 =="E3" and a2 == "E4":
        return 2
    elif a1 =="E4" and a2 == "E3":
        return 2
    elif a1 =="E3" and a2 == "E2":
        return 3
    elif a1 =="E2" and a2 == "E3":
        return 3
    elif a1 =="E4" and a2 == "E4":
        return 4
    elif a1 =="E4" and a2 == "E2":
        return 5
    elif a1 =="E2" and a2 == "E4":
        return 5
    elif a1 =="E2" and a2 == "E2":
        return 6

    return 9


class APOETransformerCSVVisitor(CSVVisitor):
    """Class for visiting each row in the APOE genotype CSV."""

    EXPECTED_APOE_INPUT_HEADERS = [
        'adcid',
        'ptid',
        'naccid',
        'a1',
        'a2'
    ]

    EXPECTED_APOE_OUTPUT_HEADERS = [
        'adcid',
        'ptid',
        'naccid',
        'apoe'
    ]

    def __init__(self, error_writer: ListErrorWriter):
        """Initializer."""
        self.__error_writer = error_writer
        self.__transformed_data = []

    @property
    def transformed_data(self):
        """The APOE transformed data."""
        return self.__transformed_data

    def visit_header(self, header: List[str]) -> bool:
        """Verifies that the header is valid.

        Args:
            header: The list of headers from the input CSV
        Returns:
            True if the header is valid, else False
        """
        result = True
        for field in self.EXPECTED_APOE_INPUT_HEADERS:
            if field not in header:
                result = False
                error = missing_field_error(field)
                self.__error_writer.write(error)

        return result

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visit the dictionary for the row (per DictReader) and
        perform the APOE transformation.

        Args:
            row: The row data
            line_num: The line number of the row
        Returns:
            True if the row is valid and transformed successfully, else False
        """
        row['apoe'] = transform_apoe(row.pop('a1'), row.pop('a2'))

        # remove any extra headers
        for field in row:
            if field not in self.EXPECTED_APOE_OUTPUT_HEADERS:
                row.pop(field)

        self.__transformed_data.append(row)
        return True


def run(*,
        proxy: FlywheelProxy,
        input_file: TextIO,
        output_filename: str,
        target_project: ProjectAdaptor,
        error_writer: ListErrorWriter,
        delimiter: str = ','):
    """Runs the APOE transformation process.

    Args:
        proxy: the proxy for the Flywheel instance
        input_file: The input CSV TextIO stream to transform on
        output_filename: The output filename to write to
        target_project: The output target project to upload results to
        error_writer: The ListErrorWriter object
        delimiter: The input CSV delimiter
    """
    # read the CSV
    visitor = APOETransformerCSVVisitor(error_writer)
    success = read_csv(input_file=input_file,
                       error_writer=error_writer,
                       visitor=visitor,
                       delimiters=delimiter)

    if not success:
        log.error(
            "The following errors were found while reading the input CSV " +
            "file, will not transform the data.")
        for x in error_writer.errors():
            log.error(x['message'])
        return

    # write transformed results to target project
    log.info(f"Writing transformed APOE data to {project.id}")
    write_csv_to_project(headers=visitor.EXPECTED_APOE_OUTPUT_HEADERS,
                         data=visitor.transformed_data,
                         filename=output_filename,
                         project=target_project)
