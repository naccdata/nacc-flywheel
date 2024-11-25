"""Class for accessing internal or external data sources."""

import json
import logging
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional

from flywheel import Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from keys.keys import DefaultValues, FieldNames, MetadataKeys
from nacc_form_validator.datastore import Datastore
from rxnorm.rxnorm_connection import RxNormConnection, RxcuiStatus

log = logging.getLogger(__name__)


class DatastoreHelper(Datastore):
    """This class extends nacc_form_validator.datastore.

    Defines functions to retrieve previous visits and RxNorm validation.
    """

    def __init__(self, pk_field: str, orderby: str, proxy: FlywheelProxy,
                 group_id: str, project: Project, legacy_label: str):
        """

        Args:
            pk_field: primary key field to uniquely identify a participant
            orderby: field to sort the records by
            proxy: Flywheel proxy object
            group: Flywheel group id
            project: Flywheel project container
            legacy_label: legacy project label
        """

        super().__init__(pk_field, orderby)

        self.__proxy = proxy
        self.__gid = group_id
        self.__project = project
        self.__legacy_label = legacy_label

        self.__legacy_project = self._get_legacy_project()
        self.__legacy_info = self._get_legacy_modules_info()

    def _get_legacy_project(self) -> Optional[Project]:
        """Get the legacy form project for the center group.

        Returns:
            Optional[Project]: legacy Flywheel project or None
        """

        projects = self.__proxy.find_projects(
            group_id=self.__gid, project_label=self.__legacy_label)

        if not projects:
            log.warning('Failed to retrieve legacy project %s in group %s',
                        self.__legacy_label, self.__gid)
            return None

        if len(projects) > 0:
            log.warning(
                'More than one matching project with label %s in group %s',
                self.__legacy_label, self.__gid)
            return None

        return projects[0]

    def _get_legacy_modules_info(self) -> Dict[str, Dict[str, str]]:
        """Get current modules->legacy modules mapping from Flywheel admin
        group metadata project.

        Returns:
            Dict[str, Dict[str, str]]: current modules->legacy modules mapping
        """

        info = {}
        admin_group = self.__proxy.find_group(DefaultValues.NACC_GROUP_ID)
        if admin_group:
            metadata_prj = admin_group.find_project(
                DefaultValues.METADATA_PRJ_LBL)
            if metadata_prj:
                info = metadata_prj.get_info()

        return info.get(MetadataKeys.LEGACY_KEY, {})

    def __get_previous_records(
            self, *, project: Project, subject_lbl: str, module: str,
            orderby: str, cutoff_val: str) -> Optional[List[Dict[str, str]]]:
        """Retrieve previous visit records for the specified project/subject.

        Args:
            project: Flywheel project container
            subject_lbl: Flywheel subject label
            module: module name
            orderby: variable name that visits are sorted by
            cutoff_val: cutoff value on orderby field

        Returns:
            List[Dict]: List of visits matching with the specified cutoff value,
                        sorted in descending order
        """

        subject = project.subjects.find_first(f'label={subject_lbl}')
        if not subject:
            log.error('Failed to retrieve subject %s in project %s',
                      subject_lbl, project.label)
            return None

        # Dataview to retrieve the previous visits
        title = ('Visits for '
                 f'{self.__gid}/{project.label}/{subject_lbl}/{module}')

        orderby_col = f'file.info.forms.json.{orderby}'
        columns = [
            'file.name', 'file.file_id', "file.parents.acquisition",
            "file.parents.session", orderby_col
        ]
        filters = (f'subject.label={subject_lbl}, acquisition.label={module},'
                   f'{orderby_col}<{cutoff_val}')

        visits = self.__proxy.get_matching_aquisition_files_info(
            container_id=subject.id,
            dv_title=title,
            columns=columns,
            filters=filters)

        if not visits:
            return None

        return sorted(visits, key=lambda d: d[orderby_col], reverse=True)

    def _get_visit_data(self, file_name: str,
                        acq_id: str) -> dict[str, str] | None:
        """Read the previous visit file and convert to python dictionary.

        Args:
            file_name: Previous visit file name
            acq_id: Previous visit acquisition id

        Returns:
            dict[str, str] | None: Previous visit data or None
        """
        visit_data = None

        acquisition = self.__proxy.get_acquisition(acq_id)
        file_content = acquisition.read_file(file_name)

        try:
            visit_data = json.loads(file_content)
            log.info('Found previous visit file: %s', file_name)
        except (JSONDecodeError, TypeError, ValueError) as error:
            log.error('Failed to read the previous visit file - %s : %s',
                      file_name, error)

        return visit_data

    def _get_legacy_records(
            self, *, module: str, subject_lbl: str,
            cutoff_value: str) -> Optional[List[Dict[str, str]]]:
        """Retrieve previous visits records from the respective legacy project.

        Args:
            module: module name
            subject_lbl: Flywheel subject label
            cutoff_val: cutoff value on orderby field

        Returns:
            List[Dict]: List of visits matching with the specified cutoff value,
                        sorted in descending order
        """

        if not self.__legacy_project or not self.__legacy_info:
            log.warning('No legacy project/module info found for %s/%s',
                        self.__project.label, module)
            return None

        legacy_module = self.__legacy_info.get(module, {})
        if (not legacy_module or MetadataKeys.LEGACY_LBL not in legacy_module
                or MetadataKeys.LEGACY_ORDERBY not in legacy_module):
            log.warning('Cannot find legacy module info for current module %s',
                        module)
            return None

        return self.__get_previous_records(
            project=self.__legacy_project,
            subject_lbl=subject_lbl,
            module=legacy_module.get(MetadataKeys.LEGACY_LBL),  # type: ignore
            orderby=legacy_module.get(
                MetadataKeys.LEGACY_ORDERBY),  # type: ignore
            cutoff_val=cutoff_value)

    def get_previous_record(
            self, current_record: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Overriding the abstract method, get the previous visit record for
        the specified participant.

        Args:
            current_record: record currently being validated

        Returns:
            dict[str, str]: previous visit record. None if no previous visit
        """

        if self.pk_field not in current_record:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'), self.pk_field)
            return None

        if self.orderby not in current_record:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'), self.orderby)
            return None

        if FieldNames.MODULE not in current_record:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'),
                      FieldNames.MODULE)
            return None

        subject_lbl = current_record[self.pk_field]
        module = current_record[FieldNames.MODULE]
        orderby_value = current_record[self.orderby]

        prev_visits = self.__get_previous_records(project=self.__project,
                                                  subject_lbl=subject_lbl,
                                                  module=module,
                                                  orderby=self.orderby,
                                                  cutoff_val=orderby_value)

        # if no previous visits found in the current project, check the legacy project
        if not prev_visits:
            legacy_visits = self._get_legacy_records(
                module=module,
                subject_lbl=subject_lbl,
                cutoff_value=orderby_value)

            if not legacy_visits:
                log.error('No previous visits found for %s/%s', subject_lbl,
                          module)
                return None

            prev_visits = legacy_visits

        latest_rec_info = prev_visits[0]
        return self._get_visit_data(
            latest_rec_info['file.name'],
            latest_rec_info['file.parents.acquisition'])

    def is_valid_rxcui(self, drugid: int) -> bool:
        """Overriding the abstract method, check whether a given drug ID is
        valid RXCUI.

        Args:
            drugid: provided drug ID (rxcui to validate)

        Returns:
            bool: True if provided drug ID is valid, else False
        """
        return RxNormConnectionError.get_rxcui_status(drugid) == RxcuiStatus.ACTIVE
