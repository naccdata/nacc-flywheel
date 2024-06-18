"""Tests serialization of enrollment/transfer form data."""

from enrollment.enrollment_transfer import EnrollmentRecord
from pydantic import ValidationError


# pylint: disable=(too-few-public-methods)
class TestEnrollmentSerialization:
    """Tests for enrollment serialization."""

    # pylint: disable=(no-self-use)
    def test_create(self):
        """Test create_from method."""
        row = {
            'adcid': 0,
            'ptid': "123456",
            'frmdate_enrl': "2024-06-10",
            'guid': ''
        }
        try:
            record = EnrollmentRecord.create_from(row)
            assert record
        except ValidationError:
            assert False, "row should be valid"
