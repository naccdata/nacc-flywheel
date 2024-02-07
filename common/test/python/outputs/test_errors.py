"""Tests for ErrorWriter class."""

# pylint: disable=no-self-use,redefined-outer-name,too-few-public-methods
from csv import DictReader
from io import StringIO

from outputs.errors import (CSVLocation, FileError, JSONLocation,
                            ListErrorWriter, StreamErrorWriter,
                            empty_file_error, identifier_error,
                            missing_header_error)


class TestFileError:
    """Tests the FileError model class."""

    def test_serialization(self):
        """Tests that serialization produces a dict with the location a
        string."""
        error = FileError(error_type='error',
                          error_code='the-error',
                          error_location=JSONLocation(key_path='k1.k2.k3'),
                          value='the-value',
                          message='the-message')
        result = error.model_dump()
        assert isinstance(result, dict)
        assert result['error_location'] == {"key_path":"k1.k2.k3"}
        assert result['error_type'] == 'error'

    def test_identifier_serialization(self):
        """Tests that error created by identifier_error can be serialized."""
        error = identifier_error(line=11, value='dummy')
        assert error.model_dump()

    def test_empty_file_serialization(self):
        """Test that error created by empty_file_error can be serialized."""
        error = empty_file_error()
        assert error.model_dump()

    def test_missing_header_serialization(self):
        """Test that error created by missing_header_error can be
        serialized."""
        error = missing_header_error()
        assert error.model_dump()


class TestErrorWriter:
    """Tests the error writer class."""

    def test_stream_write(self):
        """Tests that the stream error writer writes CSV with the flywheel
        hierarchy information inserted."""
        stream = StringIO()
        writer = StreamErrorWriter(stream=stream, container_id='the-id')
        writer.write(
            FileError(error_type='error',
                      error_code='the-error',
                      error_location=CSVLocation(line=10, column_name='ptid'),
                      container_id=None,
                      value='the-value',
                      expected=None,
                      message='the-message'))
        stream.seek(0)
        reader = DictReader(stream, dialect='unix')
        assert reader.fieldnames
        assert reader.fieldnames == list(FileError.__annotations__.keys())
        row = next(reader)
        assert row['container_id'] == 'the-id'

    def test_capture_write(self):
        """Tests that the capture error writer inserts the flywheel hierarchy
        information inserted."""
        writer = ListErrorWriter(container_id='the-id')
        writer.write(
            FileError(error_type='error',
                      error_code='the-error',
                      error_location=CSVLocation(line=10, column_name='ptid'),
                      container_id=None,
                      value='the-value',
                      expected=None,
                      message='the-message'))
        errors = writer.errors()
        assert errors[0]['container_id'] == 'the-id'
