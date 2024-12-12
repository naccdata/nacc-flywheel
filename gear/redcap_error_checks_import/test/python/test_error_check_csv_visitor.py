"""
Tests the ErrorCheckCSVVisitor.
"""
import pytest
from outputs.errors import ListErrorWriter
from redcap_error_checks_import_app.error_check_csv_visitor import (
    ErrorCheckCSVVisitor,
    ErrorCheckKey,
)


@pytest.fixture(scope='function')
def error_writer():
    """Creates an ErrorWriter for testing."""
    return ListErrorWriter(container_id='dummmy-container',
                           fw_path='dummy-fw-path')

@pytest.fixture(scope='function')
def visitor(error_writer):
    """Creates a ErrorCheckCSVVisitor for testing."""
    key = ErrorCheckKey.create_from_key(
        'CSV/module/1.0/dummy_packet/form_dummy_error_checks.csv')

    visitor = ErrorCheckCSVVisitor(key=key,
                                   error_writer=error_writer)

    headers = list(visitor.REQUIRED_HEADERS)
    assert visitor.visit_header(headers)
    return visitor


@pytest.fixture(scope='module')
def expected_extra_headers():
    """Define the extra headers that are expected in the
    CSVs but should not be in the final output.
    """
    return ['error_no', 'do_in_redcap', 'in_prev_versions', 'questions']


@pytest.fixture(scope='module')
def data():
    """Creates a dummy row to test on."""
    return {
        "error_code": "dummy-ivp-m-001",
        "error_no": "1",            # should not be in final output
        "error_type": "Error",
        "form_name": "dummy",
        "packet": "dummy_packet",
        "var_name": "TESTVAR",
        "check_type": "Missingness",
        "test_name": "TESTVAR test",
        "short_desc": "This is a test for TESTVAR",
        "full_desc": "Q0 This is a longer test description for TESTVAR",
        "test_logic": "IF TESTVAR = SOMECONDITION",
        "comp_forms": "",
        "comp_vars": "",
        "do_in_redcap": "Yes",      # should not be in final output
        "in_prev_versions": "No",   # should not be in final output
        "questions": ""             # should not be in final output
    }

class TestErrorCheckCSVVisitor:
    """Tests the ErrorCheckCSVVisitor class."""

    def test_visit_header(self, visitor, expected_extra_headers):
        """Tests the visit_header method; pytest fixture tests
        this on creation as well.
        """
        # testing the expected extra headers
        header = list(visitor.REQUIRED_HEADERS)
        header.extend(expected_extra_headers)
        assert visitor.visit_header(header)

    def test_visit_header_missing(self, visitor):
        """Tests when the header is missing expected fields."""
        assert not visitor.visit_header([])
        errors = visitor.error_writer.errors()

        assert len(errors) == len(visitor.REQUIRED_HEADERS)
        for error in errors:
            assert error['message'].startswith("Missing field")
            assert error['message'].endswith("in the header")

    def test_visit_row(self, visitor, data):
        """Test visiting a row, and that the extra fields are removed
        from final output."""
        assert visitor.visit_row(data, 1)
        assert visitor.validated_error_checks == [{
            "error_code": "dummy-ivp-m-001",
            "error_type": "Error",
            "form_name": "dummy",
            "packet": "dummy_packet",
            "var_name": "TESTVAR",
            "check_type": "Missingness",
            "test_name": "TESTVAR test",
            "short_desc": "This is a test for TESTVAR",
            "full_desc": "Q0 This is a longer test description for TESTVAR",
            "test_logic": "IF TESTVAR = SOMECONDITION",
            "comp_forms": "",
            "comp_vars": ""
        }]

    def test_visit_row_invalid(self, visitor):
        """Test visiting a row with a dummy field (to not trigger empty row bypass),
        which will trigger complaints about missing errors
        """
        data = {k: "" for k in visitor.REQUIRED_HEADERS}
        data['dummy'] = 'not-empty'
        assert not visitor.visit_row(data, 1)

        errors = visitor.error_writer.errors()
        assert len(errors) == 12
        for error in errors:
            assert error['message'].endswith("is required") or \
                error['message'].startswith('Expected')

            for field in visitor.ALLOWED_EMPTY_FIELDS:
                assert field not in error['message']

    def test_visit_enrollment_form(self, error_writer):
        """Test visiting an enrollment form which is a special case
        as it does not have a packet.
        """
        key = ErrorCheckKey.create_from_key(
            'CSV/ENROLL/1.0/form_dummy_error_checks.csv')

        visitor = ErrorCheckCSVVisitor(key=key,
                                       error_writer=error_writer)

        headers = list(visitor.REQUIRED_HEADERS)
        headers.remove('packet')
        assert visitor.visit_header(headers)

        data = {
            "error_code": "enrl-ivp-m-001",
            "error_no": "1",            # should not be in final output
            "error_type": "Error",
            "form_name": "enrl",
            "var_name": "TESTVAR",
            "check_type": "Missingness",
            "test_name": "TESTVAR test",
            "short_desc": "This is a test for TESTVAR",
            "full_desc": "Q0 This is a longer test description for TESTVAR",
            "test_logic": "IF TESTVAR = SOMECONDITION",
            "comp_forms": "",
            "comp_vars": "",
            "do_in_redcap": "Yes",      # should not be in final output
            "in_prev_versions": "No",   # should not be in final output
            "questions": ""             # should not be in final output
        }
        assert visitor.visit_row(data, 1)
        assert visitor.validated_error_checks == [{
            "error_code": "enrl-ivp-m-001",
            "error_type": "Error",
            "form_name": "enrl",
            "var_name": "TESTVAR",
            "check_type": "Missingness",
            "test_name": "TESTVAR test",
            "short_desc": "This is a test for TESTVAR",
            "full_desc": "Q0 This is a longer test description for TESTVAR",
            "test_logic": "IF TESTVAR = SOMECONDITION",
            "comp_forms": "",
            "comp_vars": ""
        }]

    def test_visit_header_form(self, error_writer):
        """Test visiting header form, which is mostly the same
        but form_name needs the module prepended.
        """
        key = ErrorCheckKey.create_from_key(
            'CSV/UDS/4.0/F/form_header_fvp_error_checks_mc.csv')

        visitor = ErrorCheckCSVVisitor(key=key,
                                       error_writer=error_writer)

        headers = list(visitor.REQUIRED_HEADERS)
        assert visitor.visit_header(headers)

        data = {
            "error_code": "uds_header-ivp-m-001",
            "error_no": "1",            # should not be in final output
            "error_type": "Error",
            "form_name": "uds_header",
            "packet": "F",
            "var_name": "TESTVAR",
            "check_type": "Missingness",
            "test_name": "TESTVAR test",
            "short_desc": "This is a test for TESTVAR",
            "full_desc": "Q0 This is a longer test description for TESTVAR",
            "test_logic": "IF TESTVAR = SOMECONDITION",
            "comp_forms": "",
            "comp_vars": "",
            "do_in_redcap": "Yes",      # should not be in final output
            "in_prev_versions": "No",   # should not be in final output
            "questions": ""             # should not be in final output
        }
        assert visitor.visit_row(data, 1)
        assert visitor.validated_error_checks == [{
            "error_code": "uds_header-ivp-m-001",
            "error_type": "Error",
            "form_name": "uds_header",
            "packet": "F",
            "var_name": "TESTVAR",
            "check_type": "Missingness",
            "test_name": "TESTVAR test",
            "short_desc": "This is a test for TESTVAR",
            "full_desc": "Q0 This is a longer test description for TESTVAR",
            "test_logic": "IF TESTVAR = SOMECONDITION",
            "comp_forms": "",
            "comp_vars": ""
        }]
