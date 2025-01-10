"""Handles functionality related to watching/polling jobs."""
import logging
import time

from flywheel.models.job import Job
from flywheel.models.job_state import JobState  # type: ignore
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)


class JobPoll:

    @staticmethod
    def poll_job_status(job: Job) -> JobState:
        """Check for the completion status of a gear job.

        Args:
            job: Flywheel Job object

        Returns:
            JobState: job completion status
        """

        while job.state in [JobState.PENDING, JobState.RUNNING]:
            time.sleep(30)
            job = job.reload()

        if job.state == 'failed':
            time.sleep(5)  # wait to see if the job gets retried
            job = job.reload()

        log.info('Job %s finished with status: %s', job.id, job.state)

        return job.state

    @staticmethod
    def poll_job_status_by_id(proxy: FlywheelProxy, job_id: str) -> JobState:
        """Check for the completion status of a gear job.

        Args:
            proxy: the FlywheelProxy
            job_id: Flywheel job ID

        Returns:
            JobState: job completion status
        """
        job = proxy.get_job_by_id(job_id)
        if not job:
            return None

        return JobPoll.poll_job_status(job)

    @staticmethod
    def is_job_complete(proxy: FlywheelProxy, job_id: str) -> bool:
        """Checks the status of the given job.

        Args:
            proxy: the FlywheelProxy
            job_id: Flywheel job ID

        Returns:
            bool: True if job successfully complete, else False
        """

        job = proxy.get_job_by_id(job_id)
        if not job:
            log.error('Cannot find a job with ID %s', job_id)
            return False

        status = JobPoll.poll_job_status(job)
        max_retries = 3  # maximum number of retries in Flywheel
        retries = 1
        while status == 'retried' and retries <= max_retries:
            new_job = proxy.find_job(f'previous_job_id="{job_id}"')
            if not new_job:
                log.error('Cannot find a retried job with previous_job_id=%s',
                          job_id)
                break
            job_id = new_job.id
            retries += 1
            status = JobPoll.poll_job_status(new_job)

        return (status == JobState.COMPLETE)
