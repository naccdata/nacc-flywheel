"""Defines Form Screening."""
import logging
from typing import List, Optional

from flywheel.models.job import Job
from flywheel.models.job_state import JobState  # type: ignore
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import (
    GearExecutionError,
    InputFileWrapper,
)
from gear_execution.gear_trigger import GearInfo, trigger_gear

log = logging.getLogger(__name__)


def check_instance_by_state(
        gear_name: str,
        proxy: FlywheelProxy,
        states: List[str],
        project_id: Optional[str] = None) -> Optional[Job]:
    """Check if an instance of the gear matches the given state.

    Args:
        gear_name: the gear name
        proxy: the proxy for the Flywheel instance
        states: List of states to check for
        project_id: The project ID to check for gear instances;
            if not specified, will match any gear instance in any project

    Returns:
        The Flywheel Job if found, None otherwise
    """
    search_str = f'gear_info.name=|{[gear_name]},state=|{states}'
    if project_id:
        search_str = f'parents.project={project_id},{search_str}'

    log.info(
        f"Checking job state with the following search str: {search_str}")
    return proxy.find_job(search_str)


def run(*, proxy: FlywheelProxy, file_input: InputFileWrapper,
        accepted_modules: List[str], tags_to_add: List[str],
        scheduler_gear: GearInfo) -> None:
    """Runs the form_screening process. Checks that the file suffix matches any
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
    if check_instance_by_state(gear_name=scheduler_gear.gear_name,
                               proxy=proxy,
                               states=states,
                               project_id=project_id):
        log.info("Scheduler gear already running")
        return

    if proxy.dry_run:
        log.info("DRY RUN: Would trigger scheduler gear")
        return

    # otherwise invoke the gear
    trigger_gear(proxy=proxy,
                 gear_name=scheduler_gear.gear_name,
                 config=scheduler_gear.model_dump(),
                 destination=proxy.get_project_by_id(project_id))
