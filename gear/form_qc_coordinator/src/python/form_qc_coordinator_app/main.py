"""Defines Form QC Coordinator."""

import logging
from typing import Optional

from flywheel import Client
from flywheel.view_builder import ViewBuilder
from flywheel_adaptor.subject_adaptor import (ParticipantVisits,
                                              SubjectAdaptor, SubjectError,
                                              VisitInfo)
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import ClientWrapper, GearExecutionError
from pandas import DataFrame

from form_qc_coordinator_app.coordinator import QCCoordinator, QCGearInfo

log = logging.getLogger(__name__)


def update_file_metadata(*, gear_context: GearToolkitContext):
    pass


def report_cannot_proceed_error(visits_info: ParticipantVisits,
                                last_failed_visit: VisitInfo):
    pass


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
        filters += f',{date_col_key}>={cutoff_date}'  # assumes all

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
        subject: SubjectAdaptor,
        date_col: str,
        visits_info: ParticipantVisits,
        qc_gear_info: QCGearInfo,
        check_all: bool = False):
    """Invoke QC process for the given participant.

    Args:
        gear_context: Flywheel gear context
        client_wrapper: Flywheel SDK client wrapper
        input_wrapper: Gear input file wrapper
        proxy: Flywheel proxy for the client
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
        try:
            last_failed_visit = subject.get_last_failed_visit(
                visits_info.module)
        except SubjectError as error:
            raise GearExecutionError from error

        if last_failed_visit:
            if (curr_visit.file_id == last_failed_visit.file_id
                    or curr_visit.filename == last_failed_visit.filename):
                cutoff = curr_visit.visitdate
            elif curr_visit.visitdate >= last_failed_visit.visitdate:
                report_cannot_proceed_error(visits_info, last_failed_visit)
                return

    visits_df = get_matching_visits(fw_client=client_wrapper.client,
                                    container_id=subject.id,
                                    subject=subject.label,
                                    module=visits_info.module,
                                    date_col=date_col,
                                    cutoff_date=cutoff)
    if not visits_df:
        return

    qc_cordinator = QCCoordinator(subject=subject,
                                  module=visits_info.module,
                                  fw_client=client_wrapper.client)

    qc_cordinator.run_error_checks(gear_name=qc_gear_info.gear_name,
                                   gear_configs=qc_gear_info.configs,
                                   visits=visits_df)

    update_file_metadata(gear_context=gear_context)
