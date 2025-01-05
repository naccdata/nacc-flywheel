"""QC checks coordination module."""

import logging
import time
from collections import deque
from typing import Dict, List, Optional

from flywheel import FileEntry
from flywheel.models.job import Job
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_adaptor.subject_adaptor import SubjectAdaptor, VisitInfo
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.utils.metadata import Metadata, create_qc_result_dict
from gear_execution.gear_execution import GearExecutionError
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
    rules_s3_bucket: str
    qc_checks_db_path: str
    primary_key: str
    admin_group: str
    strict_mode: Optional[bool] = True
    legacy_project_label: Optional[str] = None
    date_field: Optional[str] = None


class QCGearInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gear_name: str
    configs: QCGearConfigs


class QCCoordinator():
    """This class coordinates the data quality checks for a given participant.

    - For each module visits are evaluated in the order of visit date.
    - If visit N for module M has not passed error checks any of the
    subsequent visits will not be evaluated for that module.
    - If an existing visit is modified, all of the subsequent visits are re-evaluated.
    """

    def __init__(self, *, subject: SubjectAdaptor, module: str,
                 proxy: FlywheelProxy,
                 gear_context: GearToolkitContext) -> None:
        """Initialize the QC Coordinator.

        Args:
            subject: Flywheel subject to run the QC checks
            module: module label, matched with Flywheel acquisition label
            proxy: Flywheel proxy object
            gear_context: Flywheel gear context
        """
        self._subject = subject
        self._module = module
        self._proxy = proxy
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
            time.sleep(5)  # wait to see if the job gets retried
            job = job.reload()

        log.info('Job %s finished with status: %s', job.id, job.state)

        return job.state

    def is_job_complete(self, job_id: str) -> bool:
        """Checks the status of the given job.

        Args:
            job_id: Flywheel job ID

        Returns:
            bool: True if job successfully complete, else False
        """

        job = self._proxy.get_job_by_id(job_id)
        if not job:
            log.error('Cannot find a job with ID %s', job_id)
            return False

        status = self.poll_job_status(job)
        max_retries = 3  # maximum number of retries in Flywheel
        retries = 1
        while status == 'retried' and retries <= max_retries:
            new_job = self._proxy.find_job(f'previous_job_id="{job_id}"')
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
        visit_file = visit_file.reload()
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
            error: FileError object with failure info
        """

        error_writer = ListErrorWriter(
            container_id=visit_file.id,
            fw_path=self._proxy.get_lookup_path(visit_file))
        error_writer.write(error)

        qc_result = create_qc_result_dict(name='validation',
                                          state='FAIL',
                                          data=error_writer.errors())
        # add qc-coordinator gear info to visit file metadata
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
        visit failed QC validation or error occurred while running the QC gear,
        none of the subsequent visits will be evaluated.

        Args:
            gear_name: QC checks gear name (form_qc_checker)
            gear_configs: QC check gear configs
            visits: set of visits to be evaluated
            date_col: name of the visit date field to sort the visits

        Raises:
            GearExecutionError if errors occur while triggering the QC gear
        """

        try:
            gear = self._proxy.lookup_gear(gear_name)
        except ApiException as error:
            raise GearExecutionError(error) from error

        configs = gear_configs.model_dump()

        date_col_key = f'file.info.forms.json.{date_col}'

        # sort the visits in the ascending order of visit date
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
                visit_file = self._proxy.get_file(file_id)
                destination = self._proxy.get_acquisition(acq_id)
            except ApiException as error:
                raise GearExecutionError(
                    f'Failed to retrieve {filename} - {error}') from error

            job_id = gear.run(config=configs,
                              inputs={"form_data_file": visit_file},
                              destination=destination)
            if job_id:
                log.info('Gear %s queued for file %s - Job ID %s', gear_name,
                         filename, job_id)
            else:
                raise GearExecutionError(
                    f'Failed to trigger gear {gear_name} on file {filename}')

            # If QC gear did not complete, stop evaluating any subsequent visits
            if not self.is_job_complete(job_id):
                self.update_last_failed_visit(file_id=file_id,
                                              filename=filename,
                                              visitdate=visitdate)
                error_obj = system_error(
                    f'Errors occurred while running gear {gear_name} on this file'
                )
                self.update_qc_error_metadata(visit_file, error_obj)
                failed_visit = visit_file.name
                break

            # If QC checks failed, stop evaluating any subsequent visits
            # If it gets to this point, that means QC gear completed,
            # no need to update failed visit info or error metadata, QC gear handles it
            if not self.passed_qc_checks(visit_file, gear_name):
                failed_visit = visit_file.name
                break

        # If there are any visits left, update error metadata in the respective file
        if len(visits_queue) > 0:
            log.info(
                'Visit %s failed, '
                'there are %s subsequent visits for this participant.',
                failed_visit, len(visits_queue))
            log.info('Adding error metadata to respective visit files')
            while len(visits_queue) > 0:
                visit = visits_queue.popleft()
                file_id = visit['file.file_id']
                try:
                    visit_file = self._proxy.get_file(file_id)
                except ApiException as error:
                    log.warning('Failed to retrieve file %s - %s',
                                visit['file.name'], error)
                    log.warning('Error metadata not updated for visit %s',
                                visit['file.name'])
                    continue
                error_obj = previous_visit_failed_error(failed_visit)
                self.update_qc_error_metadata(visit_file, error_obj)
