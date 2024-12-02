"""Module for applying required transformations to an input visit record."""
import json
import logging
from typing import Any, Dict, Optional, Set

from dates.form_dates import DEFAULT_DATE_FORMAT, convert_date
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from gear_execution.gear_execution import GearExecutionError
from keys.keys import DefaultValues, FieldNames, MetadataKeys
from outputs.errors import ListErrorWriter, unexpected_value_error

log = logging.getLogger(__name__)


class RecordTransformer():
    """This class applies the required transformations on a visit record."""

    def __init__(self,
                 admin_project: ProjectAdaptor,
                 error_writer: ListErrorWriter,
                 schema_file: Optional[str] = None) -> None:
        """Initialize the CSV Transformer.

        Args:
            admin_project: Flywheel admin project adaptor
            error_writer: the writer for error output
            schema_file(optional): name of the transformation schema file
        """
        self._admin_project = admin_project
        self._error_writer = error_writer
        self._schema_file = schema_file
        self._transformations = None
        self._load_transformation_schemas()

    def _load_transformation_schemas(self):
        """Loads any schemas required for transformations from the admin
        project.

        Override this method to do any module specific schema
        processing.
        """
        if self._schema_file:
            try:
                self._transformations = json.loads(
                    self._admin_project.read_file(self._schema_file))
            except (ApiException, json.JSONDecodeError) as error:
                raise GearExecutionError(
                    'Failed to read the transformation schema file '
                    f'{self._schema_file} - {error}') from error

            if self._transformations:
                log.info('Loaded transformation schemas from %s',
                         self._schema_file)

    def _drop_fields(self, input_record: Dict[str, Any],
                     drop_fields: Set[str]) -> Dict[str, Any]:
        """Drop the specified list of fields from the input record.

        Args:
            input_record: input record from CSV file
            drop_fields: list of fields to drop

        Returns:
            Dict[str, Any]: modified record
        """

        if not drop_fields:
            return input_record

        return {
            key: input_record[key]
            for key in input_record if key not in drop_fields
        }

    def transform(self, input_record: Dict[str, Any],
                  line_num: int) -> Optional[Dict[str, Any]]:
        """Applies any common transformations to the input record. Assumes the
        input record has all required keys when it gets to this point.

        Args:
            input_record: input record from CSV file
            line_num (int): line number in CSV file

        Returns:
            Transformed record or None if there's processing errors
        """

        normalized_date = convert_date(
            date_string=input_record[FieldNames.DATE_COLUMN],
            date_format=DEFAULT_DATE_FORMAT)  # type: ignore
        if not normalized_date:
            self._error_writer.write(
                unexpected_value_error(
                    field=FieldNames.DATE_COLUMN,
                    value=input_record[FieldNames.DATE_COLUMN],
                    expected='',
                    message='Expected a valid date string',
                    line=line_num))
            return None

        input_record[FieldNames.DATE_COLUMN] = normalized_date
        return input_record


class UDSTransformer(RecordTransformer):
    """Classs to apply UDS specific transformations."""

    def __init__(self, admin_project: ProjectAdaptor,
                 error_writer: ListErrorWriter, schema_file: str) -> None:
        self.__c2only = set()
        self.__c2tonly = set()
        super().__init__(admin_project, error_writer, schema_file)

    def _load_transformation_schemas(self):
        """Loads UDS transformations schema from the admin project.

        Derive C2/C2T only fields from the specified schema
        """
        super()._load_transformation_schemas()
        if self._transformations:
            c2 = self._transformations.get(MetadataKeys.C2, [])
            c2t = self._transformations.get(MetadataKeys.C2T, [])
            self.__c2only = set(c2).difference(set(c2t))
            self.__c2tonly = set(c2t).difference(set(c2))

    def transform(self, input_record: Dict[str, Any],
                  line_num: int) -> Optional[Dict[str, Any]]:
        """Applies any UDS specific transformations to the input record.

        Args:
            input_record: record from CSV file
            line_num (int): line number in CSV file

        Returns:
            Transformed record or None if there's processing errors
        """

        if not super().transform(input_record, line_num):
            return None

        if self._transformations:
            c2_c2t = input_record.get(FieldNames.C2C2T)
            if c2_c2t == DefaultValues.C2TMODE:
                return self._drop_fields(input_record, self.__c2only)
            else:
                return self._drop_fields(input_record, self.__c2tonly)

        return input_record


class LBDTransformer(RecordTransformer):
    """Classs to apply LBD specific transformations."""

    def __init__(self, admin_project: ProjectAdaptor,
                 error_writer: ListErrorWriter, schema_file: str) -> None:
        self.__long_only = set()
        self.__short_only = set()
        super().__init__(admin_project, error_writer, schema_file)

    def _load_transformation_schemas(self):
        """Loads LBD transformations schema from the admin project.

        Derive v3.0/v3.1 only fields from the specified schema
        """
        super()._load_transformation_schemas()
        if self._transformations:
            lbd_long = self._transformations.get(MetadataKeys.LBD_LONG, [])
            lbd_short = self._transformations.get(MetadataKeys.LBD_SHORT, [])
            self.__long_only = set(lbd_long).difference(set(lbd_short))
            self.__short_only = set(lbd_short).difference(set(lbd_long))

    def transform(self, input_record: Dict[str, Any],
                  line_num: int) -> Optional[Dict[str, Any]]:
        """Applies any LBD specific transformations to the input record.

        Args:
            input_record: record from CSV file
            line_num (int): line number in CSV file

        Returns:
            True if the record was processed without error, False otherwise
        """
        if not super().transform(input_record, line_num):
            return None

        if self._transformations:
            formver = input_record.get(FieldNames.FORMVER)
            if formver == DefaultValues.LBD_SHORT_VER:
                return self._drop_fields(input_record, self.__long_only)
            else:
                return self._drop_fields(input_record, self.__short_only)

        return input_record
