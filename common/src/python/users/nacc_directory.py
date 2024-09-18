"""Classes for NACC directory user credentials."""

import logging
from typing import Any, Dict, List, Literal, NewType, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from users.authorizations import Authorizations

log = logging.getLogger(__name__)


class PersonName(BaseModel):
    """Type class for a person's name."""
    first_name: str
    last_name: str


EntryDictType = NewType('EntryDictType',
                        Dict[str, str | int | PersonName | Authorizations])


class UserEntry(BaseModel):
    """A base directory user entry."""
    model_config = ConfigDict(populate_by_name=True, extra='forbid')

    name: PersonName
    email: str
    auth_email: Optional[str]
    active: bool

    @property
    def first_name(self) -> str:
        """The first name for this directory entry."""
        return self.name.first_name

    @property
    def last_name(self) -> str:
        """The last name for this directory entry."""
        return self.name.last_name

    def as_dict(self) -> EntryDictType:
        """Builds a dictionary for this directory entry.

        Returns:
          A dictionary with values of this entry
        """
        return self.model_dump(serialize_as_any=True)  # type: ignore

    @classmethod
    def create(cls, entry: Dict[str, Any]) -> "UserEntry":
        """Creates an object from a dictionary. Expects dictionary to match
        output of `as_dict`

        Args:
          entry: the dictionary for entry
        Returns:
          The dictionary object
        """
        try:
            if entry.get('active'):
                return ActiveUserEntry.model_validate(entry)

            return UserEntry.model_validate(entry)
        except ValidationError as error:
            log.error("Error creating user entry from %s: %s", entry, error)
            raise UserFormatError(
                f"Error creating user entry: {error}") from error

    @classmethod
    def create_from_record(cls, record: Dict[str,
                                             Any]) -> Optional['UserEntry']:
        """Creates a UserEntry from a data platform authorization report record
        from the NACC Directory in REDCap.

        Creates a UserEntry object if the record is marked as archived.
        Otherwise, creates an ActiveUserEntry.
        Ignores records that have incomplete or unverified authorization emails.

        Args:
          record: a dictionary containing report record for user
        Returns:
          the dictionary entry for the record. None, if record is incomplete
        """

        name = PersonName(first_name=record['firstname'],
                          last_name=record['lastname'])
        email = record['email'].lower()
        auth_email = record['fw_email'] if record['fw_email'] else None

        if record['archive_contact'] == "1":
            return UserEntry(name=name,
                             email=email,
                             auth_email=auth_email,
                             active=False)

        if int(record["nacc_data_platform_access_information_complete"]) != 2:
            return None

        authorizations = Authorizations.create_from_record(
            record["flywheel_access_activities"])

        org_name = record['contact_company_name']
        center_id = record['adresearchctr']
        if not center_id.isdigit():
            center_id = '-1'
            if org_name.lower() == 'nacc':
                center_id = '0'

        return ActiveUserEntry(org_name=org_name,
                               adcid=int(center_id),
                               name=name,
                               email=email,
                               auth_email=auth_email,
                               authorizations=authorizations,
                               active=True)


class ActiveUserEntry(UserEntry):
    """A user entry from Flywheel access report of the NACC directory."""
    org_name: str
    adcid: int
    authorizations: Authorizations

    def register(self, registry_id: str) -> 'RegisteredUserEntry':
        """Adds the registry id to this user entry.

        Args:
          registry_id: the registry ID
        Returns:
          this object with the registry ID added
        """
        return RegisteredUserEntry(name=self.name,
                                   email=self.email,
                                   auth_email=self.auth_email,
                                   active=self.active,
                                   org_name=self.org_name,
                                   adcid=self.adcid,
                                   authorizations=self.authorizations,
                                   registry_id=registry_id)


class RegisteredUserEntry(ActiveUserEntry):
    registry_id: str

    @property
    def user_id(self) -> str:
        """The user ID for this directory entry."""
        return self.registry_id


class UserFormatError(Exception):
    """Exception class for user format errors."""


class DirectoryConflict(BaseModel):
    """Entries with conflicting user_id and/or emails."""
    user_id: str
    conflict_type: Literal['email', 'identifier']
    entries: List[EntryDictType]


class UserDirectory:
    """Collection of UserEntry objects.

    NACC directory identifies entries by name and email.
    """

    def __init__(self) -> None:
        """Initializes a user directory."""
        self.__email_map: Dict[str, UserEntry] = {}

    def add(self, entry: UserEntry) -> None:
        """Adds a directory entry to the user directory.

        Args:
          entry: the directory entry
        """
        self.__email_map[entry.email] = entry

    def get_entries(self) -> List[UserEntry]:
        """Returns the list of entries with no conflicts between email address
        and user IDs.

        Returns:
          List of UserEntry with no email/ID conflicts
        """
        return list(self.__email_map.values())

    def has_entry_email(self, email):
        """Determines whether directory has an entry for the email address.

        Args:
          email: the email address
        Returns:
          True if there is an entry with this address. False otherwise
        """
        return email in self.__email_map
