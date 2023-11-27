"""Defines utilities for parsing YAML input."""
import logging
from typing import Any, List, Optional

import yaml

log = logging.getLogger(__name__)


def get_object_lists(yaml_file) -> Optional[List[List[Any]]]:
    """Gets lists of objects from the yaml file.

    Assumes the file can have more than one document.

    Args:
      yaml_file: name of the yaml file
    Returns:
      List of lists of object read from the file
    """
    with open(yaml_file, 'r', encoding='utf-8') as stream:
        return get_object_lists_from_stream(stream)


def get_object_lists_from_stream(stream) -> Optional[List[List[Any]]]:
    """Gets list of objects from the IO stream.

    Assumes the file can have more than one document.

    Args:
      stream: IO stream
      yaml_file: the name of the file
    Returns:
      List of lists of objects created from file or None if an error occurs
    """
    try:
        element_gen = yaml.safe_load_all(stream)
    except yaml.MarkedYAMLError as error:
        mark = error.problem_mark
        if mark:
            raise YAMLReadError(f'Error in YAML: line {mark.line + 1}, '
                                'column {mark.column + 1}') from error
        raise YAMLReadError(f'Error in YAML file: {error}') from error
    except yaml.YAMLError as error:
        raise YAMLReadError(f'Error in YAML file: {error}') from error
    else:
        return [*element_gen]


class YAMLReadError(Exception):
    """Exception class for errors that occur when reading objects from a YAML
    file."""
