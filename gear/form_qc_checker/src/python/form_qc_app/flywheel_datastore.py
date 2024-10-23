"""Handles the connection with a Flywheel project."""

import json
import logging
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional

from centers.nacc_group import NACCGroup
from flywheel import Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from keys.keys import FieldNames
from nacc_form_validator.datastore import Datastore

log = logging.getLogger(__name__)


class FlywheelDatastore(Datastore):
    """This class defines functions to retrieve previous visits from
    Flywheel."""

    def __init__(self, proxy: FlywheelProxy, group_id: str, project: Project,
                 legacy_label: str):
        """

        Args:
            proxy: Flywheel proxy object
            group: Flywheel group id
            project: Flywheel project container
            legacy_label: legacy project label
        """

        self.__proxy = proxy
        self.__gid = group_id
        self.__project = project
        self.__legacy_label = legacy_label

        self.__legacy_project = self.get_legacy_project()
        self.__legacy_info = self.get_legacy_modules_info()

    def get_legacy_project(self) -> Optional[Project]:
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

    def get_previous_records(
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

    def get_previous_instance(
            self, orderby: str, pk_field: str,
            current_ins: dict[str, str]) -> Optional[Dict[str, str]]:
        """Overriding the abstract method, get the previous visit record for
        the specified subject.

        Args:
            orderby (str): Variable name that visits are sorted by
            pk_field (str): Primary key field of the project
            current_ins (dict[str, str]): Visit currently being validated

        Returns:
            dict[str, str]: Previous visit record. None if no previous visit
        """

        if pk_field not in current_ins:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'), pk_field)
            return None

        if orderby not in current_ins:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'), orderby)
            return None

        if FieldNames.MODULE not in current_ins:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'),
                      FieldNames.MODULE)
            return None

        subject_lbl = current_ins[pk_field]
        module = current_ins[FieldNames.MODULE]
        orderby_value = current_ins[orderby]

        prev_visits = self.get_previous_records(project=self.__project,
                                                subject_lbl=subject_lbl,
                                                module=module,
                                                orderby=orderby,
                                                cutoff_val=orderby_value)

        if not prev_visits and self.__legacy_project and self.__legacy_info:
            legacy_module = self.__legacy_info.get(module, {})
            if (not legacy_module or 'legacy_label' not in legacy_module
                    or 'legacy_orderby' not in legacy_module):
                log.warning(
                    'Cannot find legacy module info for current module %s',
                    module)
                return None

            prev_visits = self.get_previous_records(
                project=self.__legacy_project,
                subject_lbl=subject_lbl,
                module=legacy_module.get('legacy_label'),  # type: ignore
                orderby=legacy_module.get('legacy_orderby'),  # type: ignore
                cutoff_val=orderby_value)

        if not prev_visits:
            log.error('No previous visits found for %s/%s', subject_lbl,
                      module)
            return None

        latest_rec_info = prev_visits[0]
        return self.get_visit_data(latest_rec_info['file.name'],
                                   latest_rec_info['file.parents.acquisition'])

    def get_visit_data(self, file_name: str,
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

    def get_legacy_modules_info(self) -> Dict[str, Dict[str, str]]:
        """Get current modules->legacy modules mapping from Flywheel admin
        group metadata project.

        Returns:
            Dict[str, Dict[str, str]]: current modules->legacy modules mapping
        """
        admin_group = NACCGroup.create(proxy=self.__proxy)
        metadata_prj = admin_group.get_metadata()
        info = metadata_prj.get_info()
        return info.get('legacy', {})
