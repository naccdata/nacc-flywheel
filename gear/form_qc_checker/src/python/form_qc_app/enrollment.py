"""Module for processing CSV files."""

# Assumes all the records in the CSV file belongs to same module/version/packet
# Note: Optional forms check is not implemented for CSV files
# Currently only enrollment module is submitted as a CSV file,
# and does not require optional forms check.
# Need to change the way we load rule definitions if we
# have to support optional forms chek for CSV inputs.

from csv import Dialect, DictReader, Error, Sniffer
from typing import Any, Dict, List, Mapping, Optional, TextIO

from flywheel import Project
from gear_execution.gear_execution import GearExecutionError, InputFileWrapper
from inputs.csv_reader import CSVVisitor
from keys.keys import FieldNames
from outputs.errors import (
    ListErrorWriter,
    empty_field_error,
    empty_file_error,
    malformed_file_error,
    missing_field_error,
    missing_header_error,
    unknown_field_error,
)

from form_qc_app.definitions import DefinitionsLoader
from form_qc_app.processor import FileProcessor
from form_qc_app.validate import RecordValidator


class EnrollmentFormVisitor(CSVVisitor):
    """Class to validate form data uploaded as a CSV file.

    Requires the input CSV has primary-key column and module column.
    """

    def __init__(self, pk_field: str, error_writer: ListErrorWriter) -> None:
        """
        Args:
          pk_field: primary key field for the project/module
          error_writer: the error output writer
        """
        self.__pk_field = pk_field
        self.__error_writer = error_writer
        self.__header: Optional[List[str]] = None
        self.__reader: Optional[DictReader] = None
        self.__dialect: Optional[Dialect] = None

    @property
    def header(self) -> Optional[List[str]]:
        """Returns header columns list."""
        return self.__header

    @property
    def reader(self) -> Optional[DictReader]:
        """Returns reader."""
        return self.__reader

    @reader.setter
    def reader(self, reader: DictReader):
        """Set the reader.

        Args:
            reader: csv DictReader
        """

        self.__reader = reader

    @property
    def dialect(self) -> Optional[Dialect]:
        """Returns dialect."""
        return self.__dialect

    @dialect.setter
    def dialect(self, dialect: Dialect):
        """Set the dialect.

        Args:
            dialect: csv Dialect
        """

        self.__dialect = dialect

    def visit_header(self, header: List[str]) -> bool:
        """Validates the header fields in file. If the header doesn't have
        `<primary key>`, formver, writes an error.

        Args:
          header: the list of header names

        Returns:
          True if required fields occur in the header, False otherwise
        """

        expected_columns = {self.__pk_field, FieldNames.FORMVER}
        if not set(expected_columns).issubset(set(header)):
            self.__error_writer.write(missing_field_error(expected_columns))
            return False

        self.__header = header

        return True

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Validates a row from the CSV file.

        If the row doesn't have `<primary key>`, formver writes an error.

        Args:
          row: the dictionary from the CSV row (DictReader)
          line_num: the line number of the row

        Returns:
          True if required fields occur in the row, False otherwise
        """
        if not row.get(self.__pk_field):
            self.__error_writer.write(
                empty_field_error(self.__pk_field, line_num))
            return False

        if not row.get(FieldNames.FORMVER):
            self.__error_writer.write(
                empty_field_error(FieldNames.FORMVER, line_num))
            return False

        return True


def read_first_data_row(
        input_file: TextIO, error_writer: ListErrorWriter,
        visitor: EnrollmentFormVisitor) -> Optional[Dict[str, Any]]:
    """Reads CSV file and validates the header and first data row. Sets the CSV
    dialect for the visitor by sniffing a data sample.

    Args:
        input_file: the input stream for the CSV file
        error_writer: the ErrorWriter for the input file
        visitor: the visitor

    Returns:
        Returns first data row as a dict if no errors, else None
    """
    sniffer = Sniffer()
    csv_sample = input_file.read(1024)
    if not csv_sample:
        error_writer.write(empty_file_error())
        return None

    try:
        if not sniffer.has_header(csv_sample):
            error_writer.write(missing_header_error())
            return None

        detected_dialect = sniffer.sniff(csv_sample, delimiters=',')

        input_file.seek(0)
        reader = DictReader(input_file, dialect=detected_dialect)
    except Error as error:
        error_writer.write(malformed_file_error(str(error)))
        return None

    assert reader.fieldnames, "File has header, reader should have fieldnames"

    # check for required fields in the header
    if not visitor.visit_header(list(reader.fieldnames)):
        return None

    first_row = next(reader)
    if not visitor.visit_row(first_row, 1):
        return None

    visitor.dialect = detected_dialect  # type: ignore
    input_file.seek(0)

    return first_row


class CSVFileProcessor(FileProcessor):
    """Class for processing CSV input file.

    Assumes the entire CSV file is for same module/version. (used for
    enrollment form processing).
    """

    def __init__(self, *, pk_field: str, module: str,
                 error_writer: ListErrorWriter) -> None:
        super().__init__(pk_field=pk_field,
                         module=module,
                         error_writer=error_writer)

    def validate_input(self, *, input_wrapper: InputFileWrapper,
                       project: Optional[Project]) -> Optional[Dict[str, Any]]:
        """Validates a CSV input file. Check whether all required fields are
        present in the header and the first data row.

        Args:
            input_wrapper: Wrapper object for gear input file
            project: Flywheel project container

        Returns:
            Dict[str, Any]: None if required info missing, else first row as dict
        """

        enrl_visitor = EnrollmentFormVisitor(pk_field=self._pk_field,
                                             error_writer=self._error_writer)

        with open(input_wrapper.filepath, mode='r',
                  encoding='utf-8') as file_obj:
            input_data = read_first_data_row(input_file=file_obj,
                                             error_writer=self._error_writer,
                                             visitor=enrl_visitor)

            if input_data:
                csv_content = file_obj.readlines()
                self.__csv_reader = DictReader(
                    csv_content, dialect=enrl_visitor.dialect)  # type: ignore

        return input_data

    def load_schema_definitions(
        self, rule_def_loader: DefinitionsLoader, input_data: Dict[str, Any]
    ) -> tuple[Dict[str, Mapping], Optional[Dict[str, Dict]]]:
        """Loads the rule definition JSON schemas for the respective
        module/version. Assumes the entire CSV file is for same module/version.

        Args:
            rule_def_loader: Helper class to load rule definitions
            input_data: Input data record

        Returns:
            rule definition schema, code mapping schema (optional)

        Raises:
            DefinitionException: if error occurred while loading schemas
        """
        return rule_def_loader.load_definition_schemas(input_data=input_data,
                                                       module=self._module)

    def process_input(self, *, validator: RecordValidator) -> bool:
        """Reads the CSV file and apply NACC data quality checks to each record
        Rejects the file if there are any unknown fields in the header.

        Args:
            validator: Helper class for validating a input record

        Returns:
            bool: True if all records passed NACC data quality checks, else False

        Raises:
            GearExecutionError: if errors occured while processing the input file
        """

        if not self.__csv_reader or not self.__csv_reader.fieldnames:
            raise GearExecutionError('Failed to intialize the CSV reader')

        unknown_fields = set(self.__csv_reader.fieldnames).difference(
            set(validator.get_validation_schema().keys()))

        if unknown_fields:
            for unknown_field in unknown_fields:
                self._error_writer.write(unknown_field_error(unknown_field))
            return False

        passed_all = True
        for row in self.__csv_reader:
            if not validator.process_data_record(
                    record=row, line_number=self.__csv_reader.line_num - 1):
                passed_all = False

        return passed_all
