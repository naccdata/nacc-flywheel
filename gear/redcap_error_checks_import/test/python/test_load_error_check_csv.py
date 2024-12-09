"""
Tests the load_error_check_csv method.
"""
import pytest
from outputs.errors import ListErrorWriter
from redcap_error_checks_import.error_check_csv_visitor import ErrorCheckCSVVisitor
from redcap_error_checks_import.main import load_error_check_csv


@pytest.fixture(scope='function')
def error_writer():
    """Creates an ErrorWriter for testing."""
    return ListErrorWriter(container_id='dummmy-container',
                           fw_path='dummy-fw-path')


@pytest.fixture(scope="module")
def file():
    """Creates dummy data in FileObject format for testing."""
    headers = list(ErrorCheckCSVVisitor.REQUIRED_HEADERS) \
        + ['error_no', 'do_in_redcap', 'in_prev_versions', 'questions']
    headers = ','.join(headers)
    row = 'd1a-ivp-m-001,001,Error,d1a,I,FRMDATED1A,Missingness' \
        + 'FRMDATED1A must be present,FRMDATED1A cannot be blank' \
        + 'Q0a. FRMDATED1A (D1a form date) cannot be blank,' \
        + 'If FRMDATED1A = blank,,,Yes,'

    data = f'{headers}\n{row}'
    return {"Body": str(data)}


@pytest.fixture(scope="module")
def key():
    """Create dummy key for data."""
    return "dummy_module/3.1/I/dummy_test_file.csv"


class TestLoadErrorCheckCSV:
    """Tests the load_error_check_csv method."""

    def test_load_error_check_csv(self, key, file, error_writer):
        """Test loading with valid dummy data."""
        assert load_error_check_csv(key, file, error_writer) == [{
            "error_code": "d1a-ivp-m-001",
            "error_type": "Error",
            "form_name": "d1a",
            "packet": "dummy_packet",
            "var_name": "I",
            "check_type": "Missingness",
            "test_name": "FRMDATED1A must be present",
            "short_desc": "FRMDATED1A cannot be blank",
            "full_desc": "Q0a. FRMDATED1A (D1a form date) cannot be blank",
            "test_logic": "If FRMDATED1A = blank",
            "comp_forms": "",
            "comp_vars": ""
        }]
