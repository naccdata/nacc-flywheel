"""QC checks cordination module."""

import logging
import time

from flywheel import Client, FileEntry
from flywheel.rest import ApiException
from flywheel_adaptor.subject_adaptor import SubjectAdaptor
from flywheel_gear_toolkit.utils.metadata import Metadata
from gear_execution.gear_execution import GearExecutionError
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
                 fw_client: Client) -> None:
        """Initialize the QC Cordinator.

        Args:
            subject: Flywheel subject to run the QC checks
            module: module label, matched with Flywheel acquisition label
            fw_client: Flywheel SDK client
        """
        self._subject = subject
        self._module = module
        self._fwclient = fw_client
        self._metadata = Metadata()

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

    def report_errors(self, visit_file: FileEntry):
        """ errors = {}
        name='validation'
        state='FAIL'
        qc_result = self._metadata.create_qc_result_dict(name, state, **errors)
        self._metadata.update_file_metadata(visit_file,
                                            container_type='acquisition',
                                            info=qc_info) """

    def run_error_checks(self, *, gear_name: str, gear_configs: QCGearConfigs,
                         visits: DataFrame):
        """Sequentially trigger the error checks on the provided visits.

        Args:
            gear_name: QC check gear name (form_qc_checker)
            gear_configss: QC check gear configs
            visits: set of visits to be evaluated (sorted by visit date)
        """

        try:
            gear = self._fwclient.lookup(f'gears/{gear_name}')
        except ApiException as error:
            raise GearExecutionError(error) from error

        configs = gear_configs.model_dump()

        run_checks = True
        for index, row in visits.iterrows():
            filename = row['file.name']
            try:
                visit_file = self._fwclient.get_file(row['file.file_id'])
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

                if not self.is_job_complete(job_id):
                    self.report_errors(visit_file)
                    run_checks = False
                    continue

                if not self.passed_qc_checks(visit_file, gear_name):
                    self.report_errors(visit_file)
                    run_checks = False
                    continue
            else:
                self.report_errors(visit_file)
