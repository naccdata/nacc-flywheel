"""Module for applying required transformations to an input visit record."""
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, RootModel, model_validator

from dates.form_dates import DEFAULT_DATE_FORMAT, convert_date
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from gear_execution.gear_execution import GearExecutionError
from keys.keys import DefaultValues, FieldNames, MetadataKeys
from outputs.errors import ListErrorWriter, unexpected_value_error

log = logging.getLogger(__name__)

"""
{
    "UDS": {
        "C2": [],
        "C2T": []
    },
    "LBD": {
        "v3.0": [],
        "v3.1": []
    }
}
"""

ModuleName = Literal['UDS', 'LBD']

class FormTransform(BaseModel):
    drop_lists: Dict[str,List[str]] = {}

    def unique_fields(self, version_name: str) -> Set[str]:
        field_set = set(self.drop_lists.get(version_name, set()))
        if not field_set:
            return field_set

        for key in self.drop_lists.keys():
            if key == version_name:
                continue

            key_fields = self.drop_lists.get(key)
            if not key_fields:
                continue

            field_set = field_set.difference(set(key_fields))

        return field_set
    
    def filter(self, input_record: Dict[str, Any], version_name: str) -> Dict[str,Any]:
        drop_fields = self.unique_fields(version_name)
        if not drop_fields:
            return input_record
        
        return {
            field:value for field, value in input_record.items()
            if field not in drop_fields
        }

class FormTransformations(RootModel):
    root: Dict[ModuleName, FormTransform] = {}

    def __getitem__(self, key: ModuleName) -> FormTransform:
        return self.root[key]
    
    def __setitem__(self, key: ModuleName, value: FormTransform) -> None:
        self.root[key] = value



class RecordTransformer():
    """This class applies the required transformations on a visit record."""

    def __init__(self,
                 error_writer: ListErrorWriter) -> None:
        """Initialize the CSV Transformer.

        Args:
            schema_file(optional): name of the transformation schema file
        """
        self._error_writer = error_writer

    # def _load_transformation_schemas(self):
    #     """Loads any schemas required for transformations from the admin
    #     project.

    #     Override this method to do any module specific schema
    #     processing.
    #     """
    #     if self._schema_file:
    #         try:
    #             self._transformations = json.loads(
    #                 self._admin_project.read_file(self._schema_file))
    #         except (ApiException, json.JSONDecodeError) as error:
    #             raise GearExecutionError(
    #                 'Failed to read the transformation schema file '
    #                 f'{self._schema_file} - {error}') from error

    #         if self._transformations:
    #             log.info('Loaded transformation schemas from %s',
    #                      self._schema_file)

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

    def __init__(self,
                 transform: FormTransform,
                 error_writer: ListErrorWriter) -> None:
        self._transform = transform
        super().__init__(error_writer)

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

        c2_c2t = input_record.get(FieldNames.C2C2T)
        if c2_c2t == DefaultValues.C2TMODE:
            return self._transform.filter(input_record, 'C2')

        return self._transform.filter(input_record, 'C2T')



class LBDTransformer(RecordTransformer):
    """Classs to apply LBD specific transformations."""

    def __init__(self, transform: FormTransform,
                 error_writer: ListErrorWriter) -> None:
        self._transform = transform
        super().__init__(error_writer)

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

        formver = input_record.get(FieldNames.FORMVER)
        if formver == DefaultValues.LBD_SHORT_VER:
            return self._transform.filter(input_record, 'v3.0')

        return self._transform.filter(input_record, 'v3.1')

