# COPIED FROM ANOTHER PROJECT. MUST BE ALTERED FOR PULL SCAN PROJECT
"""Main function for running template push process."""
import logging
import sys

import boto3
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.api_key import get_api_key
from inputs.context_parser import parse_config
from inputs.parameter_store import get_parameter_store
from scan_metadata_app.main import run
from ssm_parameter_store import EC2ParameterStore

log = logging.getLogger(__name__)


def main():
    """Main method to distribute SCAN metadata from S3 bucket to center
    projects."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        context_args = parse_config(gear_context=gear_context, filename=None)
        dry_run = context_args['dry_run']

    parameter_store = get_parameter_store()
    if not parameter_store:
        log.error('Unable to connect to parameter store')
        sys.exit(1)

    api_key = get_api_key(parameter_store)
    if not api_key:
        log.error('No API key found. Check API key configuration')
        sys.exit(1)

    proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

    s3_client = get_s3_client(store=parameter_store,
                              path='/prod/flywheel/gearbot/loni')
    if not s3_client:
        log.error('Unable to connect to S3')
        sys.exit(1)

    table_list = [
        "v_scan_upload_with_qc", "v_scan_mri_dashboard", "v_scan_pet_dashboard"
    ]

    run(proxy=proxy,
        table_list=table_list,
        s3_client=s3_client,
        bucket_name='loni-table-data',
        center_tag_pattern=r'adcid-\d+',
        destination_label='ingest-scan')


if __name__ == "__main__":
    main()


def get_s3_client(*, store: EC2ParameterStore, path: str):
    """Returns the S3 client for the access credentials in the parameter store
    at the given path.

    Args:
      store: the parameter store with the credentials
      path: the parameter store path for the S3 credentials
    Returns:
      the boto3 S3 client
    """
    # Get S3 credentials
    parameters = store.get_parameters_by_path(path=path)
    access_key = parameters.get('accesskey')
    secret_key = parameters.get('secretkey')
    region = parameters.get('region')

    # Initialize the S3 client
    client = boto3.client('s3',
                          aws_access_key_id=access_key,
                          aws_secret_access_key=secret_key,
                          region_name=region)

    return client
