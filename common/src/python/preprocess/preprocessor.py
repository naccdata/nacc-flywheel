"""Module to implement form data pre-processing checks."""

import logging
from typing import Any, Dict, List, Optional

from datastore.forms_store import FormsStore
from keys.keys import DefaultValues, FieldNames, SysErrorCodes
from outputs.errors import ListErrorWriter, preprocess_errors, preprocessing_error
from pydantic import BaseModel

log = logging.getLogger(__name__)


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
        return ModuleConfigs(initial_packets=configs['initial_packets'],
                             followup_packets=configs['followup_packets'],
                             versions=configs['versions'],
                             date_field=configs['date_field'],
                             legacy_module=configs.get('legacy_module', label),
                             legacy_date=configs.get('legacy_date',
                                                     configs['date_field']))


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

    def __is_accepted_packet(self, *, module: str,
                             module_configs: ModuleConfigs, packet: str,
                             line_num: int) -> bool:
        """_summary_

        Args:
            module (str): _description_
            module_configs (ModuleConfigs): _description_
            packet (str): _description_
            line_num (int): _description_

        Returns:
            bool: _description_
        """
        if (packet not in module_configs.initial_packets
                and packet not in module_configs.followup_packets):
            log.error('%s - %s/%s',
                      preprocess_errors[SysErrorCodes.INVALID_PACKET], module,
                      packet)
            self.__error_writer.write(
                preprocessing_error(field=FieldNames.PACKET,
                                    value=packet,
                                    line=line_num,
                                    error_code=SysErrorCodes.INVALID_PACKET))
            return False

        return True

    def __check_initial_visit(  # noqa: C901
            self, *, subject_lbl: str, input_record: Dict[str, Any],
            module: str, module_configs: ModuleConfigs, line_num: int) -> bool:
        """_summary_

        Args:
            subject_lbl (str): _description_
            input_record: _description_
            module: module
            module_configs (str): _description_
            line_num: the line number of the input record

        Raises:
            PreprocessingException: _description_

        Returns:
            bool: _description_
        """

        packet = input_record[FieldNames.PACKET]

        if self.__forms_store.is_new_subject(subject_lbl):
            if packet in module_configs.initial_packets:
                return True

            if packet in module_configs.followup_packets:
                log.error('%s - %s',
                          preprocess_errors[SysErrorCodes.MISSING_IVP], packet)
                self.__error_writer.write(
                    preprocessing_error(field=FieldNames.PACKET,
                                        value=packet,
                                        line=line_num,
                                        error_code=SysErrorCodes.MISSING_IVP))
                return False

        initial_packets = self.__forms_store.query_ingest_project(
            subject_lbl=subject_lbl,
            module=module,
            search_col=FieldNames.PACKET,
            search_val=module_configs.initial_packets,
            search_op=DefaultValues.FW_SEARCH_OR)

        if not initial_packets:
            if module_configs.legacy_module:
                module = module_configs.legacy_module

            initial_packets = self.__forms_store.query_legacy_project(
                subject_lbl=subject_lbl,
                module=module,
                search_col=FieldNames.PACKET,
                search_val=module_configs.initial_packets,
                search_op=DefaultValues.FW_SEARCH_OR)

        if initial_packets and len(initial_packets) > 1:
            self.__error_writer.write(
                preprocessing_error(field=FieldNames.PACKET,
                                    value=packet,
                                    line=line_num,
                                    error_code=SysErrorCodes.MULTIPLE_IVP))
            return False

        initial_packet = initial_packets[0] if initial_packets else None

        if packet in module_configs.followup_packets and not initial_packet:
            self.__error_writer.write(
                preprocessing_error(field=FieldNames.PACKET,
                                    value=packet,
                                    line=line_num,
                                    error_code=SysErrorCodes.MISSING_IVP))
            return False

        if packet in module_configs.initial_packets and initial_packet:
            ivp_record = self.__forms_store.get_visit_data(
                initial_packet['file.name'],
                initial_packet['file.parents.acquisition'])

            if not ivp_record:
                raise PreprocessingException(
                    f"Error reading previous visit file {initial_packet['file.name']}"
                )

            # If IVP exists and not a modification to the same visit
            if not (ivp_record[module_configs.date_field]
                    == input_record[module_configs.date_field]
                    and ivp_record[FieldNames.VISITNUM]
                    == input_record[FieldNames.VISITNUM]):
                log.error('%s - %s, %s',
                          preprocess_errors[SysErrorCodes.IVP_EXISTS],
                          ivp_record[module_configs.date_field],
                          ivp_record[FieldNames.VISITNUM])
                self.__error_writer.write(
                    preprocessing_error(field=FieldNames.PACKET,
                                        value=packet,
                                        line=line_num,
                                        error_code=SysErrorCodes.IVP_EXISTS))
                return False

        return True

    def __check_visitdate_visitnum(self, *, subject_lbl: str, module: str,
                                   input_record: Dict[str, Any],
                                   line_num: int) -> bool:
        """_summary_

        Args:
            subject_lbl (str): _description_
            module (str): _description_
            input_record (Dict[str, Any]): _description_
            line_num: the line number of the input record

        Returns:
            bool: _description_
        """
        return True

    def preprocess(self, *, input_record: Dict[str, Any], module: str,
                   line_num: int) -> bool:
        """_summary_

        Args:
            input_record (Dict[str, Any]): _description_
            module (str): _description_
            line_num: the line number of the input record

        Returns:
            bool: _description_
        """

        module_configs = self.__module_info.get(module)
        if not module_configs:
            raise PreprocessingException(
                f'No configurations found for module {module}')

        subject_lbl = input_record[self.__primary_key]
        log.info('Running preprocessing checks for subject %s', subject_lbl)

        if not self.__is_accepted_packet(
                module_configs=module_configs,
                module=module,
                packet=input_record[FieldNames.PACKET],
                line_num=line_num):
            return False

        if not self.__check_initial_visit(subject_lbl=subject_lbl,
                                          module_configs=module_configs,
                                          module=module,
                                          input_record=input_record,
                                          line_num=line_num):
            return False

        return self.__check_visitdate_visitnum(subject_lbl=subject_lbl,
                                               module=module,
                                               input_record=input_record,
                                               line_num=line_num)
