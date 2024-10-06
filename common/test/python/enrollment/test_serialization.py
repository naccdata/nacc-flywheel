"""Tests serialization of enrollment/transfer form data."""

import pytest
from dates.form_dates import DATE_FORMATS, DateFormatException, parse_date
from enrollment.enrollment_transfer import EnrollmentRecord
from identifiers.model import CenterIdentifiers
from pydantic import ValidationError


@pytest.fixture
def bad_date_row():
    yield {
        'adcid': 0,
        'ptid': "123456",
        'naccid': "000000",
        'frmdate_enrl': "10/06/2024",
        'guid': '(*#$@@##)'
    }


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
        guid = row.get('guid', None)
        try:
            enroll_date = parse_date(date_string=row['frmdate_enrl'],
                                     formats=DATE_FORMATS)
        except DateFormatException:
            assert False, 'date should be OK'
        try:
            record = EnrollmentRecord(center_identifier=CenterIdentifiers(
                adcid=row['adcid'], ptid=row['ptid']),
                                      guid=guid if guid else None,
                                      naccid=None,
                                      start_date=enroll_date)
            assert record
        except ValidationError:
            assert False, "row should be valid, got {str(e)}"

    def test_create_error(self, bad_date_row):
        """Test create_from method."""
        row = bad_date_row
        guid = row.get('guid', None)
        try:
            parse_date(date_string=row['frmdate_enrl'], formats=DATE_FORMATS)
        except DateFormatException:
            assert True, 'date is invalid'

        try:
            EnrollmentRecord(center_identifier=CenterIdentifiers(
                adcid=row['adcid'], ptid=row['ptid']),
                             guid=guid if guid else None,
                             naccid=None,
                             start_date=row['frmdate_enrl'])
            assert False, "date is invalid should fail"
        except ValidationError as e:
            assert True, "date is invalid"
            assert e.error_count() == 2
            for error in e.errors():
                print(error)
                assert error['type'] == 'string_pattern_mismatch' or error[
                    'type'] == 'datetime_from_date_parsing'
                if error['type'] == 'string_pattern_mismatch':
                    assert error['loc'][0] == 'guid'
