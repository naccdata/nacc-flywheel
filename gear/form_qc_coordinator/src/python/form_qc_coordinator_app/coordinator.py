"""QC checks cordination module."""

import logging
import time
from collections import deque
from typing import Dict, List

from flywheel import FileEntry
from flywheel.models.job import Job
from flywheel.rest import ApiException
from flywheel_adaptor.subject_adaptor import SubjectAdaptor, VisitInfo
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.utils.metadata import Metadata, create_qc_result_dict
from gear_execution.gear_execution import ClientWrapper, GearExecutionError
from outputs.errors import (
    FileError,
    ListErrorWriter,
    previous_visit_failed_error,
    system_error,
)
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


class QCGearConfigs(BaseModel):
    """Class to represent qc gear configs."""
    model_config = ConfigDict(populate_by_name=True)

    apikey_path_prefix: str
    parameter_path: str
    qc_checks_db_path: str
    primary_key: str
    strict_mode: str
    tag: str


class QCGearInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gear_name: str
    configs: QCGearConfigs


class QCCoordinator():
    """This class cordinates the data quality checks for a given participant.

    - For each module visits are evaluated in the order of visit date.
    - If visit N for module M has not passed error checks any of the
    subsequent visits will not be evaluated for that module.
    - If an existing visit is modified, all of the subsequent visits are re-evaluated.
    """

    def __init__(self, *, subject: SubjectAdaptor, module: str,
                 client_wrapper: ClientWrapper,
                 gear_context: GearToolkitContext) -> None:
        """Initialize the QC Cordinator.

        Args:
            subject: Flywheel subject to run the QC checks
            module: module label, matched with Flywheel acquisition label
            client_wrapper: Flywheel SDK client wrapper
            gear_context: Flywheel gear context
        """
        self._subject = subject
        self._module = module
        self._fwclient = client_wrapper.client
        self._proxy = client_wrapper.get_proxy()
        self._metadata = Metadata(context=gear_context)

    def poll_job_status(self, job: Job) -> str:
        """Check for the completion status of a gear job.

        Args:
            job: Flywheel Job object

        Returns:
            str: job completion status
        """

        while job.state in ['pending', 'running']:
            time.sleep(30)
            job = job.reload()

        if job.state == 'failed':
            time.sleep(10)  # wait to see if the job gets retried
            job = job.reload()

        log.info('Job %s finished with status: %s', job.id, job.state)

        return job.state

    def is_job_complete(self, job_id: str) -> bool:
        """Checks the status of given job.

        Args:
            job_id (str): Flywheel job ID

        Returns:
            bool: True if job successfully complete, else False
        """

        job = self._fwclient.jobs.find_first(f'id={job_id}')
        status = self.poll_job_status(job)
        max_retries = 3  # maximum number of retries in Flywheel
        retries = 1
        while status == 'retired' or retries <= max_retries:
            new_job = self._fwclient.jobs.find_first(
                f'previous_job_id={job_id}')
            if not new_job:
                log.error('Cannot find a retried job with previous_job_id=%s',
                          job_id)
                break
            job_id = new_job.id
            retries += 1
            status = self.poll_job_status(new_job)

        return (status == 'complete')

    def passed_qc_checks(self, visit_file: FileEntry, gear_name: str) -> bool:
        """Check the validation status for the specified visit for the
        specified gear.

        Args:
            visit_file: visit file object
            gear_name: gear name

        Returns:
            bool: True if the visit passed validation
        """
        if not visit_file.info:
            return False

        qc_info = visit_file.info.get('qc', {})
        gear_info = qc_info.get(gear_name, {})
        validation = gear_info.get('validation', {})
        if 'state' not in validation or validation['state'] != 'PASS':
            return False

        return True

    def update_qc_error_metadata(self, visit_file: FileEntry,
                                 error: FileError):
        """Add error metadata to the visits file qc info section
        Note: This method modifies metadata in a file which is not tracked as gear input

        Args:
            visit_file: FileEntry object for the visits file
            previous_visit: name of the failed previous visit file
        """

        error_writer = ListErrorWriter(
            container_id=visit_file.id,
            fw_path=self._proxy.get_lookup_path(visit_file))
        error_writer.write(error)

        qc_result = create_qc_result_dict(name='validation',
                                          state='FAIL',
                                          data=error_writer.errors())
        updated_qc_info = self._metadata.add_gear_info('qc', visit_file,
                                                       **qc_result)
        self._metadata.update_file_metadata(visit_file,
                                            container_type='acquisition',
                                            info=updated_qc_info)

    def update_last_failed_visit(self, file_id: str, filename: str,
                                 visitdate: str):
        """Update last failed visit details in subject metadata.

        Args:
            file_id: Flywheel file id of the failed visit file
            filename: name of the failed visit file
            visitdate: visit date of the failed visit
        """
        visit_info = VisitInfo(file_id=file_id,
                               filename=filename,
                               visitdate=visitdate)
        self._subject.set_last_failed_visit(self._module, visit_info)

    def run_error_checks(self, *, gear_name: str, gear_configs: QCGearConfigs,
                         visits: List[Dict[str, str]], date_col: str) -> None:
        """Sequentially trigger the QC checks gear on the provided visits. If a
        visit failed QC validation or error occured while running the QC gear,
        none of the subsequent visits will be evaluated.

        Args:
            gear_name: QC checks gear name (form_qc_checker)
            gear_configs: QC check gear configs
            visits: set of visits to be evaluated
            date_col: name of the visit date field to sort the visits

        Raises:
            GearExecutionError if errors occurr while triggering the QC gear
        """

        try:
            gear = self._fwclient.lookup(f'gears/{gear_name}')
        except ApiException as error:
            raise GearExecutionError(error) from error

        configs = gear_configs.model_dump()

        date_col_key = f'file.info.forms.json.{date_col}'

        sorted_visits = sorted(visits, key=lambda d: d[date_col_key])
        visits_queue = deque(sorted_visits)

        failed_visit = ''
        while len(visits_queue) > 0:
            visit = visits_queue.popleft()
            filename = visit['file.name']
            file_id = visit['file.file_id']
            acq_id = visit['file.parents.acquisition']
            visitdate = visit[date_col_key]

            try:
                visit_file = self._fwclient.get_file(file_id)
                destination = self._fwclient.get_acquisition(acq_id)
            except ApiException as error:
                raise GearExecutionError(
                    f'Failed to retrieve {filename} - {error}')

            job_id = gear.run(config=configs,
                              inputs={"form_data_file": visit_file},
                              destination=destination)
            if job_id:
                log.info('Gear %s queued for file %s - Job ID %s', gear_name,
                         filename, job_id)
            else:
                raise GearExecutionError(
                    f'Failed to trigger gear {gear_name} on file {filename}')

            # QC gear did not complete, stop evaluating any subsequent visits
            if not self.is_job_complete(job_id):
                self.update_last_failed_visit(file_id=file_id,
                                              filename=filename,
                                              visitdate=visitdate)
                error = system_error(
                    f'Errors occurred while running gear {gear_name} on this file'
                )
                self.update_qc_error_metadata(visit_file, error)
                failed_visit = visit_file.name
                break

            # QC checks failed, stop evaluating any subsequent visits
            # No need to update failed visit info here, QC gear updates it
            if not self.passed_qc_checks(visit_file, gear_name):
                failed_visit = visit_file.name
                break

        # If there are any visits left, update error metadata in the visit file
        if len(visits_queue) > 0:
            log.info(
                'Visit %s failed, '
                'there are %s subsequent visits for this participant.',
                failed_visit, len(visits_queue))
            log.info('Updating error metadata for remaining visits')
            while len(visits_queue) > 0:
                visit = visits_queue.popleft()
                file_id = visit['file.file_id']
                try:
                    visit_file = self._fwclient.get_file(file_id)
                except ApiException as error:
                    log.warning('Failed to retrieve file %s - %s',
                                visit['file.name'], error)
                    log.warning('Error metadata not updated for visit %s',
                                visit['file.name'])
                    continue
                error = previous_visit_failed_error(failed_visit)
                self.update_qc_error_metadata(visit_file, error)
