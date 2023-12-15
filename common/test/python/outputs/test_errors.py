"""Tests for ErrorWriter class."""

# pylint: disable=no-self-use,redefined-outer-name,too-few-public-methods
from csv import DictReader
from io import StringIO

from outputs.errors import (CSVLocation, ErrorType, ErrorWriter, FileError,
                            JSONLocation)


class TestFileError:
    """Tests the FileError model class."""

    def test_serialization(self):
        """Tests that serialization produces a dict with the location a
        string."""
        error = FileError(error_type=ErrorType(type='error',
                                               detail='the-error'),
                          error_location=JSONLocation(key_path='k1.k2.k3'),
                          value='the-value',
                          message='the-message')
        result = error.model_dump()
        assert isinstance(result, dict)
        assert result['error_location'] == '{"key_path":"k1.k2.k3"}'
        assert result['error_type'] == '{"type":"error","detail":"the-error"}'


class TestErrorWriter:
    """Tests the error writer class."""

    def test_write(self):
        """Tests that the error writer writes CSV with the flywheel hierarchy
        information inserted."""
        stream = StringIO()
        writer = ErrorWriter(stream=stream,
                             flywheel_path="the-path",
                             container_id='the-id')
        writer.write(
            FileError(error_type=ErrorType(type='error', detail='the-error'),
                      error_location=CSVLocation(line=10, column_name='ptid'),
                      flywheel_path=None,
                      container_id=None,
                      value='the-value',
                      expected=None,
                      message='the-message'))
        stream.seek(0)
        reader = DictReader(stream, dialect='unix')
        assert reader.fieldnames
        assert reader.fieldnames == list(FileError.__annotations__.keys())
        row = next(reader)
        assert row['flywheel_path'] == 'the-path'
        assert row['container_id'] == 'the-id'
