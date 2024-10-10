"""Utilities to handle dates."""

from datetime import datetime
from typing import List

DATE_FORMATS = ['%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d', '%Y-%m-%d']


def parse_date(*, date_string: str, formats: List[str]) -> datetime:
    """Parses the date string against the list of formats.

    Args:
      date_string: a date as a string
    Returns:
      the datetime object for the string
    Raises:
      DateFormatException if the string doesn't match either format
    """

    for format in formats:
        try:
            return datetime.strptime(date_string, format)
        except ValueError:
            pass

    raise DateFormatException(formats=formats)


class DateFormatException(Exception):

    def __init__(self, formats: List[str]) -> None:
        self.formats = formats
