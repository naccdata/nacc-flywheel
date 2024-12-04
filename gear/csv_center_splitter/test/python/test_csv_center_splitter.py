"""Tests for CSV Center Splitter, namely the CSVCenterSplitterVisitor."""
import csv
from io import StringIO
from typing import Any, List

import pytest
from csv_center_splitter_app.main import CSVVisitorCenterSplitter
from outputs.errors import ListErrorWriter


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


@pytest.fixture(scope='function')
def visitor():
    """Creates a CSVVisitorCenterSplitter for testing."""
    error_writer = ListErrorWriter(container_id='dummmy-container',
                                   fw_path='dummy-fw-path')
    return CSVVisitorCenterSplitter('adcid', error_writer)


class TestCSVVisitorCenterSplitter:
    """Tests the CSVVisitorCenterSplitter class."""

    def test_visit_header(self, visitor):
        """Test the visit_header method, also checks that headers property is
        updated."""
        assert visitor.visit_header(['adcid', 'data'])
        assert visitor.headers == ['adcid', 'data']
        assert visitor.visit_header(['adcid'])
        assert visitor.headers == ['adcid']

    def test_visit_header_invalid(self, visitor):
        """Test an invalid header."""
        assert not visitor.visit_header(['id', 'data'])
        assert not visitor.visit_header([])

        errors = visitor.error_writer.errors()
        assert len(errors) == 2
        assert errors[0]['message'] == 'Missing field "adcid" in the header'

    def test_visit_row(self, visitor):
        """Test the visit_row method, also checks that split_data property is
        updated."""
        visitor.visit_header(['adcid', 'data'])
        for i in range(10):
            data = {'adcid': '0', 'data': f'value{i}'}
            assert visitor.visit_row(data, i + 1)
            assert len(visitor.split_data[0]) == i + 1
            assert visitor.split_data[0][i] == data

        assert len(visitor.split_data) == 1

        data = {'adcid': '1', 'data': 'dummy_value'}
        assert visitor.visit_row(data, 11)
        assert len(visitor.split_data) == 2
        assert len(visitor.split_data[1]) == 1
        assert visitor.split_data[1][0] == data

    def test_visit_row_invalid(self, visitor):
        """Test an invalid row."""
        visitor.visit_header(['adcid', 'data'])
        assert not visitor.visit_row({'adcid': 'hello', 'data': 'world'}, 1)

        errors = visitor.error_writer.errors()
        assert len(errors) == 1
        assert errors[0]['message'] == "Row 1 was invalid: ADCID value must be " \
            + "an int: invalid literal for int() with base 10: 'hello'"
