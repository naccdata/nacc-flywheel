"""Module for applying required transformations to an input visit record."""

import logging
from typing import Any, Dict

from dates.form_dates import DEFAULT_DATE_FORMAT, convert_date
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from keys.keys import FieldNames
from outputs.errors import ListErrorWriter, unexpected_value_error

log = logging.getLogger(__name__)


class RecordTransformer():
    """This class applies the required transformations on a visit record."""

    def __init__(self, admin_project: ProjectAdaptor,
                 error_writer: ListErrorWriter) -> None:
        """Initialize the CSV Transformer.

        Args:
            admin_project: Flywheel admin project adaptor
            error_writer: the writer for error output
        """
        self.__admin_project = admin_project
        self.__error_writer = error_writer
        self._load_transformation_schemas()

    def _load_transformation_schemas(self):
        """Loads any schemas required for transformation from admin project.

        Nothing required for default transformation. Should override
        this method in module specific transformation class.
        """
        pass

    def transform(self, input_record: Dict[str, Any], line_num: int) -> bool:
        """Applies any common transformations to the input record. Assumes the
        input record has all required keys when it gets to this point.

        Args:
            input_record: record from CSV file
            line_num (int): line number in CSV file

        Returns:
            True if the record was processed without error, False otherwise
        """

        normalized_date = convert_date(
            date_string=input_record[FieldNames.DATE_COLUMN],
            date_format=DEFAULT_DATE_FORMAT)  # type: ignore
        if not normalized_date:
            self.__error_writer.write(
                unexpected_value_error(
                    field=FieldNames.DATE_COLUMN,
                    value=input_record[FieldNames.DATE_COLUMN],
                    expected='',
                    message='Expected a valid date string',
                    line=line_num))
            return False

        input_record[FieldNames.DATE_COLUMN] = normalized_date
        return True


class UDSTransformer(RecordTransformer):
    """Classs to apply UDS specific transformations."""

    def __init__(self, admin_project: ProjectAdaptor,
                 error_writer: ListErrorWriter) -> None:
        super().__init__(admin_project, error_writer)

    def _load_transformation_schemas(self):
        pass

    def transform(self, input_record: Dict[str, Any], line_num: int) -> bool:
        """Applies any UDS specific transformations to the input record.

        Args:
            input_record: record from CSV file
            line_num (int): line number in CSV file

        Returns:
            True if the record was processed without error, False otherwise
        """

        if not super().transform(input_record, line_num):
            return False

        # TODO - apply UDS transformations
        return True


class LBDTransformer(RecordTransformer):
    """Classs to apply LBD specific transformations."""

    def __init__(self, admin_project: ProjectAdaptor,
                 error_writer: ListErrorWriter) -> None:
        super().__init__(admin_project, error_writer)

    def _load_transformation_schemas(self):
        pass

    def transform(self, input_record: Dict[str, Any], line_num: int) -> bool:
        """Applies any LBD specific transformations to the input record.

        Args:
            input_record: record from CSV file
            line_num (int): line number in CSV file

        Returns:
            True if the record was processed without error, False otherwise
        """
        if not super().transform(input_record, line_num):
            return False

        # TODO - apply LBD transformations
        return True
