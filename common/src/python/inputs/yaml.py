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
        return get_object_lists_from_stream(stream, yaml_file)

def get_object_lists_from_stream(stream, yaml_file) -> Optional[List[List[Any]]]:
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
    except yaml.MarkedYAMLError as exception:
        log.error("Error in YAML file: %s", yaml_file)
        mark = exception.problem_mark
        if mark:
            log.error("Error: line %s, column %s", mark.line + 1,
                        mark.column + 1)
        else:
            log.error("Error: %s", exception)
        return None
    except yaml.YAMLError as exception:
        log.error("Error in YAML file: %s", yaml_file)
        log.error("Error: %s", exception)
        return None
    else:
        return [*element_gen]
