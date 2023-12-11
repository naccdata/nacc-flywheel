"""Repository for Identifiers.

Inspired by
https://github.com/cosmicpython/code/tree/chapter_02_repository_exercise
"""

from typing import List, Optional, overload

from identifiers.identifiers_tables import metadata
from identifiers.model import Identifier
from sqlalchemy import create_engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, sessionmaker


class IdentifierRepository:
    """Repository for Identifier records.

    Assumes the Identifier class is mapped to the identifier table.
    """

    def __init__(self, session: Session) -> None:
        self.__session = session

    @classmethod
    def create_from(cls, database_url: str) -> 'IdentifierRepository':
        """Creates an IdentifierRepository.

        Args:
          database_url: the URL for the database connection
        Returns:
          the IdentifierRepository for the identifier database at the URL
        """
        engine = create_engine(url=database_url)
        metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        return IdentifierRepository(session)

    # def add(self, identifier: Identifier):

    @overload
    def get(self, nacc_id: int) -> Identifier:
        ...

    @overload
    def get(self, nacc_id: Optional[int], adc_id: int,
            ptid: str) -> Identifier:
        ...

    def get(self,
            nacc_id: Optional[int] = None,
            adc_id: Optional[int] = None,
            ptid: Optional[str] = None) -> Identifier:
        """Returns Identifier object for the IDs given.

        Args:
          nacc_id: the (integer part of the) NACCID
          adc_id: the center ID
          ptid: the participant ID assigned by the center
        Returns:
          the identifier for the nacc_id or the adcid-ptid pair
        Raises:
          NoMatchingIdentifier: if no Identifier record was found
          TypeError: if the arguments are nonsensical
        """
        print(f"arguments: {nacc_id}, {adc_id}, {ptid}")
        if nacc_id is not None:
            try:
                return self.__session.query(Identifier).filter_by(
                    nacc_id=nacc_id).one()
            except NoResultFound as error:
                raise NoMatchingIdentifier("NACCID not found") from error

        if adc_id is not None and ptid:
            try:
                return self.__session.query(Identifier).filter_by(
                    adc_id=adc_id, patient_id=ptid).one()
            except NoResultFound as error:
                raise NoMatchingIdentifier(
                    "ADCID-PTID pair not found") from error

        raise TypeError("Invalid arguments")

    def list(self) -> List[Identifier]:
        """Returns the list of all identifiers in the repository.

        Returns:
          List of all identifiers in the repository
        """
        return self.__session.query(Identifier).all()


class NoMatchingIdentifier(Exception):
    """Exception for case when identifier is matched."""
