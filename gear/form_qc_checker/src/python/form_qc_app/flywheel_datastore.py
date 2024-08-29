"""Handles the connection with a Flywheel project."""

import json
import logging
from json.decoder import JSONDecodeError
from typing import Dict, Optional

from flywheel import Client, Project
from flywheel.rest import ApiException
from flywheel.view_builder import ViewBuilder
from pandas import DataFrame
from validator.datastore import Datastore

from form_qc_app.parser import Keys

log = logging.getLogger(__name__)


class FlywheelDatastore(Datastore):
    """This class defines functions to retrieve previous visits from
    Flywheel."""

    def __init__(self, client: Client, group: str, project: str):
        """

        Args:
            client (Client): the Flywheel SDK client
            group (str): Flywheel group id
            project (str): Flywheel project id
        """

        self.__client = client
        self.__gid = group
        self.__pid = project

        # Retrieve Project container from Flywheel
        try:
            self.__project = self.__client.get_project(self.__pid)
        except ApiException as error:
            log.error('Failed to retrieve Flywheel container: %s', error)

        # TODO - get legacy project label from params
        self.__legacy_project = self.get_legacy_project('retrospective-form')

    def get_legacy_project(self, project_lbl: str) -> Optional[Project]:
        """Get the legacy form project for the given Flywheel ingest project.

        Args:
            project_lbl: Flywheel project label

        Returns:
            Optional[Project]: legacy Flywheel project or None
        """
        try:
            return self.__client.lookup(f'{self.__gid}/{project_lbl}')
        except ApiException as error:
            log.error('Failed to retrieve legacy project in group %s: %s',
                      self.__gid, error)
            return None

    def get_previous_records(self, *, project: Project, subject_lbl: str,
                             module: str, orderby: str,
                             cutoff_val: str) -> DataFrame:
        """Retrieve previous visit records for the specified subject.

        Args:
            project: Flywheel project to pull the records
            subject_lbl: Flywheel subject label
            module: module name
            orderby: variable name that visits are sorted by
            cutoff_val: cutoff value on orderby field

        Returns:
            Optional[DataFrame]: Dataframe of previous visits
        """

        # Dataview to retrieve the previous visits
        orderby_col = f'file.info.forms.json.{orderby}'
        columns = [
            'file.name', 'file.file_id', "file.parents.acquisition",
            "file.parents.session", orderby_col
        ]
        builder = ViewBuilder(
            label=('Visits for '
                   f'{self.__gid}/{project.label}/{subject_lbl}/{module}'),
            columns=columns,
            container='acquisition',
            filename='*.json',
            match='all',
            process_files=False,
            filter=(f'subject.label={subject_lbl},'
                    f'acquisition.label={module},{orderby_col}<{cutoff_val}'),
            include_ids=False,
            include_labels=False)
        view = builder.build()

        dframe = self.__client.read_view_dataframe(view, project.id)
        if not dframe.empty:
            dframe = dframe.sort_values(orderby_col, ascending=False)

        return dframe

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

        if Keys.MODULE not in current_ins:
            log.error(('Variable %s not set in current visit data, '
                       'cannot retrieve the previous visits'), Keys.MODULE)
            return None

        subject_lbl = current_ins[pk_field]
        module = current_ins[Keys.MODULE]
        orderby_value = current_ins[orderby]

        dframe = self.get_previous_records(project=self.__project,
                                           subject_lbl=subject_lbl,
                                           module=module,
                                           orderby=orderby,
                                           cutoff_val=orderby_value)

        # TODO get legacy module and orderby column
        if dframe.empty and self.__legacy_project:
            self.get_previous_records(project=self.__legacy_project,
                                      subject_lbl=subject_lbl,
                                      module='UDSv3',
                                      orderby='vstdate_a1',
                                      cutoff_val=orderby_value)

        if dframe.empty:
            log.error('No previous visits found for %s/%s', subject_lbl,
                      module)
            return None

        latest_rec_info = dframe.head(1).to_dict('records')[0]
        return self.get_visit_data(latest_rec_info['file.name'],
                                   latest_rec_info['file.parents.acquisition'])

    def get_visit_data(self, file_name: str,
                       acq_id: str) -> dict[str, str] | None:
        """Read the previous visit file and convert to python dictionary.

        Args:
            file_name (str): Previous visit file name
            acq_id (str): Previous visit acquisition id

        Returns:
            dict[str, str] | None: Previous visit data or None
        """
        visit_data = None

        acquisition = self.__client.get_acquisition(acq_id)
        file_content = acquisition.read_file(file_name)

        try:
            visit_data = json.loads(file_content)
            log.info('Found previous visit file: %s', file_name)
        except (JSONDecodeError, TypeError, ValueError) as error:
            log.error('Failed to read the previous visit file - %s : %s',
                      file_name, error)

        return visit_data
