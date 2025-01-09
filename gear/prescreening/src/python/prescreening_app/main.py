"""Defines Prescreening."""
import logging
from typing import List

from flywheel.models.job_state import JobState  # type: ignore
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import (
    GearExecutionError,
    InputFileWrapper,
)
from gear_execution.gear_trigger import GearInfo

log = logging.getLogger(__name__)


def run(*, proxy: FlywheelProxy, file_input: InputFileWrapper,
        accepted_modules: List[str], tags_to_add: List[str],
        scheduler_gear: GearInfo) -> None:
    """Runs the prescreening process. Checks that the file suffix matches any
    accepted modules; if so, tag the file with the specified tags, and run the
    scheduler gear if it's not already running, else report error.

    Args:
        proxy: the proxy for the Flywheel instance
        file_input: The InputFileWrapper representing the file to
            potentially queue
        accepted_modules: List of accepted modules (case-insensitive)
        tags_to_add: List of tags to add if the file passes prescreening
        scheduler_gear: GearInfo of the scheduler gear to trigger
    """
    module = file_input.basename.split('-')[-1]
    if module.lower() not in accepted_modules:
        raise GearExecutionError(f"Unallowed module suffix: {module}")

    file = proxy.get_file(file_input.file_id)
    if proxy.dry_run:
        log.info("DRY RUN: file passes prescreening, would have added" +
                 f"{tags_to_add}")
    else:
        # add the specified tag
        log.info(f"Adding the following tags to file: {tags_to_add}")
        for tag in tags_to_add:
            file.add_tag(tag)

    # check if the scheduler gear is pending/running
    project_id = file.parents.project
    states = [JobState.RUNNING, JobState.PENDING]
    log.info(f"Checking status of {scheduler_gear.gear_name}")
    if scheduler_gear.check_instance_by_state(proxy=proxy,
                                              states=states,
                                              project_id=project_id):
        log.info("Scheduler gear already running")
        return

    if proxy.dry_run:
        log.info("DRY RUN: Would trigger scheduler gear")
        return

    # otherwise invoke the gear
    scheduler_gear.trigger_gear(
        proxy=proxy, destination=proxy.get_project_by_id(project_id))
