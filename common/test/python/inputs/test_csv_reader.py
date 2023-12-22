from io import StringIO
from typing import Any, List

import pytest
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import ErrorWriter


@pytest.fixture(scope="function")
def empty_data_stream():
    """Create empty data stream."""
    yield StringIO()


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


@pytest.fixture(scope="function")
def no_header_stream():
    """Create data stream without header row."""
    data = [[1, 1, 8], [1, 2, 99]]
    stream = StringIO()
    write_to_stream(data, stream)
    yield stream


@pytest.fixture(scope="function")
def no_ids_stream():
    """Create data stream without expected column headers."""
    data = [['dummy1', 'dummy2', 'dummy3'], [1, 1, 8], [1, 2, 99]]
    stream = StringIO()
    write_to_stream(data, stream)
    yield stream


@pytest.fixture(scope="function")
def data_stream():
    """Create data stream without header row."""
    data = [['adcid', 'ptid', 'var1'], [1, '1', 8], [1, '2', 99]]
    stream = StringIO()
    write_to_stream(data, stream)
    stream.seek(0)
    yield stream


def empty(stream) -> bool:
    """Checks that the stream is empty.

    Returns   True if no data is read from the stream, False otherwise
    """
    stream.seek(0)
    return not bool(stream.readline())


class DummyVisitor(CSVVisitor):

    def __init__(self) -> None:
        super().__init__()


class TestCSVReader:

    def test_empty_input_stream(self):
        """Test empty input stream."""
        out_stream = StringIO()
        err_stream = StringIO()
        errors = read_csv(input_file=empty_data_stream,
                          error_writer=ErrorWriter(stream=err_stream,
                                                   container_id='dummy'),
                          visitor=DummyVisitor())
        assert False
