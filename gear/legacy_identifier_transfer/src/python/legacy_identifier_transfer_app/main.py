"""Defines legacy_identifier_transfer."""

import logging
from typing import Dict, Optional

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from identifiers.model import IdentifierObject

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
    pass
