"""Repository for Identifiers.

Inspired by
https://github.com/cosmicpython/code/tree/chapter_02_repository_exercise
"""

import abc
import logging
from abc import abstractmethod
from typing import List, Optional, overload

from identifiers.model import Identifier
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


class IdentifierRepository(abc.ABC):

    @abstractmethod
    def add(self, identifier: Identifier) -> None:
        """Adds an Identifier to the repository.

        Args:
          identifier: the Identifier object to add
        """

    @abstractmethod
    def add_list(self, identifiers: List[Identifier]) -> None:
        """Adds a list of identifiers to the repository.

        Args:
          identifiers: the list of Identifiers
        """

    @abstractmethod
    @overload
    def get(self, nacc_id: int) -> Identifier:
        ...

    @abstractmethod
    @overload
    def get(self, nacc_id: Optional[int], adc_id: int,
            ptid: str) -> Identifier:
        ...

    @abstractmethod
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

    @abstractmethod
    @overload
    def list(self, adc_id: int) -> List[Identifier]:
        ...

    @abstractmethod
    @overload
    def list(self) -> List[Identifier]:
        ...

    @abstractmethod
    def list(self, adc_id: Optional[int] = None) -> List[Identifier]:
        """Returns the list of all identifiers in the repository.

        If an ADCID is given filters identifiers by the center.

        Args:
          adc_id: the ADCID used for filtering

        Returns:
          List of all identifiers in the repository
        """


class IdentifierSQLAlchemyRepository(IdentifierRepository):
    """Repository for Identifier records.

    Assumes the Identifier class is mapped to the identifier table.

    Create repository within a resource block for a session to ensure that
    session lifecycle is correct.
    """

    def __init__(self, session: Session) -> None:
        self.__session = session

    def add(self, identifier: Identifier) -> None:
        self.__session.add(identifier)

    def add_list(self, identifiers: List[Identifier]) -> None:
        self.__session.add_all(identifiers)

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


class IdentifierUnitOfWork(abc.ABC):
    """UnitOfWork object for managing interactions with the idenfier
    repository.

    Inspired by https://www.cosmicpython.com/book/chapter_06_uow.html
    """

    @property
    def repository(self) -> Optional[IdentifierSQLAlchemyRepository]:
        """Returns the IdentifierRepository for this unit of work."""
        return None

    def __enter__(self):
        """Entrypoint for context manager."""
        return self

    def __exit__(self, *args):
        """Exit for context manager.

        By default calls rollback
        """
        self.rollback()

    @abc.abstractmethod
    def commit(self):
        """Commits identifiers to repository."""
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        """Rollsback any identifiers added to repository."""
        raise NotImplementedError


class SQLAlchemyUnitOfWork(IdentifierUnitOfWork):
    """Unit-of-work object for managing indentifier repository using
    SQLAlchemy.

    Inspired by https://www.cosmicpython.com/book/chapter_06_uow.html
    """

    def __init__(self, session_factory):
        self.__session_factory = session_factory
        self.__session: Optional[Session] = None
        self.__repository: Optional[IdentifierSQLAlchemyRepository] = None

    @property
    def repository(self) -> Optional[IdentifierSQLAlchemyRepository]:
        """Returns the currently set repository.

        Repository is created when context manager is entered.
        """
        return self.__repository

    def __enter__(self):
        """Entry for context manager.

        Creates session and repository object.
        """
        self.__session = self.__session_factory()
        self.__repository = IdentifierSQLAlchemyRepository(self.__session)
        return super().__enter__()

    def __exit__(self, *args):
        """Exit for context manager.

        Closes session.
        """
        super().__exit__(*args)
        if self.__session:
            self.__session.close()

    def commit(self):
        """Commits any identifiers added to the repository."""
        if self.__session:
            self.__session.commit()

    def rollback(self):
        """Rolls back any identifiers added to repository."""
        if self.__session:
            self.__session.rollback()


class NoMatchingIdentifier(Exception):
    """Exception for case when identifier is not matched."""
