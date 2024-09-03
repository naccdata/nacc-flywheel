"""Defines repository as interface to user registry."""
from typing import List

from coreapi_client.api.default_api import DefaultApi
from coreapi_client.exceptions import ApiException
from coreapi_client.models.co_person_message import CoPersonMessage
from coreapi_client.models.identifier import Identifier


class UserRegistry:
    """Repository class for COManage user registry."""

    def __init__(self, api_instance: DefaultApi, coid: int):
        self.__api_instance = api_instance
        self.__coid = coid

    def create(self, *, firstname: str, lastname: str,
               email: str) -> List[Identifier]:
        """Creates a CoPerson record in the registry with name and email.

        Args:
          firstname: the first name of the user
          lastname: the last name of the user
          email: the email address of the user

        Returns:
          a list of CoManage Identifer objects
        """
        message = CoPersonMessage.from_dict({
            "CoPerson": {
                "co_id": str(self.__coid),
                "status": "A"
            },
            "EmailAddress": [{
                "mail": email,
                "type": "official",
                "verified": True
            }],
            "CoPersonRole": [{
                "cou_id": None,
                "affiliation": "member",
                "status": "A"
            }],
            "Name": [{
                "given": firstname,
                "family": lastname,
                "type": "official",
                "primary_name": True
            }]
        })
        assert message, "coperson creation failed"

        try:
            return self.__api_instance.add_co_person(coid=self.__coid,
                                                     co_person_message=message)
        except ApiException as error:
            raise RegistryError(f"API call failed: {error}")

    def get(self, *, identifier: str) -> List[CoPersonMessage]:
        """Returns the CoPersonMessage objects with the identifier.

        Args:
          the identifer string
        Returns:
          the list of CoPersonMessage objects with the identifier
        """
        try:
            response = self.__api_instance.get_co_person(coid=self.__coid,
                                                         identifier=identifier)
            assert response, "expecting identity in registry"
        except ApiException as error:
            raise RegistryError(f"API call failed: {error}")

        coperson_dict = response.to_dict()
        result = []
        for person_message in coperson_dict.values():
            coperson = CoPersonMessage.from_dict(person_message)
            if coperson:
                result.append(coperson)
        return result

    def list(self, email: str) -> List[CoPersonMessage]:
        """Returns the list of CoPersonMessage objects with the email.

        Args:
          the email address
        Returns:
          the list of CoPersonMessage objects with the email address
        """
        limit = 100
        page_index = 0
        read_length = limit

        result = []
        while read_length == limit:
            try:
                response = self.__api_instance.get_co_person(coid=self.__coid,
                                                             direction='asc',
                                                             limit=limit,
                                                             page=page_index)
            except ApiException as error:
                raise RegistryError(f"API call failed: {error}")

            coperson_dict = response.to_dict()
            read_length = len(coperson_dict.keys())
            page_index += 1

            for person_message in coperson_dict.values():
                coperson = CoPersonMessage.from_dict(person_message)
                if not coperson:
                    continue
                if not coperson.email_address:
                    continue

                for address in coperson.email_address:
                    if email == address.mail:
                        result.append(coperson)

        return result


class RegistryError(Exception):
    pass
