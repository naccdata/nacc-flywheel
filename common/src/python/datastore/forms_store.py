"""Module to extract/query form data from storage/warehouse."""

import logging
from typing import Dict, List, Literal, Optional

from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from keys.keys import DefaultValues

log = logging.getLogger(__name__)

SearchOperator = Literal['=', '>', '<', '!=', '>=', '<=', '|=']


class FormsStore():
    """Class to extract/query form data from Flywheel for ingest projects."""

    def __init__(self, ingest_project: ProjectAdaptor,
                 legacy_project: Optional[ProjectAdaptor]) -> None:
        self.__ingest_project = ingest_project
        self.__legacy_project = legacy_project

    def query_ingest_project(
            self,
            *,
            subject_lbl: str,
            module: str,
            search_col: str,
            search_val: str | List[str],
            search_op: SearchOperator,
            qc_gear: Optional[str] = None) -> Optional[List[Dict[str, str]]]:
        """_summary_

        Args:
            subject_lbl (str): _description_
            module (str): _description_
            search_col (str): _description_
            search_val (str | List[str]): _description_
            search_op (SearchOperator): _description_
            qc_gear (Optional[str], optional): _description_. Defaults to None.

        Returns:
            Optional[List[Dict[str, str]]]: _description_
        """
        return self.__query_project(project=self.__ingest_project,
                                    subject_lbl=subject_lbl,
                                    module=module,
                                    search_col=search_col,
                                    search_val=search_val,
                                    search_op=search_op,
                                    qc_gear=qc_gear)

    def query_legacy_project(
        self,
        *,
        subject_lbl: str,
        module: str,
        search_col: str,
        search_val: str | List[str],
        search_op: SearchOperator,
        qc_gear: Optional[str] = None,
    ) -> Optional[List[Dict[str, str]]]:
        """_summary_

        Args:
            subject_lbl (str): _description_
            module (str): _description_
            search_col (str): _description_
            search_val (str): _description_
            search_op (SearchOperator): _description_
            qc_gear (Optional[str], optional): _description_. Defaults to None.

        Returns:
            Optional[List[Dict[str, str]]]: _description_
        """
        if not self.__legacy_project:
            log.warning('Legacy project not provided for group %s',
                        self.__ingest_project.group)
            return None

        return self.__query_project(project=self.__legacy_project,
                                    subject_lbl=subject_lbl,
                                    module=module,
                                    search_col=search_col,
                                    search_val=search_val,
                                    search_op=search_op,
                                    qc_gear=qc_gear)

    def __query_project(
            self,
            *,
            project: ProjectAdaptor,
            subject_lbl: str,
            module: str,
            search_col: str,
            search_val: str | List[str],
            search_op: SearchOperator,
            qc_gear: Optional[str] = None) -> Optional[List[Dict[str, str]]]:
        """Retrieve previous visit records for the specified project/subject.

        Args:
            project: Flywheel project container
            subject_lbl: Flywheel subject label
            module: module name
            orderby: variable name that visits are sorted by
            cutoff_val: cutoff value on orderby field
            qc_gear (optional): specify qc_gear name to retrieve records that passed QC

        Returns:
            List[Dict]: List of visits matching with the specified cutoff value,
                        sorted in descending order
        """

        subject = project.find_subject(subject_lbl)
        if not subject:
            log.error('Failed to retrieve subject %s in project %s',
                      subject_lbl, project.label)
            return None

        if isinstance(search_val,
                      List) and search_op != DefaultValues.FW_SEARCH_OR:
            log.error('Unsupported operator "%s" for list input %s', search_op,
                      search_val)
            return None

        if isinstance(search_val,
                      str) and search_op == DefaultValues.FW_SEARCH_OR:
            search_val = [search_val]

        # Dataview to retrieve the previous visits
        title = ('Visits for '
                 f'{project.group}/{project.label}/{subject_lbl}/{module}')

        search_col = f'file.info.forms.json.{search_col}'
        columns = [
            'file.name', 'file.file_id', "file.parents.acquisition",
            "file.parents.session", search_col
        ]
        filters = (
            f'acquisition.label={module},{search_col}{search_op}{search_val}')

        if qc_gear:
            filters += f',file.info.qc.{qc_gear}.validation.state=PASS'

        visits = project.proxy.get_matching_acquisition_files_info(
            container_id=subject.id,
            dv_title=title,
            columns=columns,
            filters=filters)

        if not visits:
            return None

        return sorted(visits, key=lambda d: d[search_col], reverse=True)
