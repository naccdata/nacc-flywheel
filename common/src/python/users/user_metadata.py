"""Defines an adaptor class to manage registry person metadata that is not
available through the CoManage API."""

from datetime import datetime
from typing import Dict, Optional

from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from pydantic import AliasGenerator, BaseModel, ConfigDict, ValidationError
from serialization.case import kebab_case


class PersonInfo(BaseModel):
    """Tracks additional information for person with email."""
    model_config = ConfigDict(populate_by_name=True,
                              alias_generator=AliasGenerator(alias=kebab_case))
    email: str
    creation_date: datetime


class RegistryMetadata(BaseModel):
    """Metadata for registry."""
    registered: Dict[str, PersonInfo]

    def add(self, person: PersonInfo) -> None:
        """Adds the person info to the metadata.

        Args:
          person: the person info object
        """
        self.registered[person.email] = person

    def get(self, email: str) -> Optional[PersonInfo]:
        """Gets the person info for the email.

        Args:
          email: the email for the person
        Returns:
          the person info object if exists. None otherwise.
        """
        return self.registered.get(email, None)


class RegistryMetadataManager:
    """Manages RegistryMetadata as info objects attached to a project.

    For NACC this should be nacc/project-admin
    """

    def __init__(self, admin_project: ProjectAdaptor) -> None:
        self.__project = admin_project
        self.__registry_info = None

    def add(self, person: PersonInfo) -> None:
        """Adds the person info object to the registry metadata.

        Args:
          person_info: the person info object
        """
        if not self.__registry_info:
            self.__registry_info = self.__get_metadata()

        self.__registry_info.add(person)
        self.__set_metadata(self.__registry_info)

    def get(self, email: str) -> Optional[PersonInfo]:
        """Gets the PersonInfo object for the email.

        Args:
          email: the email address
        Returns:
          the PersonInfo object with the email. Otherwise, None.
        """
        if not self.__registry_info:
            self.__registry_info = self.__get_metadata()

        return self.__registry_info.get(email=email)

    def __get_metadata(self) -> RegistryMetadata:
        """Gets the registry metadata from the project info.

        Returns:
          the registry metadata object
        Raises:
          MetadataError if the registry metadata has unexpected format
        """

        info = self.__project.get_info()
        if not info:
            return RegistryMetadata(registered={})

        if 'registered' not in info:
            return RegistryMetadata(registered={})

        try:
            return RegistryMetadata.model_validate(info)
        except ValidationError as error:
            raise MetadataError(f"Info in {self.__project.label}"
                                " does not match registry format") from error

    def __set_metadata(self, registry_info: RegistryMetadata) -> None:
        """Sets the registry metadata in the project info.

        Args:
          registry_info: the registry metadata
        """
        self.__project.update_info(
            registry_info.model_dump(by_alias=True, exclude_none=True))


class MetadataError(Exception):
    """Exception for mismatch in expected project info."""
