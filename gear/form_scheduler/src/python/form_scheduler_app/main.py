"""Defines the Form Scheduler.

1. Pulls the current list of project files with the specified
   queue tags and adds them to processing queues for each module
   sorted by file timestamp
2. Process the queues in a round robin
    a. Check whether there are any submission pipelines running/pending;
       if so, wait for them to finish
    b. Pull the next CSV from the queue and trigger the submission pipeline
    c. Remove the queue tags from the file
    d. Wait for the triggered submission pipeline to finish
    e. Send email to user that the submission pipeline is complete
    f. Move to next queue
3. Repeat 2) until all queues are empty
4. Repeat from the beginning until there are no more files to be queued
"""
import logging
import re
from typing import Dict, List, Optional, Tuple

from flywheel.models.file_output import FileOutput  # type: ignore
from flywheel.models.project_output import ProjectOutput  # type: ignore

#from flywheel.models.origin_type import OriginType
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import GearExecutionError
from gear_execution.gear_trigger import trigger_gear
from jobs.job_poll import JobPoll
from notifications.email import EmailClient, create_ses_client
from pydantic import BaseModel

MODULE_PATTERN = re.compile(r"^.+-([a-zA-Z]+)(\..+)$")
log = logging.getLogger(__name__)


class QueueAlertTemplateModel(BaseModel):
    """Queue alert template model."""
    project: str
    filename: str
    email_address: str


class FormSchedulerQueue:
    """Class to define a queue for each accepted module, with prioritization
    allowed."""

    def __init__(self,
                 proxy: FlywheelProxy,
                 module_order: List[str],
                 queue_tags: List[str],
                 source_email: Optional[str] = None) -> None:
        """Initializer.
        Args:
            proxy: the proxy for the Flywheel instance
            module_order: The modules and the order to process them in
            queue_tags: The queue tags to filter project files for
                to determine which need to be queued
            prioritized_modules: Prioritized modules; will
                go first in the round robin ordering
            source_email: Source email - if provided, will send emails
        """
        self.__proxy = proxy
        self.__module_order = module_order
        self.__index = -1
        self.queue_tags = set(queue_tags)  # make set for comparison later

        # if sending emails, set up client
        self.__email_client = EmailClient(client=create_ses_client(),
                                          source=source_email) \
            if source_email else None

        self.__queue: Dict[str, List[FileOutput]] = {
            k: []
            for k in self.__module_order
        }

    def add_files(self, project: ProjectOutput) -> int:
        """Add the files (filtered by queue tags) to queue.

        Args:
            project: Project to pull queue files from
        Returns:
            The number of files added to the queue
        """
        files = [
            x for x in project.files if self.queue_tags.issubset(set(x.tags))
        ]
        num_files = 0

        # grabs files in the format *-<module>.<ext>
        for file in files:
            match = re.search(MODULE_PATTERN, file.name.lower())
            # skip over files that do not match regex - form-screening gear should
            # check this so these should just be files that were incorrectly tagged
            # by something else
            if not match:
                continue

            module = match.group(1)
            ext = match.group(2)
            if ext not in ['.csv', '.json']:
                continue

            # add to queue
            self.__queue[module].append(file)
            num_files += 1

        # sort each queue by last modified date
        for subqueue in self.__queue.values():
            subqueue.sort(key=lambda file: file.modified)

        return num_files

    def next_queue(self) -> Tuple[str, List[FileOutput]]:
        """Returns the next queue in the round robin.

        Returns:
            Tuple with the module name and its corresponding
            queue to be processed.
        """
        self.__index = (self.__index + 1) % len(self.__module_order)
        module = self.__module_order[self.__index]
        return module, self.__queue[module]

    def empty(self) -> bool:
        """Returns whether or not the queue is empty.

        Returns:
            True if the queue is empty, False otherwise.
        """
        return all(not x for x in self.__queue.values())


def wait_for_submission_pipeline(proxy: FlywheelProxy,
                                 search_str: str) -> None:
    """Wait for a submission pipeline to finish executing bfore continuing.

    Args:
        proxy: the proxy for the Flywheel instance
        search_str: The search string to search for the submission pipeline
    """
    running = True
    while running:
        job = proxy.find_job(search_str)
        if job:
            log.info(f"A submission pipeline with id {job.id} is currently " +
                     "running, waiting for completion")
            # at least for now we don't really care about the state
            # of other submission pipelines, we just wait for it to finish
            JobPoll.poll_job_status(job)
        else:
            running = False


def run(*, proxy: FlywheelProxy, queue: FormSchedulerQueue, project_id: str,
        submission_pipeline: List[str]):
    """Runs the Form Scheduler process.

    Args:
        proxy: the proxy for the Flywheel instance
        queue: The FormSchedulerQueue which handles the queues
        project_id: The project ID
        submission_pipeline: List of gear names representing the submission
            pipeline
    """
    project = proxy.get_project_by_id(project_id)
    if not project:
        raise GearExecutionError(f"Cannot find project with ID {project_id}")

    # search string to use for looking for running submission pipelines
    search_str = JobPoll.generate_search_string(
        project_ids_list=[project_id],
        gears_list=submission_pipeline,
        states_list=['running', 'pending'])
    log.info("Starting Form Scheduler queue")

    # 1. Pull the current list of files
    num_files = -1
    while num_files != 0:
        # force a project reload with each outer loop
        project = project.reload()
        num_files = queue.add_files(project)
        log.info(f"Pulled {num_files} queued files, beginning queue process")

        # 2. Process queue in round robin
        while not queue.empty():
            # grab the next subqueue with files in it in the round robin
            module, subqueue = queue.next_queue()
            if not subqueue:
                continue

            # a. Check if any submission pipelines are already running for
            #    this project if one is found, wait for it to finish before continuing
            #    This should actually not happen as it would mean that this gear
            #    instance is not the owner/trigger of this submission pipeline,
            #    but left in as a safeguard
            wait_for_submission_pipeline(proxy, search_str)

            # b. Pull the next CSV from queue and trigger submission pipeline
            #    Here's where it isn't actually parameterized - we assume that
            #    the first gear is the file-validator regardless, and passes
            #    the corresponding inputs + uses the default configuration
            #    If the first gear changes and has different inputs/needs updated
            #    configurations, this may break as a result and will need to be updated
            #    Maybe we should check that the first gear is always this?
            file = subqueue.pop(0)
            log.info(
                f"Kicking off {submission_pipeline[0]} for {file.name}, " +
                f"module {module}")

            validation_schema = project.get_file(f'{module}-schema.json')
            if not validation_schema:
                raise GearExecutionError(
                    f"Missing validation schema for {module}")

            inputs = {
                "input_file": file,
                "validation_schema": validation_schema
            }
            trigger_gear(proxy=proxy,
                         gear_name=submission_pipeline[0],
                         inputs=inputs)

            # c. clear queue tags
            for tag in queue.queue_tags:
                file.delete_tag(tag)

            # d. wait for the above submission pipeline to finish
            wait_for_submission_pipeline(proxy, search_str)

            # e. TODO: send email to user
            # if file.origin.type == 'user':
            #     send_email(file.origin.id)

        # 3. repeat until all queues empty

    # 4. Repeat from beginning (pulling files) until no more files are found

    log.info("No more queued files to process, exiting Form Scheduler gear")
