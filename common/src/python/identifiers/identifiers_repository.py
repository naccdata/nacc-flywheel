"""Repository for Identifiers.

Inspired by
https://github.com/cosmicpython/code/tree/chapter_02_repository_exercise
"""

from typing import List, Optional, overload

from identifiers.model import Identifier
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session


class IdentifierRepository:
    """Repository for Identifier records.

    Assumes the Identifier class is mapped to the identifier table.

    Create repository within a resource block for a session to ensure that
    session lifecycle is correct.
    """

    def __init__(self, session: Session) -> None:
        self.__session = session

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

        Note: some valid arguments can be falsey.
        These are explicitly checked that they are not None.

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

    @overload
    def list(self, adc_id: int) -> List[Identifier]:
        ...

    @overload
    def list(self) -> List[Identifier]:
        ...

    def list(self, adc_id: Optional[int] = None) -> List[Identifier]:
        """Returns the list of all identifiers in the repository.

        If an ADCID is given filters identifiers by the center.

        Args:
          adc_id: the ADCID used for filtering

        Returns:
          List of all identifiers in the repository
        """
        if adc_id is None:
            return self.__session.query(Identifier).all()

        return self.__session.query(Identifier).filter_by(adc_id=adc_id).all()


class NoMatchingIdentifier(Exception):
    """Exception for case when identifier is not matched."""
