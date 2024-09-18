"""Defines repository as interface to user registry."""
from datetime import datetime
from typing import List, Optional

from coreapi_client.api.default_api import DefaultApi
from coreapi_client.exceptions import ApiException
from coreapi_client.models.co_person import CoPerson
from coreapi_client.models.co_person_message import CoPersonMessage
from coreapi_client.models.co_person_role import CoPersonRole
from coreapi_client.models.email_address import EmailAddress
from coreapi_client.models.get_co_person200_response import GetCoPerson200Response
from coreapi_client.models.identifier import Identifier
from coreapi_client.models.name import Name


class RegistryPerson:
    """Wrapper for COManage CoPersonMessage object.

    Enables predicates needed for processing.
    """

    def __init__(self, coperson_message: CoPersonMessage) -> None:
        self.__coperson_message = coperson_message

    @classmethod
    def create(cls, *, firstname: str, lastname: str, email: str,
               coid: str) -> 'RegistryPerson':
        """Creates a RegistryPerson object with the name and email.

        Note: the coid must match that of the registry

        Args:
          firstname: the first (given) name of person
          lastname: the last (family) name of the person
          email: the email address of the person
          coid: the CO ID for the COManage registry
        Returns:
          the RegistryPerson with name and email
        """
        coperson = CoPerson(co_id=coid, status="A")
        email_address = EmailAddress(mail=email,
                                     type="official",
                                     verified=True)
        role = CoPersonRole(cou_id=None, affiliation="member", status="A")
        name = Name(given=firstname,
                    family=lastname,
                    type="official",
                    primary_name=True)
        return RegistryPerson(
            coperson_message=CoPersonMessage(CoPerson=coperson,
                                             EmailAddress=[email_address],
                                             CoPersonRole=[role],
                                             Name=[name]))

    def as_coperson_message(self) -> CoPersonMessage:
        return self.__coperson_message

    @property
    def creation_date(self) -> Optional[datetime]:
        """Returns the creation date for this person in the registry.

        Will be None for person that is created locally.

        Returns:
          the creation date for this person. None if not set.
        """
        if not self.__coperson_message.co_person:
            return None
        if not self.__coperson_message.co_person.meta:
            return None

        return self.__coperson_message.co_person.meta.created

    @property
    def email_address(self) -> Optional[List[EmailAddress]]:
        return self.__coperson_message.email_address

    def has_email(self, email: str) -> bool:
        """Indicates whether this person has the email address.

        Args:
          email: the email address
        Returns:
          True if this person has the email address. False, otherwise.
        """
        if not self.email_address:
            return False

        email_addresses = [
            address for address in self.email_address if email == address.mail
        ]
        if not email_addresses:
            return False

        return True

    def is_claimed(self) -> bool:
        """Indicates whether the CoPerson record is claimed.

        The record is claimed if there is an OrgIdentity that has an
        Identifier with type "oidcsub" and login True.

        Returns:
          True if the record has been claimed. False, otherwise.
        """
        if not self.__coperson_message.org_identity:
            return False

        for org_identity in self.__coperson_message.org_identity:
            if not org_identity.identifier:
                return False

            for identifier in org_identity.identifier:
                if identifier.type == "oidcsub" and identifier.login:
                    return True

        return False

    def registry_id(self) -> Optional[str]:
        """Returns the registry ID for the person.

        Returns:
          the registry ID for the person
        """
        if not self.__coperson_message.identifier:
            return None

        for identifier in self.__coperson_message.identifier:
            if identifier.type == "naccid" and identifier.status == "A":
                return identifier.identifier

        return None


class UserRegistry:
    """Repository class for COManage user registry."""

    def __init__(self, api_instance: DefaultApi, coid: int):
        self.__api_instance = api_instance
        self.__coid = coid

    @property
    def coid(self) -> int:
        """Returns the community ID (coid).

        Returns:
          the coid for the registry
        """
        return self.__coid

    def add(self, person: RegistryPerson) -> List[Identifier]:
        """Creates a CoPerson record in the registry with name and email.

        Args:
          person: the person to add
        Returns:
          a list of CoManage Identifier objects
        """

        try:
            return self.__api_instance.add_co_person(
                coid=self.__coid,
                co_person_message=person.as_coperson_message())
        except ApiException as error:
            raise RegistryError(f"API call failed: {error}") from error

    def list(self, email: str) -> List[RegistryPerson]:
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
                raise RegistryError(f"API call failed: {error}") from error

            person_list = self.__parse_response(response)

            read_length = len(person_list)
            page_index += 1

            for person in person_list:
                if person.has_email(email):
                    result.append(person)

        return result

    def __parse_response(
            self, response: GetCoPerson200Response) -> List[RegistryPerson]:
        """Collects the CoPersonMessages from the response object and creates a
        list of RegistryPerson objects.

        The response object has the first person object in response.var_0 as a
        CoPersonMessage. If there are more person objects, they are in the
        additional_properties as dictionary objects and have to be loaded
        as CoPersonMessage objects using Pydantic model_validate.

        Args:
          the response object
        Returns:
          the list of registry person objects
        """
        person_list: List[RegistryPerson] = []
        if response.var_0:
            person_list.append(RegistryPerson(response.var_0))

        if response.additional_properties:
            for message_object in response.additional_properties.values():
                person_list.append(
                    RegistryPerson(
                        CoPersonMessage.model_validate(message_object)))

        return person_list


class RegistryError(Exception):
    pass
