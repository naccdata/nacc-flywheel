import json
from typing import Any, Dict, Literal, Optional

import boto3
from botocore.exceptions import ClientError
from inputs.environment import get_environment_variable
from pydantic import BaseModel, ValidationError


def create_lambda_client():
    """Creates a boto3 lambda client if AWS credentials are set.

    Expects AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID, and
    AWS_DEFAULT_REGION.
    """
    secret_key = get_environment_variable('AWS_SECRET_ACCESS_KEY')
    access_id = get_environment_variable('AWS_ACCESS_KEY_ID')
    region = get_environment_variable('AWS_DEFAULT_REGION')
    if not secret_key or not access_id or not region:
        return None

    return boto3.client('lambda',
                        aws_access_key_id=access_id,
                        aws_secret_access_key=secret_key,
                        region_name=region)


class BaseRequest(BaseModel):
    """Base model for request objects with connection mode."""
    mode: Optional[Literal['dev', 'prod']] = 'prod'


class ResponseObject(BaseModel):
    """Base model for response objects."""
    statusCode: str
    headers: Dict[str, str]
    body: str


class LambdaClient:
    """Wrapper for boto3 lambda client."""

    def __init__(self, client) -> None:
        self.__client = client

    def invoke(self, name: str, request: BaseRequest) -> ResponseObject:
        """Invokes the named lambda function on the request object.

        Note: using this function requires AWS credentials with invoke rights
        on the lambda.

        Args:
          name: the name of the AWS lambda function
          request: the request object
        Returns:
          the response object from invoking the lambda function
        """
        try:
            response = self.__client.invoke(
                FunctionName=name,
                InvocationType='RequestResponse',
                Payload=request.model_dump_json().encode('utf-8'),
                LogType="None",
            )
        except ClientError as error:
            raise LambdaInvocationError(str(error)) from error

        try:
            return ResponseObject.model_validate_json(
                response['Payload'].read())
        except ValidationError as error:
            raise LambdaInvocationError(str(error)) from error


class LambdaInvocationError(Exception):
    """Error class for error related to invoking lambda."""
