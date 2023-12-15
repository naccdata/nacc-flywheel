"""Utilities for writing errors to a CSV error file."""
from csv import DictWriter
from typing import Literal, Optional, TextIO

from pydantic import BaseModel, field_serializer


class ErrorType(BaseModel):
    """Represents type of error."""
    type: Literal['alert', 'error']
    detail: str


class CSVLocation(BaseModel):
    """Represents location of an error in a CSV file."""
    line: int
    column_name: str


class JSONLocation(BaseModel):
    """Represents the location of an error in a JSON file."""
    key_path: str


class FileError(BaseModel):
    """Represents an error that might be found in file during a step in a
    pipeline."""
    error_type: ErrorType
    error_location: Optional[CSVLocation | JSONLocation] = None
    flywheel_path: Optional[str] = None
    container_id: Optional[str] = None
    value: Optional[str] = None
    expected: Optional[str] = None
    message: str

    # pylint: disable=no-self-use
    @field_serializer('error_location')
    def serialize_location(self,
                           location: Optional[CSVLocation | JSONLocation]):
        """Serializes the error_location field to a JSON string.

        Args:
          location: the location object
        Returns:
          JSON string representation of the location object
        """
        if not location:
            return None

        return location.model_dump_json()

    # pylint: disable=no-self-use
    @field_serializer('error_type')
    def serialize_type(self, type: Optional[ErrorType]):
        """Serializes the error_type field to a JSON string.

        Args:
          type: the error type
        Returns:
          JSON string representation of the error type
        """

        if not type:
            return None

        return type.model_dump_json()


def identifier_error(line: int, value: str) -> FileError:
    """Creates a FileError for an unrecognized PTID error in a CSV file.

    Tags the error type as 'error:identifier'

    Args:
      line: the line where error occurred
      value: the value of the PTID
    Returns:
      a FileError object initialized for an identifier error
    """
    return FileError(error_type=ErrorType(type='error', detail='identifier'),
                     error_location=CSVLocation(line=line, column_name='ptid'),
                     value=value,
                     message='Unrecognized participant ID')


def empty_file_error() -> FileError:
    """Creates a FileError for an empty input file."""
    return FileError(error_type=ErrorType(type='error', detail='empty-file'),
                     message='Empty input file')


def missing_header_error() -> FileError:
    """Creates a FileError for a missing header."""
    return FileError(error_type=ErrorType(type='error',
                                          detail='missing-header'),
                     message='No file header found')


# pylint: disable=(too-few-public-methods)
class ErrorWriter:
    """Writes FileErrors to a stream as CSV."""

    def __init__(self, stream: TextIO, flywheel_path: str,
                 container_id: str) -> None:
        self.__writer = DictWriter(stream,
                                   fieldnames=FileError.__annotations__.keys(),
                                   dialect='unix')
        self.__flywheel_path = flywheel_path
        self.__container_id = container_id
        self.__header_written = False

    def __write_header(self):
        """Writes the header to the output stream."""
        if self.__header_written:
            return

        self.__writer.writeheader()
        self.__header_written = True

    def write(self, error: FileError) -> None:
        """Writes the error to the output stream with flywheel hierarchy
        information filled in for the reference file.

        Args:
          error: the file error object
        """
        self.__write_header()

        error.flywheel_path = self.__flywheel_path
        error.container_id = self.__container_id
        self.__writer.writerow(error.model_dump())
