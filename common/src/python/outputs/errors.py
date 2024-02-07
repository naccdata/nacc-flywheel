"""Utilities for writing errors to a CSV error file."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, TextIO

from outputs.outputs import CSVWriter
from pydantic import BaseModel, Field, field_serializer


class ErrorType(BaseModel):
    """Represents type of error."""
    error_type: Literal['alert', 'error'] = Field(serialization_alias='type')
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
    error_id: Optional[str] = None
    error_location: Optional[CSVLocation | JSONLocation] = None
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
    def serialize_type(self, error_type: Optional[ErrorType]):
        """Serializes the error_type field to a JSON string.

        Args:
          type: the error type
        Returns:
          JSON string representation of the error type
        """

        if not error_type:
            return None

        return error_type.model_dump_json(by_alias=True)


def identifier_error(line: int, value: str) -> FileError:
    """Creates a FileError for an unrecognized PTID error in a CSV file.

    Tags the error type as 'error:identifier'

    Args:
      line: the line where error occurred
      value: the value of the PTID
    Returns:
      a FileError object initialized for an identifier error
    """
    return FileError(error_type=ErrorType(error_type='error',
                                          detail='identifier'),
                     error_location=CSVLocation(line=line, column_name='ptid'),
                     value=value,
                     message='Unrecognized participant ID')


def empty_file_error() -> FileError:
    """Creates a FileError for an empty input file."""
    return FileError(error_type=ErrorType(error_type='error',
                                          detail='empty-file'),
                     message='Empty input file')


def missing_header_error() -> FileError:
    """Creates a FileError for a missing header."""
    return FileError(error_type=ErrorType(error_type='error',
                                          detail='missing-header'),
                     message='No file header found')


class ErrorWriter(ABC):
    """Abstract base class for error writer."""

    def __init__(self, container_id: str) -> None:
        self.__container_id = container_id

    @abstractmethod
    def write(self, error: FileError) -> None:
        """Writes the error to the output target of implementing class."""

    def set_container(self, error: FileError) -> None:
        error.container_id = self.__container_id


# pylint: disable=(too-few-public-methods)
class StreamErrorWriter(ErrorWriter):
    """Writes FileErrors to a stream as CSV."""

    def __init__(self, stream: TextIO, container_id: str) -> None:
        self.__writer = CSVWriter(stream=stream,
                                  fieldnames=list(
                                      FileError.__annotations__.keys()))
        super().__init__(container_id)

    def write(self, error: FileError) -> None:
        """Writes the error to the output stream with flywheel hierarchy
        information filled in for the reference file.

        Args:
          error: the file error object
        """
        self.set_container(error)
        self.__writer.write(error.model_dump())


class ListErrorWriter(ErrorWriter):
    """Collects FileErrors to file metadata."""

    def __init__(self, container_id: str) -> None:
        super().__init__(container_id)
        self.__errors: List[Dict[str, Any]] = []

    def write(self, error: FileError) -> None:
        """Captures error for writing to metadata.

        Args:
          error: the file error object
        """
        self.set_container(error)
        self.__errors.append(error.model_dump())

    def errors(self) -> List[Dict[str, Any]]:
        """Returns serialized list of accumulated file errors.

        Returns:
          List of serialized FileError objects
        """
        return self.__errors
