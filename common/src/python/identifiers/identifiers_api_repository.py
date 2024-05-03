import logging
from typing import List, Optional, overload

from identifiers.identifiers_repository import (IdentifierRepository,
                                                NoMatchingIdentifier)
from identifiers.model import Identifier
from pydantic import BaseModel, TypeAdapter
from requests_oauthlib import OAuth2Session

log = logging.getLogger(__name__)


class APIClientConfig(BaseModel):
    token_issuer: str
    client_id: str
    client_secret: str
    audience: str
    url: str


class IdentifiersAPIRepository(IdentifierRepository):

    def __init__(self, client: OAuth2Session, url: str) -> None:
        self.__client = client
        self.__url = url

    def add(self, identifier: Identifier) -> None:
        """Adds an Identifier to the repository.

        Args:
          identifier: the Identifier object to add
        """
        type_adapter = TypeAdapter(Identifier)
        body = type_adapter.dump_json(identifier)
        headers = {'Content-type': 'application/json'}
        response = self.__client.post(f"{self.__url}/identifiers",
                                      data=body,
                                      headers=headers)

        if not response.ok:
            log.warning("Failed to create identifier for %s:%s",
                        identifier.adc_id, identifier.patient_id)
            return

        log.info("Created NACCID for %s:%s", identifier.adc_id,
                 identifier.patient_id)

    def add_list(self, identifiers: List[Identifier]) -> None:
        """Adds a list of identifiers to the repository.

        Args:
          identifiers: the list of Identifiers
        """

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
            raise NoMatchingIdentifier("NACCID not found")

        if adc_id is not None and ptid:
            raise NoMatchingIdentifier("NACCID not found")

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
            return []

        return []
