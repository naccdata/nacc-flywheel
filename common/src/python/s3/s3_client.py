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


def read_data(*, s3_client, bucket_name: str, file_name: str):
    """Reads the file object from S3 with bucket name and file name.

    Args:
      s3_client: client for S3
      bucket_name: bucket prefix
      file_name: name of file
    """
    response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    return response['Body'].read()
