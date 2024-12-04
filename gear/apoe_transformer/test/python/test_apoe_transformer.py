"""Tests for the APOE transformer, namely APOETransformerCSVVisitor."""
import pytest
from apoe_transformer_app.main import (
    APOE_ENCODINGS,
    APOETransformerCSVVisitor,
)
from outputs.errors import ListErrorWriter


@pytest.fixture(scope='function')
def visitor():
    """Creates a APOETransformerCSVVisitor for testing."""
    error_writer = ListErrorWriter(container_id='dummmy-container',
                                   fw_path='dummy-fw-path')
    return APOETransformerCSVVisitor(error_writer)


@pytest.fixture(scope='module')
def apoe_headers():
    """Creates the expected headers."""
    return APOETransformerCSVVisitor.EXPECTED_APOE_INPUT_HEADERS


class TestAPOETransformerCSVVisitor:
    """Tests the APOETransformerCSVVisitor class."""

    def test_visit_header(self, visitor, apoe_headers):
        """Test the visit_header method."""
        assert visitor.visit_header(apoe_headers)
        assert visitor.visit_header((*apoe_headers, 'extra1', 'extra2'))

    def test_visit_header_invalid(self, visitor):
        """Test an invalid header."""
        assert not visitor.visit_header(['a1', 'a2'])
        assert not visitor.visit_header([])

        errors = visitor.error_writer.errors()
        assert len(errors) == 8
        assert errors[0]['message'] == 'Missing field adcid in the header'

    def test_visit_row(self, visitor, apoe_headers):
        """Test the visit_row method, and check that the transformed_data
        property was updated."""
        visitor.visit_header(apoe_headers)
        for i, (pair, value) in enumerate(APOE_ENCODINGS.items()):
            data = {
                'adcid': 0,
                'ptid': 0,
                'naccid': 0,
                'a1': pair[0],
                'a2': pair[1]
            }
            assert visitor.visit_row(data, i + 1)
            assert len(visitor.transformed_data) == i + 1
            assert visitor.transformed_data[i] == {
                'adcid': 0,
                'ptid': 0,
                'naccid': 0,
                'apoe': value
            }

        # test the 9/unknown case
        data = {'adcid': 3, 'ptid': 3, 'naccid': 3, 'a1': "EE", 'a2': "FF"}
        assert visitor.visit_row(data, 10)
        assert len(visitor.transformed_data) == 10
        assert visitor.transformed_data[9] == {
            'adcid': 3,
            'ptid': 3,
            'naccid': 3,
            'apoe': 9
        }

    def test_visit_row_drops_extra_fields(self, visitor, apoe_headers):
        """Test that the visit_row method drops unexpected fields in output."""
        visitor.visit_header(apoe_headers)

        data = {
            'adcid': 3,
            'ptid': 3,
            'naccid': 3,
            'a1': "EE",
            'a2': "FF",
            'extra1': 'hello',
            'extra2': 'world'
        }
        assert visitor.visit_row(data, 1)
        assert len(visitor.transformed_data) == 1
        assert visitor.transformed_data[0] == {
            'adcid': 3,
            'ptid': 3,
            'naccid': 3,
            'apoe': 9
        }
