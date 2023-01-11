"""Defines utilities for parsing YAML input."""
import logging
from typing import Any, List, Optional

import yaml

log = logging.getLogger(__name__)


def get_object_list(yaml_file) -> Optional[List[Any]]:
    """Gets list of objects from the yaml file."""
    with open(yaml_file, 'r', encoding='utf-8') as stream:
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
            return list(element_gen)
