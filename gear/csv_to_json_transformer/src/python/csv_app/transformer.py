"""Module for applying required transformations to an input visit record."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar

from dates.form_dates import DEFAULT_DATE_FORMAT, convert_date
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from keys.keys import FieldNames
from outputs.errors import ListErrorWriter, unexpected_value_error

log = logging.getLogger(__name__)


class ModuleTransformer(ABC):

    def __init__(self, admin_project: ProjectAdaptor) -> None:
        self._admin_project = admin_project

    @abstractmethod
    def transform(self, input_record: Dict[str, Any]) -> bool:
        """Apply module specific transformations."""


MT = TypeVar('MT', bound=ModuleTransformer)


class UDSTransformer(ModuleTransformer):
    """Classs to apply UDS specific transformations."""

    def transform(self, input_record: Dict[str, Any]) -> bool:
        return True


class LBDTransformer(ModuleTransformer):
    """Classs to apply LBD specific transformations."""

    def transform(self, input_record: Dict[str, Any]) -> bool:
        return True


module_transformers = {'UDS': UDSTransformer, 'LBD': LBDTransformer}


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

    def transform_record(self, input_record: Dict[str, Any],
                         line_num: int) -> bool:
        """Applies any module specific transformations to the input record.
        Assumes the input record has all required keys when it gets to this
        point.

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
        return self.tranform_module(input_record)

    def tranform_module(self, input_record: Dict[str, Any]) -> bool:
        module = input_record[FieldNames.MODULE].upper()
        transformer_type = module_transformers.get(module)
        if not transformer_type:
            log.info('No module specific transformations defined for %s',
                     module)
            return True

        transformer = transformer_type(self.__admin_project)
        return transformer.transform(input_record)
