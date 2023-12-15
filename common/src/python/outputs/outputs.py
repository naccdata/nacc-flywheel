"""Defines utilities for writing data files."""

from csv import DictWriter
from typing import Dict, List, Optional, TextIO

SimpleJSONObject = Dict[str, Optional[int | str | bool | float]]


# pylint: disable=(too-few-public-methods)
class CSVWriter:
    """Wrapper for DictWriter that ensures header is written."""

    def __init__(self, stream: TextIO, fieldnames: List[str]) -> None:
        self.__writer = DictWriter(stream,
                                   fieldnames=fieldnames,
                                   dialect='unix')
        self.__header_written = False

    def __write_header(self):
        """Writes the header to the output stream."""
        if self.__header_written:
            return

        self.__writer.writeheader()
        self.__header_written = True

    def write(self, json_object: SimpleJSONObject) -> None:
        """Writes the dictionary to the stream.

        Dictionary is assumed to correspond to a row from a CSV file, and so
        the values all must have primitive types.

        Args:
          json_object: dictionary with only primitive values
        """
        self.__write_header()
        self.__writer.writerow(json_object)
