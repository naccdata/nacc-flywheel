"""Defines the Form Scheduler.

1. Pulls the current list of project files with the specified
   queue tags and adds them to processing queues for each module
   sorted by file timestamp
2. If there are no files to process, quit
3. Process the queues in round robin, with the prioritized modules
   analyzed to completion first
    a. Check whether there are any submission pipelines running/pending.
       If there are, exit gear, no need to spin up another instance.
    b. If none found, send an email notification to the user(s) who uploaded
       the original file(s) to let them know their file is in the queue
    c. Pull the next CSV in queue and trigger the submission pipeline
    d. Remove the queue tags from the file
    e. Move to next queue
4. Repeat a-e until all queues are empty
5. Repeat from the beginning
"""
import logging
import re
from typing import List
from pydantic import BaseModel

from flywheel.models.origin_type import OriginType
from flywheel.models.file_entry import FileEntry
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import GearExecutionError
from notifications.email import EmailClient

MODULE_PATTERN = re.compile(f"^.+-([a-zA-Z]+)(\\..+)$")
log = logging.getLogger(__name__)


class QueueAlertTemplateModel(BaseModel):
    """Queue alert template model"""
    project: str
    filename: str
    email_address: str


class FormSchedulerQueue:
    """Class to define a queue for each accepted module,
    with prioritization allowed.
    """

    def __init__(self,
                 proxy: FlywheelProxy,
                 project_id: str,
                 module_order: List[str],
                 queue_tags: List[str],
                 source_email: str = None) -> None:
        """Initializer.
        Args:
            proxy: the proxy for the Flywheel instance
            project_id: The project ID of the project to
                pull and queues file from
            module_order: The modules and the order to process them in
            queue_tags: The queue tags to filter project files for
                to determine which need to be queued
            prioritized_modules: Prioritized modules; will
                go first in the round robin ordering
            source_email: Source email - if provided, will send emails
        """
        self.__proxy = proxy
        self.__project_id = project_id
        self.__module_order = module_order
        self.__index = -1
        self.__queue_tags = set(queue_tags)  # make set for comparison later

        # if sending emails, set up client
        self.__email_client = EmailClient(client=create_ses_client(),
                                          source=source_email) \
            if source_email else None

        self.queue = {k: [] for k in self.__module_order}

    def add_files(self, files: List[File]) -> None:
        """Add the files (filtered by queue tags) to queue.

        Args:
            files: The new batch of files to potentially add
                   to the queue
        """
        # grab each time to refresh
        project = self.__proxy.get_project_by_id(self.__project_id)
        files = [x for x in project.files if self.__queue_tags.issubset(set(x.tags))]

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

            # add to queue and maybe send email
            # TODO: These need to be set up in AWS
            self.queue[module].append(file)
            # if self.__email_client and file.origin.type == OriginType.USER:
            #     owner = file.origin.id
            #     template_data = QueueAlertTemplateModel(
            #         project=project.label,
            #         file=file.name,
            #         email_address=owner)

            #     self.__email_client.send(configuration_set_name='TODO',
            #                              destination=DestinationModel(
            #                                 to_addresses=owner),
            #                              template='TODO',
            #                              template_data=template_data)

        # sort each queue by last modified date
        for subqueue in self.queue.values():
            subqueue.sort(key=lambda file: file.modified)

        log.info(f"Queued files: {self.queue}")

    def next_queue(self) -> Tuple[str, List[FileType]]:
        """Returns the next queue in the round robin.

        Returns:
            Tuple with the module name and its corresponding
            queue to be processed.
        """
        if self.__index + 1 >= len(self.__module_order):
            self.__index = 0
        else:
            self.__index += 1

        module = self.__module_order[self.__index]
        return module, self.queue[module]

    def empty(self) -> bool:
        """Returns whether or not the queue is empty.

        Returns:
            True if the queue is empty, False otherwise.
        """
        return all(not x for x in self.queue.values())

def run(*,
        proxy: FlywheelProxy,
        queue: FormSchedulerQueue,
        submission_pipeline: List[str]):
    """Runs the Form Scheduler process.

    Args:
        proxy: the proxy for the Flywheel instance
        queue: The FormSchedulerQueue which handles the queues
        submission_pipeline: List of gear names representing the submission
            pipeline
    """
    project = self.__proxy.get_project_by_id(self.__project_id)

    while not queue.empty():
        # grab the next subqueue with files in it in the round robin
        module, subqueue = queue.next_queue()
        if not subqueue:
            continue

        # first check if any submission pipelines are running for this project

