"""Defines the NACCID lookup computation."""

import logging
from typing import Any, Dict, List, Optional, TextIO

from enrollment.enrollment_transfer import CenterValidator
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from gear_execution.gear_execution import GearExecutionError
from identifiers.model import IdentifierObject
from inputs.csv_reader import CSVVisitor, read_csv
from keys.keys import FieldNames
from outputs.errors import (
    ListErrorWriter,
    get_error_log_name,
    identifier_error,
    missing_field_error,
    update_error_log_and_qc_metadata,
)
from outputs.outputs import CSVWriter

log = logging.getLogger(__name__)


class IdentifierVisitor(CSVVisitor):
    """A CSV Visitor class for adding a NACCID to the rows of a CSV input.

    Requires the input CSV has a PTID column, and all rows represent
    data from same ADRC (have the same ADCID).
    """

    def __init__(self,
                 *,
                 adcid: int,
                 identifiers: Dict[str, IdentifierObject],
                 output_file: TextIO,
                 module_name: str,
                 error_writer: ListErrorWriter,
                 date_field: str,
                 gear_name: str,
                 project: Optional[ProjectAdaptor] = None) -> None:
        """
        Args:
            adcid: ADCID for the center
            identifiers: the map from PTID to Identifier object
            output_file: the data output stream
            module_name: the module name for the form
            error_writer: the error output writer
            date_field: visit date field for the module
            gear_name: gear name
            project: Flywheel project adaptor
        """
        self.__identifiers = identifiers
        self.__output_file = output_file
        self.__error_writer = error_writer
        self.__module_name = module_name
        self.__date_field = date_field
        self.__project = project
        self.__gear_name = gear_name
        self.__header: Optional[List[str]] = None
        self.__writer: Optional[CSVWriter] = None
        self.__validator = CenterValidator(center_id=adcid,
                                           error_writer=error_writer)
        self.__req_fields = {
            FieldNames.PTID, FieldNames.ADCID, self.__date_field
        }
        self.__error_log_template = {
            "ptid": FieldNames.PTID,
            "visitdate": self.__date_field
        }

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

        If the header doesn't have required fields returns an error.

        Args:
          header: the list of header names

        Returns:
          True if required fields occur in the header, False otherwise
        """

        if not self.__req_fields.issubset(set(header)):
            self.__error_writer.write(missing_field_error(self.__req_fields))
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

        self.__error_writer.clear()

        if not self.__validator.check(row=row, line_number=line_num):
            self.__update_visit_error_log(input_record=row, qc_passed=False)
            return False

        identifier = self.__identifiers.get(row[FieldNames.PTID])
        if not identifier:
            self.__error_writer.write(
                identifier_error(line=line_num, value=row[FieldNames.PTID]))
            self.__update_visit_error_log(input_record=row, qc_passed=False)
            return False

        row[FieldNames.NACCID] = identifier.naccid
        row[FieldNames.MODULE] = self.__module_name

        writer = self.__get_writer()
        writer.write(row)
        self.__update_visit_error_log(input_record=row, qc_passed=True)

        return True

    def __update_visit_error_log(self, *, input_record: Dict[str, Any],
                                 qc_passed: bool):
        """Update error log file for the visit and store error metadata in
        file.info.qc.

        Args:
            input_record: input visit record
            qc_passed: whether the visit passed QC checks

        Returns:
            bool: True if error log updated successfully, else False
        """

        if not self.__project:
            log.warning(
                'Parent project not specified to upload visit error log')
            return

        error_log_name = get_error_log_name(
            module=self.__module_name,
            input_data=input_record,
            naming_template=self.__error_log_template)

        # This is first gear in pipeline validating individual rows
        # therefore, clear metadata from previous runs `reset_metadata=True`
        if not error_log_name or not update_error_log_and_qc_metadata(
                error_log_name=error_log_name,
                destination_prj=self.__project,
                gear_name=self.__gear_name,
                state='PASS' if qc_passed else 'FAIL',
                errors=self.__error_writer.errors(),
                reset_metadata=True):
            raise GearExecutionError(
                'Failed to update error log for visit '
                f'{input_record[FieldNames.PTID]}, {input_record[self.__date_field]}'
            )


def run(*,
        input_file: TextIO,
        identifiers: Dict[str, IdentifierObject],
        module_name: str,
        adcid: int,
        output_file: TextIO,
        error_writer: ListErrorWriter,
        date_field: str,
        gear_name: str,
        project: Optional[ProjectAdaptor] = None) -> bool:
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
      identifiers: the map from PTID to Identifier object
      module_name: the module name for the form
      adcid: ADCID for the center
      output_file: the data output stream
      error_writer: the error output writer
      date_field: visit date field for the module
      gear_name: gear name
      project: Flywheel project adaptor

    Returns:
      True if there were IDs with no corresponding NACCID
    """

    return read_csv(input_file=input_file,
                    error_writer=error_writer,
                    visitor=IdentifierVisitor(adcid=adcid,
                                              identifiers=identifiers,
                                              output_file=output_file,
                                              module_name=module_name,
                                              error_writer=error_writer,
                                              date_field=date_field,
                                              project=project,
                                              gear_name=gear_name),
                    clear_errors=True)
