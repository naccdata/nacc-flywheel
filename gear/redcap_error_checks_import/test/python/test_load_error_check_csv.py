"""
Tests the load_error_check_csv method.
"""
import pytest
from io import BytesIO

from outputs.errors import ListErrorWriter
from redcap_error_checks_import_app.error_check_csv_visitor import ErrorCheckCSVVisitor
from redcap_error_checks_import_app.main import load_error_check_csv


@pytest.fixture(scope='function')
def error_writer():
    """Creates an ErrorWriter for testing."""
    return ListErrorWriter(container_id='dummmy-container',
                           fw_path='dummy-fw-path')


@pytest.fixture(scope="module")
def headers():
    """Creates dummy headers for testing."""
    headers = list(ErrorCheckCSVVisitor.REQUIRED_HEADERS) \
        + ['error_no', 'do_in_redcap', 'in_prev_versions', 'questions']
    return ','.join(headers)

@pytest.fixture(scope="module")
def file(headers):
    """Creates dummy data in FileObject format for testing."""
    row = 'd1a-ivp-m-001,Error,d1a,I,FRMDATED1A,Missingness,' \
        + 'FRMDATED1A must be present,FRMDATED1A cannot be blank,' \
        + 'Q0a. FRMDATED1A (D1a form date) cannot be blank,' \
        + 'If FRMDATED1A = blank,,,001,Yes,'

    data = f'{headers}\n{row}'
    return {"Body": BytesIO(data.encode('utf-8'))}


@pytest.fixture(scope="module")
def key():
    """Create dummy key for data."""
    return "dummy_module/3.1/I/form_d1a_ivp_error_checks_mc.csv"


class TestLoadErrorCheckCSV:
    """Tests the load_error_check_csv method."""

    def test_valid_csv(self, key, file, error_writer):
        """Test loading with valid dummy data."""
        assert load_error_check_csv(key, file, error_writer) == [{
            "error_code": "d1a-ivp-m-001",
            "error_type": "Error",
            "form_name": "d1a",
            "packet": "I",
            "var_name": "FRMDATED1A",
            "check_type": "Missingness",
            "test_name": "FRMDATED1A must be present",
            "short_desc": "FRMDATED1A cannot be blank",
            "full_desc": "Q0a. FRMDATED1A (D1a form date) cannot be blank",
            "test_logic": "If FRMDATED1A = blank",
            "comp_forms": "",
            "comp_vars": ""
        }]

    def test_invalid_key(self):
        """Test with an invalid key."""
        with pytest.raises(ValueError) as e:
            load_error_check_csv("bad/key", None, None)

        assert str(e.value) == "Expected file to be under " \
            + "MODULE / FORM_VER / PACKET / filename"

    def test_empty_error_checks(self, key, headers, error_writer):
        """Test when there is only a header"""
        data = {"Body": BytesIO(headers.encode('utf-8'))}
        assert not load_error_check_csv(key, data, error_writer)
