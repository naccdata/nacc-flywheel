"""Defines legacy_identifier_transfer."""

import logging
from typing import Dict, Optional

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from identifiers.model import IdentifierObject
from inputs.environment import get_environment_variable

log = logging.getLogger(__name__)


def run(*,
        proxy: FlywheelProxy,
        adcid: Optional[int] = None,
        identifiers: Dict[str, IdentifierObject]
        ):
    """Runs ADD DETAIL process.

    Args:
      proxy: the proxy for the Flywheel instance
      adcid: the ADCID for the current center
      identifiers: the map from PTID to Identifier object
    """
    log.info(f"Running the Legacy Identifier Transfer gear for ADCID {adcid}")

    env_var = get_environment_variable("AWS_DEFAULT_REGION")
    log.info(env_var)
    pass
