"""Utilities for using S3 client."""
import logging
from io import StringIO
from typing import Optional

import boto3
from ssm_parameter_store import EC2ParameterStore

log = logging.getLogger(__name__)


class S3BucketReader:
    """Reads files from an S3 bucket."""

    def __init__(self, boto_client, bucket_name: str) -> None:
        """Creates an object that uses the boto3 client to read from the
        bucket.

        Args:
          boto_client: the boto3 s3 client
          bucket_name: the prefix for the bucket
        Returns:
          the object for the client and bucket
        """
        self.__client = boto_client
        self.__bucket = bucket_name

    @property
    def exceptions(self):
        """Expose boto client exceptions."""
        return self.__client.exceptions

    @property
    def bucket_name(self) -> str:
        """Expose name of bucket."""
        return self.__bucket

    def read_data(self, filename: str) -> StringIO:
        """Reads the file object from S3 with bucket name and file name.

        Args:
        file_name: name of file
        """

        file_obj = self.__client.get_object(Bucket=self.__bucket, Key=filename)

        return StringIO(file_obj['Body'].read().decode('utf-8'))

    @classmethod
    def create_from(cls, *, store: EC2ParameterStore,
                    param_path: str) -> Optional['S3BucketReader']:
        """Returns the bucket reader using the access credentials in the
        parameter store at the given path.

        Args:
          store: the parameter store with the credentials
          path: the parameter store path for the S3 credentials
        Returns:
          the S3BucketReader
        """
        parameters = store.get_parameters_by_path(path=param_path)
        access_key = parameters.get('accesskey')
        secret_key = parameters.get('secretkey')
        region = parameters.get('region')
        bucket_name = parameters.get('bucket')

        client = boto3.client('s3',
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key,
                              region_name=region)
        if not bucket_name:
            return None

        return S3BucketReader(boto_client=client, bucket_name=bucket_name)
