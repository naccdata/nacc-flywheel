"""Defines Form QC Coordinator."""

import logging
from typing import Optional

from flywheel import Client
from flywheel.view_builder import ViewBuilder
from flywheel_adaptor.subject_adaptor import (
    ParticipantVisits,
    SubjectAdaptor,
)
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearExecutionError,
    InputFileWrapper,
)
from pandas import DataFrame

from form_qc_coordinator_app.coordinator import QCCoordinator, QCGearInfo

log = logging.getLogger(__name__)


def get_matching_visits(
        *,
        fw_client: Client,
        container_id: str,
        subject: str,
        module: str,
        date_col: str,
        cutoff_date: Optional[str] = None) -> Optional[DataFrame]:
    """Get the list of visits for the specified partipant for the specified
    module.

    Note: This method assumes visit date in file metadata is notmalized to
    YYYY-MM_DD format at a previous stage of the submission pipeline.

    Args:
        fw_client: Flywheel SDK client
        container_id: Flywheel subject container ID
        subject: Flywheel subject label for participant
        module: module label, matched with Flywheel acquisition label
        date_col: name of the visit date column to sort the visits
        cutoff_date (optional): If specified, filter visits on date_col >= cutoff_date

    Returns:
        DataFrame: Dataframe of matching visits sorted in the asc. order of date column
    """

    date_col_key = f'file.info.forms.json.{date_col}'
    columns = [
        date_col_key, 'file.name', 'file.file_id', 'file.parents.acquisition',
        'file.info.forms.json.visitnum'
    ]
    filters = f'acquisition.label={module}'

    if cutoff_date:
        filters += f',{date_col_key}>={cutoff_date}'

    builder = ViewBuilder(label=f'{module} visits for participant {subject}',
                          columns=columns,
                          container='acquisition',
                          filename='*.json',
                          match='all',
                          process_files=False,
                          filter=filters,
                          include_ids=False,
                          include_labels=False)
    builder = builder.missing_data_strategy('drop-row')
    view = builder.build()

    dframe = fw_client.read_view_dataframe(view, container_id)
    if dframe.empty:
        return None

    return dframe.sort_values(date_col_key, ascending=True)


def run(*,
        gear_context: GearToolkitContext,
        client_wrapper: ClientWrapper,
        visits_file_wrapper: InputFileWrapper,
        subject: SubjectAdaptor,
        date_col: str,
        visits_info: ParticipantVisits,
        qc_gear_info: QCGearInfo,
        check_all: bool = False):
    """Invoke QC process for the given participant/module.

    Args:
        gear_context: Flywheel gear context
        client_wrapper: Flywheel SDK client wrapper
        visits_file_wrapper: Input file wrapper
        subject: Flywheel subject to run the QC checks
        date_col: field name to sort the participant visits
        visits_info: Info on new/updated visits for the participant/module
        qc_gear_info: QC gear name and configs
        check_all: re-evaluate all visits for the participant/module

    Raises:
        GearExecutionError if any problem occurrs during the QC process
    """

    if check_all:
        cutoff = None
    else:
        curr_visit = sorted(visits_info.visits, key=lambda d: d.visitdate)[0]
        cutoff = curr_visit.visitdate

    module = visits_info.module
    visits_df = get_matching_visits(fw_client=client_wrapper.client,
                                    container_id=subject.id,
                                    subject=subject.label,
                                    module=module,
                                    date_col=date_col,
                                    cutoff_date=cutoff)
    if not visits_df:
        # This cannot happen, at least one file should exist with matching cutoff date
        raise GearExecutionError(
            'Cannot find matching visits for subject '
            f'{subject.label}/{module} with {date_col}>={cutoff}')

    qc_cordinator = QCCoordinator(subject=subject,
                                  module=module,
                                  client_wrapper=client_wrapper,
                                  gear_context=gear_context)

    qc_cordinator.run_error_checks(gear_name=qc_gear_info.gear_name,
                                   gear_configs=qc_gear_info.configs,
                                   visits=visits_df,
                                   date_col=date_col)
