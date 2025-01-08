"""Defines Pre-Screening."""
import logging
from typing import List

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import (
    GearExecutionError,
    InputFileWrapper,
)

log = logging.getLogger(__name__)


def run(*,
        proxy: FlywheelProxy,
        file_input: InputFileWrapper,
        accepted_modules: List[str],
        tags_to_add: List[str],
        local_run: bool = False) -> None:
    """Runs the PreScreening process. Checks that the file suffix matches any
    accepted modules; if so, tag the file with the specified tags, else report
    error.

    Args:
        proxy: the proxy for the Flywheel instance
        file_input: The InputFileWrapper representing the file to
            potentially queue
        accepted_modules: List of accepted modules (case-insensitive)
        tags_to_add: List of tags to add if the file passes pre-screening
        local_run: Whether or not this is a local run - if so will verify the
            file but won't push changes upstream
    """
    module = file_input.basename.split('-')[-1]
    if module.lower() not in accepted_modules:
        raise GearExecutionError(f"Unallowed module suffix: {module}")

    if local_run or proxy.dry_run:
        log.info("Dry run or local run set: file passes prescreening, " +
                 f"would have added {tags_to_add}")
        return

    # add the specified tag
    log.info(f"Adding the following tags to file: {tags_to_add}")
    file = proxy.get_file(file_input.file_id)
    for tag in tags_to_add:
        file.add_tag(tag)
