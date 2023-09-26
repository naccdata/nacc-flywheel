"""Utilities for using S3 client."""
import boto3
from ssm_parameter_store import EC2ParameterStore


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
