"""Module for downloading and parsing rule definition schemas."""

import json
import logging
from io import StringIO
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Mapping, Optional

import yaml
from keys.keys import DefaultValues, FieldNames
from outputs.errors import ListErrorWriter, empty_field_error, system_error
from s3.s3_client import S3BucketReader

log = logging.getLogger(__name__)


class ParserException(Exception):
    """Raised when an error occurs during loading rule definitions."""


# pylint: disable=(too-few-public-methods)
class Parser:
    """Class to load the validation rules definitions as python objects."""

    def __init__(self, s3_bucket: S3BucketReader, strict: bool = True):
        """

        Args:
            s3_bucket (S3BucketReader): S3 bucket to load rule definitions
            strict (optional): Validation mode, defaults to True.
        """

        self.__s3_bucket = s3_bucket
        self.__strict = strict
        # optional forms file in S3 bucket
        self.__opfname = 'optional_forms.json'

    def download_rule_definitions(
            self, prefix: str,
            optional_forms: Optional[Dict[str, bool]]) -> Dict[str, Mapping]:
        """Download rule definition files from a source S3 bucket and generate
        validation schema. For optional forms, there are two definition files
        in the S3 bucket. Load the appropriate definition depending on whether
        the form is submitted or not.

        Args:
            prefix: S3 path prefix
            optional_forms (optional): Submission status of each optional form

        Returns:
            dict[str, Mapping[str, object]: Schema object from rule definitions

        Raises:
            ParserException: If error occurred while loading rule definitions
        """

        full_schema: dict[str, Mapping] = {}

        # Handle missing / at end of prefix
        if not prefix.endswith('/'):
            prefix += '/'

        rule_defs = self.__s3_bucket.read_directory(prefix)
        if not rule_defs:
            message = ('Failed to load definitions from the S3 bucket: '
                       f'{self.__s3_bucket.bucket_name}/{prefix}')
            raise ParserException(message)

        parser_error = False
        for key, file_object in rule_defs.items():
            if optional_forms:
                # Select which file to load depending on form is submitted or not
                filename = key.removeprefix(prefix)
                formname = filename.partition('_')[0]
                optional_def = filename.endswith('_optional.json')

                if formname in optional_forms:
                    if optional_forms[formname]:  # form is submitted
                        if optional_def:
                            continue  # skip optional schema
                    else:  # form not submitted
                        if not optional_def:
                            continue  # skip regular schema

            if 'Body' not in file_object:
                log.error('Failed to load the rule definition file: %s', key)
                parser_error = True
                continue

            file_data = StringIO(file_object['Body'].read().decode('utf-8'))
            rules_type = 'json'
            if 'ContentType' in file_object:
                rules_type = file_object['ContentType']

            try:
                if 'json' in rules_type:
                    form_def = json.load(file_data)
                elif 'yaml' in rules_type:
                    form_def = yaml.safe_load(file_data)
                else:
                    log.error('Unhandled rule definition file type: %s - %s',
                              key, rules_type)
                    parser_error = True
                    continue

                # If there are any duplicate keys(i.e. variable names) across
                # forms, they will be replaced with the latest definitions.
                # It is assumed all variable names are unique within a project
                if form_def:
                    full_schema.update(form_def)
                    log.info('Parsed rule definition file: %s', key)
                else:
                    log.error('Empty rule definition file: %s', key)
                    parser_error = True
            except (JSONDecodeError, yaml.YAMLError, TypeError) as error:
                log.error('Failed to parse the rule definition file: %s - %s',
                          key, error)
                parser_error = True

        if parser_error:
            raise ParserException(
                'Error(s) occurred while loading rule definitions')

        return full_schema

    def get_optional_forms_submission_status(
            self,
            *,
            input_data: Dict[str, Any],
            module: str,
            packet: Optional[str] = None,
            error_writer: ListErrorWriter) -> Optional[Dict[str, bool]]:
        """Get the list of optional forms for the module/packet from
        optional_forms.json file in rule definitions S3 bucket. Check whether
        each optional form is submitted or not using the mode variable in input
        data.

        Args:
            input_data: input data record
            module: module name
            packet: packet code,
            error_writer: error writer object to output error metadata

        Returns:
            Dict[str, bool]: submission status of each optional form

        Raises:
            ParserException: If failed to get optional forms submission status
        """

        s3_client = self.__s3_bucket
        try:
            optional_forms = json.load(s3_client.read_data(self.__opfname))
        except s3_client.exceptions.NoSuchKey as error:
            message = (f'Optional forms file {self.__opfname} '
                       f'not found in S3 bucket {s3_client.bucket_name}')
            error_writer.write(system_error(message, None))
            raise ParserException(message) from error
        except s3_client.exceptions.InvalidObjectState as error:
            message = f'Unable to access optional forms file {self.__opfname}: {error}'
            error_writer.write(system_error(message, None))
            raise ParserException(message) from error
        except (JSONDecodeError, TypeError) as error:
            message = f'Error in reading optional forms file {self.__opfname}: {error}'
            error_writer.write(system_error(message, None))
            raise ParserException(message) from error

        if not optional_forms or module not in optional_forms:
            log.warning('Cannot find optional forms info for module %s',
                        module)
            return None

        module_info = optional_forms[module]
        # some modules may not have separate packet codes, set to 'D' for default
        if not packet:
            packet = 'D'

        if packet not in module_info:
            log.warning('Cannot find optional forms info for packet %s/%s',
                        module, packet)
            return None

        packet_info: List[str] = module_info[packet]
        missing = []
        submission_status = {}
        for form in packet_info:
            mode_var = f'{FieldNames.MODE}{form}'
            if mode_var not in input_data or input_data[mode_var] == '':
                if self.__strict:
                    error_writer.write(empty_field_error(mode_var))
                    missing.append(mode_var)
                else:
                    submission_status[form] = False
                continue

            submission_status[form] = (input_data[mode_var]
                                       != DefaultValues.NOTFILLED)

        if missing:
            raise ParserException(
                f'Missing fields {missing} required to validate optional forms'
            )

        return submission_status
