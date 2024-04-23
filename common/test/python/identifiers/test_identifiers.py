"""Tests for IdentifierRepository."""

import pytest
from identifiers.identifiers_repository import (IdentifierRepository,
                                                NoMatchingIdentifier)
from identifiers.identifiers_tables import metadata
from identifiers.model import Identifier
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# pylint: disable=(redefined-outer-name)
@pytest.fixture(scope="function")
def sqlite_db():
    """Fixture to create sqlite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


# pylint: disable=(redefined-outer-name)
@pytest.fixture(scope="function")
def session(sqlite_db):
    """Fixture to create session for sqlite database."""
    yield sessionmaker(bind=sqlite_db)()


# pylint: disable=(no-self-use)
class TestIdentifierRepository:
    """Tests for the IdentifierRepository class."""

    def test_identifier_load(self, session):
        """Sanity check that mapping works for save."""
        session.execute(
            text("INSERT INTO identifier "
                 "(nacc_id, nacc_adc, adc_id, patient_id) VALUES "
                 '(1, 2934, 0, "992321"),'
                 '(2, 5397, 0, "168721"),'
                 '(3, 7162, 0, "239451")'))
        expected = [
            Identifier(nacc_id=1, nacc_adc=2934, adc_id=0,
                       patient_id="992321"),
            Identifier(nacc_id=2, nacc_adc=5397, adc_id=0,
                       patient_id="168721"),
            Identifier(nacc_id=3, nacc_adc=7162, adc_id=0, patient_id="239451")
        ]
        assert session.query(Identifier).all() == expected

    def test_identifier_save(self, session):
        """Sanity check that mapping works for save."""
        new_identifier = Identifier(nacc_id=4,
                                    nacc_adc=9999,
                                    adc_id=0,
                                    patient_id="11111")
        session.add(new_identifier)
        session.commit()

        rows = list(
            session.execute(
                text('SELECT nacc_id, nacc_adc, adc_id, patient_id '
                     'FROM "identifier"')))
        assert rows == [(4, 9999, 0, "11111")]

    def test_empty_repository(self, session):
        """Test empty repository behaves empty."""
        repo = IdentifierRepository(session)
        assert not repo.list()

        with pytest.raises(NoMatchingIdentifier) as error:
            repo.get(nacc_id=1)
        assert str(error.value) == "NACCID not found"

    def test_non_empty_repository(self, session):
        """Test repository after add."""
        expected = [
            Identifier(nacc_id=1, nacc_adc=2934, adc_id=0,
                       patient_id="992321"),
            Identifier(nacc_id=2, nacc_adc=5397, adc_id=0,
                       patient_id="168721"),
            Identifier(nacc_id=3, nacc_adc=7162, adc_id=0, patient_id="239451")
        ]

        for identifier in expected:
            session.add(identifier)
        session.commit()

        repo = IdentifierRepository(session)
        assert repo.list() == expected
        assert repo.get(nacc_id=1) == Identifier(nacc_id=1,
                                                 nacc_adc=2934,
                                                 adc_id=0,
                                                 patient_id="992321")
        assert repo.get(adc_id=0, ptid="992321") == Identifier(  # type: ignore
            nacc_id=1,
            nacc_adc=2934,
            adc_id=0,
            patient_id="992321")
        with pytest.raises(NoMatchingIdentifier) as error:
            repo.get(adc_id=1, ptid="0")  # type: ignore
        assert str(error.value) == "ADCID-PTID pair not found"
        with pytest.raises(TypeError) as error:
            repo.get(adc_id=0, ptid="")  # type: ignore
        assert str(error.value) == "Invalid arguments"

    def test_list_by_adcid(self, session):
        """Test listing by ADCID."""

        expected = [
            Identifier(nacc_id=1, nacc_adc=2934, adc_id=0,
                       patient_id="992321"),
            Identifier(nacc_id=3, nacc_adc=7162, adc_id=0, patient_id="239451")
        ]

        for identifier in expected:
            session.add(identifier)
        session.add(
            Identifier(nacc_id=2, nacc_adc=5397, adc_id=1,
                       patient_id="168721"))
        session.commit()

        repo = IdentifierRepository(session)
        assert repo.list(adc_id=0) == expected
        assert repo.list(adc_id=1) == [
            Identifier(nacc_id=2, nacc_adc=5397, adc_id=1, patient_id="168721")
        ]
        assert not repo.list(adc_id=99)

    def test_add(self, session):
        """Test adding single identifier."""
        repo = IdentifierRepository(session)
        assert not repo.list(), "repo should be empty"

        input = Identifier(nacc_id=5,
                           nacc_adc=3333,
                           adc_id=3,
                           patient_id='92413')
        repo.add(identifier=input)
        try:
            output = repo.get(nacc_id=input.nacc_id)
            assert output == input, "should be added identifier"
        except NoMatchingIdentifier:
            assert False, "should be added identifier"
