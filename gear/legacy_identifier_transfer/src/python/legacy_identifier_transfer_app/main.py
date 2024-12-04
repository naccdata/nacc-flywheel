"""Defines legacy_identifier_transfer."""

import logging

from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)


def run(*,
        proxy: FlywheelProxy,
        ):
    """Runs ADD DETAIL process.

    Args:
      proxy: the proxy for the Flywheel instance
    """
    log.info("Running the Legacy Identifier Transfer gear.")
    pass
