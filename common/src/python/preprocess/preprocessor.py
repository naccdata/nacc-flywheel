"""Module to implement form data pre-processing checks."""

from typing import Any, Dict, List, Optional

from datastore.forms_store import FormsStore
from keys.keys import DefaultValues, FieldNames
from outputs.errors import ListErrorWriter
from pydantic import BaseModel


class PreprocessingException(Exception):
    pass


class ModuleConfigs(BaseModel):
    initial_packets: List[str]
    followup_packets: List[str]
    versions: List[str]
    date_field: str
    legacy_module: Optional[str] = None
    legacy_date: Optional[str] = None

    @classmethod
    def create(cls, label: str, configs: Dict[str, Any]) -> 'ModuleConfigs':
        """Create from given configs."""
        return ModuleConfigs(
            initial_packets=configs['initial_packets'],
            followup_packets=configs['followup_packets'],
            versions=configs['versions'],
            date_field=configs['date_field'],
            legacy_module=configs.get('legacy_module', label),
            legacy_date=configs.get('legacy_date', configs['date_field']))


class FormProjectConfigs(BaseModel):
    primary_key: str
    legacy_project_label: Optional[str] = DefaultValues.LEGACY_PRJ_LABEL
    module_configs: Dict[str, ModuleConfigs]


class FormPreprocessor():
    """Class to carryout preprocessing checks for a participant visit
    record."""

    def __init__(self, primary_key: str, forms_store: FormsStore,
                 module_info: Dict[str, ModuleConfigs],
                 error_writer: ListErrorWriter) -> None:
        self.__primary_key = primary_key
        self.__forms_store = forms_store
        self.__module_info = module_info
        self.__error_writer = error_writer

    def __check_initial_visit(self, *, subject_lbl: str, module: str,
                              packet: str) -> bool:
        """_summary_

        Args:
            subject_lbl (str): _description_
            module (str): _description_
            packet (str): _description_

        Raises:
            PreprocessingException: _description_

        Returns:
            bool: _description_
        """
        module_config = self.__module_info.get(module)
        if not module_config:
            raise PreprocessingException(
                f'No configurations found for module {module}')

        if (packet not in module_config.initial_packets
                or packet not in module_config.followup_packets):
            return False

        initial_packet = self.__forms_store.query_ingest_project(
            subject_lbl=subject_lbl,
            module=module,
            search_col=FieldNames.PACKET,
            search_val=module_config.initial_packets,
            search_op=DefaultValues.FW_SEARCH_OR)

        if not initial_packet:
            if module_config.legacy_module:
                module = module_config.legacy_module

            initial_packet = self.__forms_store.query_legacy_project(
                subject_lbl=subject_lbl,
                module=module,
                search_col=FieldNames.PACKET,
                search_val=module_config.initial_packets,
                search_op=DefaultValues.FW_SEARCH_OR)

        if initial_packet and len(initial_packet) > 1:
            raise PreprocessingException(
                f'More than one IVP packet found for {subject_lbl}/{module}')

        if packet in module_config.initial_packets and initial_packet:
            return False

        return not (packet in module_config.followup_packets
                    and not initial_packet)

    def __check_visitdate_visitnum(self, *, subject_lbl: str, module: str,
                                   input_record: Dict[str, Any]) -> bool:
        """_summary_

        Args:
            subject_lbl (str): _description_
            module (str): _description_
            input_record (Dict[str, Any]): _description_

        Returns:
            bool: _description_
        """
        return True

    def preprocess(self, *, input_record: Dict[str, Any], module: str) -> bool:
        """_summary_

        Args:
            input_record (Dict[str, Any]): _description_
            module (str): _description_

        Returns:
            bool: _description_
        """

        subject_lbl = input_record[self.__primary_key]
        passed = self.__check_initial_visit(
            subject_lbl=subject_lbl,
            module=module,
            packet=input_record[FieldNames.PACKET])

        passed = passed and self.__check_visitdate_visitnum(
            subject_lbl=subject_lbl, module=module, input_record=input_record)

        return passed
