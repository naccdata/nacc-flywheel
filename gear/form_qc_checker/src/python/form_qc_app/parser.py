"""Module for downloading and parsing rule definition schemas."""

import json
import logging
import sys
from io import StringIO
from json.decoder import JSONDecodeError
from typing import Mapping

import yaml
from s3.s3_client import S3BucketReader
from yaml.loader import SafeLoader

log = logging.getLogger(__name__)


class FormVars:
    """Class to store frquently accessed form data variable names."""

    NACCID = 'naccid'
    MODULE = 'module'
    PACKET = 'packet'
    PTID = 'ptid'


class Parser:
    """Class to load the validation rules definitions as python objects."""

    def __init__(self, s3_bucket: S3BucketReader):
        """

        Args:
            s3_bucket (S3BucketReader): S3 bucket to load rule definitions
        """

        self.__s3_bucket = s3_bucket

    def download_rule_definitions(
            self, prefix: str) -> dict[str, Mapping[str, object]]:
        """Download rule definition files from a source S3 bucket and generate
        validation schema.

        Args:
            prefix (str): S3 path prefix

        Returns:
            dict[str, Mapping[str, object]: Schema object from rule definitions
        """

        full_schema: dict[str, Mapping[str, object]] = {}

        # Handle missing / at end of prefix
        if not prefix.endswith('/'):
            prefix += '/'

        rule_defs = self.__s3_bucket.read_directory(prefix)
        if not rule_defs:
            log.error(
                'Failed to load rule definitions from the S3 bucket: %s/%s',
                self.__s3_bucket.bucket_name, prefix)
            sys.exit(1)

        for key, file_object in rule_defs.items():
            if 'Body' not in file_object:
                log.error('Failed to load the rule definition file: %s', key)
                sys.exit(1)

            file_data = StringIO(file_object['Body'].read().decode('utf-8'))
            rules_type = 'json'
            if 'ContentType' in file_object:
                rules_type = file_object['ContentType']

            try:
                if 'json' in rules_type:
                    form_def = json.load(file_data)
                elif 'yaml' in rules_type:
                    form_def = yaml.load(file_data, Loader=SafeLoader)
                else:
                    log.error('Unhandled rule definition file type: %s - %s',
                              key, rules_type)
                    sys.exit(1)

                # If there are any duplicate keys(i.e. variable names) across
                # forms, they will be replaced with the latest definitions.
                # It is assumed all variable names are unique within a project
                if form_def:
                    full_schema.update(form_def)
                    log.info('Parsed rule definition file: %s', key)
                else:
                    log.error('Empty rule definition file: %s', key)
                    sys.exit(1)
            except (JSONDecodeError, yaml.YAMLError, TypeError) as error:
                log.error('Failed to parse the rule definition file: %s - %s',
                          key, error)
                sys.exit(1)

        return full_schema
