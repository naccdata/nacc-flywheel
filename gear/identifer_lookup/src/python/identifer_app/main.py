"""Defines ADD DETAIL computation."""

import logging
from typing import Any, Dict, List, TextIO

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from identifiers.model import Identifier

log = logging.getLogger(__name__)


def run(*, proxy: FlywheelProxy, input_file: TextIO,
        identifiers: Dict[str, Identifier], output_file: TextIO,
        error_file: TextIO) -> bool:
    """Runs ADD DETAIL process.

    Args:
      proxy: the proxy for the Flywheel instance
      input_file: the data input stream
      output_file: the data output stream
      error_file: the error output stream
    Returns:
      True if there were IDs with no corresponding NACCID
    """
    return False
