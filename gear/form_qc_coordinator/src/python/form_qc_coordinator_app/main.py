"""Defines Form QC Coordinator."""

import logging

from flywheel_gear_toolkit import GearToolkitContext
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_adaptor.subject_adaptor import SubjectAdaptor
from gear_execution.gear_execution import ClientWrapper, GearExecutionError

log = logging.getLogger(__name__)


def run(*,
        gear_context: GearToolkitContext,
        client_wrapper: ClientWrapper,
        proxy: FlywheelProxy,
        subject: SubjectAdaptor,
        module: str,
        sort_by: str,
        check_all: bool = False):
    """Invoke QC process for the given participant

    Args:
        gear_context: Flywheel gear context
        client_wrapper: Flywheel SDK client wrapper
        proxy: Flywheel proxy for the client
        subject: Flywheel subject to run the QC checks
        module: module to be evaluated (eg. UDSv4, LBDv3, ...)
        sort_by: field name to sort the participant visits
        check_all: re-evaluate all visits for the module/participant

    Raises:
        GearExecutionError if any problem occurrs during the QC process
    """
    subject_info = subject.info
