"""Defines ADD DETAIL computation."""

import logging
from typing import Any, List

from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)

def run(*,
        proxy: FlywheelProxy,
        s3_client,
        form_file):
    """Runs ADD DETAIL process.
    
    Args:
      proxy: the proxy for the Flywheel instance
      s3_client: boto3 client for rules S3 bucket
      form_file: path of input form file
    """
    pass