"""QC checks cordination module."""

import logging
import time

from flywheel import FileEntry
from flywheel.rest import ApiException
from flywheel_adaptor.subject_adaptor import SubjectAdaptor, VisitInfo
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.utils.metadata import Metadata, create_qc_result_dict
from gear_execution.gear_execution import ClientWrapper, GearExecutionError
from outputs.errors import (
    FileError,
    ListErrorWriter,
    gear_execution_error,
    previous_visit_failed_error,
)
from pandas import DataFrame
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

    def is_job_complete(self, job_id: str) -> bool:
        """Checks the status of given job.

        Args:
            job_id (str): Flywheel job ID

        Returns:
            bool: True if job successfully complete, else False
        """

        job = self._fwclient.jobs.find_first(f'id={job_id}')
        while job.state in ['pending', 'running']:
            time.sleep(60)
            job = job.reload()

        # TODO - how to check for retried jobs

        log.info('Job %s finished with status: %s', job_id, job.state)
        return (job.state == 'complete')

    def passed_qc_checks(self, visit_file: FileEntry, gear_name: str) -> bool:
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
                         visits: DataFrame, date_col: str):
        """Sequentially trigger the QC checks gear on the provided visits. If a
        visit failed QC validation or error occured while running the QC gear,
        none of the subsequent visits will be evaluated.

        Args:
            gear_name: QC checks gear name (form_qc_checker)
            gear_configss: QC check gear configs
            visits: set of visits to be evaluated (sorted by visit date)
            date_col_str: date column name in visits dataframe

        Raises:
            GearExecutionError if errors occurr while triggering the QC gear
        """

        try:
            gear = self._fwclient.lookup(f'gears/{gear_name}')
        except ApiException as error:
            raise GearExecutionError(error) from error

        configs = gear_configs.model_dump()

        run_checks = True
        prev_visit = ''
        date_col_key = f'file.info.forms.json.{date_col}'
        for index, row in visits.iterrows():
            filename = row['file.name']
            file_id = row['file.file_id']
            visitdate = row[date_col_key]
            try:
                visit_file = self._fwclient.get_file(file_id)
                destination = self._fwclient.get_acquisition(
                    row['file.parents.acquisition'])
            except ApiException as error:
                raise GearExecutionError(error) from error

            if run_checks:
                job_id = gear.run(config=configs,
                                  inputs={"form_data_file": visit_file},
                                  destination=destination)
                if job_id:
                    log.info('Gear %s queued for file %s - Job ID %s',
                             gear_name, filename, job_id)
                else:
                    raise GearExecutionError(
                        f'Failed to trigger gear {gear_name} on file {filename}'
                    )

                # QC gear did not complete, disable evaluating any subsequent visits
                if not self.is_job_complete(job_id):
                    self.update_last_failed_visit(file_id=file_id,
                                                  filename=filename,
                                                  visitdate=visitdate)
                    error = gear_execution_error(gear_name)
                    self.update_qc_error_metadata(visit_file, error)
                    run_checks = False
                    prev_visit = visit_file.name
                    continue

                # QC checks failed, disable evaluating any subsequent visits
                # No need to update failed visit info here, QC gear updates it
                if not self.passed_qc_checks(visit_file, gear_name):
                    run_checks = False
                    prev_visit = visit_file.name
                    continue
            else:
                error = previous_visit_failed_error(prev_visit)
                self.update_qc_error_metadata(visit_file, error)
