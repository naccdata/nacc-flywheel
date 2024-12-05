"""Defines legacy_identifier_transfer."""

import logging
from typing import Optional

from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)


def run(*,
        proxy: FlywheelProxy,
        adcid: Optional[int] = None
        ):
    """Runs ADD DETAIL process.

    Args:
      proxy: the proxy for the Flywheel instance
    """
    log.info("Running the Legacy Identifier Transfer gear.")
    log.info(f"ADCID: {adcid}")
    pass
