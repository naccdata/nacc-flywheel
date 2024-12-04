"""Defines the APOE Transformer."""
import logging
from typing import Any, Dict, List, TextIO, Tuple

from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import (
    ListErrorWriter,
    missing_field_error,
)
from outputs.outputs import write_csv_to_project

log = logging.getLogger(__name__)

# NCRAD (a1, a2) to NACC encoding
APOE_ENCODINGS = {
    ("E3", "E3"): 1,
    ("E3", "E4"): 2,
    ("E4", "E3"): 2,
    ("E3", "E2"): 3,
    ("E2", "E3"): 3,
    ("E4", "E4"): 4,
    ("E4", "E2"): 5,
    ("E2", "E4"): 5,
    ("E2", "E2"): 6
}


class APOETransformerCSVVisitor(CSVVisitor):
    """Class for visiting each row in the APOE genotype CSV."""

    EXPECTED_APOE_INPUT_HEADERS: Tuple[str] = ('adcid', 'ptid', 'naccid', 'a1',
                                               'a2')

    EXPECTED_APOE_OUTPUT_HEADERS: Tuple[str] = ('adcid', 'ptid', 'naccid',
                                                'apoe')

    def __init__(self, error_writer: ListErrorWriter):
        """Initializer."""
        self.__error_writer = error_writer
        self.__transformed_data = []

    @property
    def transformed_data(self):
        """The APOE transformed data."""
        return self.__transformed_data

    @property
    def error_writer(self):
        """The error writer."""
        return self.__error_writer

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
        """Visit the dictionary for the row (per DictReader) and perform the
        APOE transformation.

        Args:
            row: The row data
            line_num: The line number of the row
        Returns:
            True if the row is valid and transformed successfully, else False
        """
        a1, a2 = row.pop('a1'), row.pop('a2')
        pair = (a1.strip().upper(), a2.strip().upper())
        row['apoe'] = APOE_ENCODINGS.get(pair, 9)

        # remove any extra headers
        extra_fields = set(row.keys()) - set(self.EXPECTED_APOE_OUTPUT_HEADERS)
        for field in extra_fields:
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
                       visitor=visitor)
    #delimiters=delimiter)  # TODO - pass after merging

    if not success:
        log.error(
            "The following errors were found while reading the input CSV " +
            "file, will not transform the data.")
        for x in error_writer.errors():
            log.error(x['message'])
        return

    # write transformed results to target project
    log.info(f"Writing transformed APOE data to {target_project.id}")
    write_csv_to_project(headers=visitor.EXPECTED_APOE_OUTPUT_HEADERS,
                         data=visitor.transformed_data,
                         filename=output_filename,
                         project=target_project)
