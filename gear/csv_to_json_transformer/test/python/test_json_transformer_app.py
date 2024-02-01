import csv
from io import StringIO
from typing import Any, List

import pytest


def write_to_stream(data: List[List[Any]], stream: StringIO) -> None:
    """Writes data to the StringIO object for use in a test.

    Resets stream pointer to beginning.

    Args:
      data: tabular data
      stream: the output stream
    """
    writer = csv.writer(stream,
                        delimiter=',',
                        quotechar='\"',
                        quoting=csv.QUOTE_NONNUMERIC,
                        lineterminator='\n')
    writer.writerows(data)
    stream.seek(0)

