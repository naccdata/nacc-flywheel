"""Classes for NACC directory user credentials."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Literal, NewType, Optional, Set

from pydantic import BaseModel, ValidationError
from users.authorizations import Authorizations

log = logging.getLogger(__name__)


class Credentials(BaseModel):
    """Type class for credentials."""
    type: str
    id: str


class PersonName(BaseModel):
    """Type class for a person's name."""
    first_name: str
    last_name: str


EntryDictType = NewType(
    'EntryDictType',
    Dict[str,
         str | int | PersonName | Authorizations | Credentials | datetime])


class UserDirectoryEntry(BaseModel):
    """A user entry from Flywheel access report of the NACC directory."""
    org_name: str
    adcid: int
    name: PersonName
    email: str
    authorizations: Authorizations
    credentials: Credentials
    submit_time: datetime

    @property
    def user_id(self) -> str:
        """The user ID for this directory entry."""
        return self.credentials.id

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
        return self.model_dump()  # type: ignore

    @classmethod
    def create(cls, entry: Dict[str, Any]) -> "UserDirectoryEntry":
        """Creates an object from a dictionary. Expects dictionary to match
        output of `as_dict`

        Args:
          entry: the dictionary for entry
        Returns:
          The dictionary object
        """
        try:
            return UserDirectoryEntry.model_validate(entry)
        except ValidationError as error:
            log.error("Error creating user entry from %s: %s", entry, error)
            raise UserFormatError(
                f"Error creating user entry: {error}") from error

    @classmethod
    def create_from_record(
            cls, record: Dict[str, Any]) -> Optional['UserDirectoryEntry']:
        """Creates a DirectoryEntry from a Flywheel Access report record from
        the NACC Directory in REDCap.

        Ignores records that are incomplete or unverified

        Args:
          record: a dictionary containing report record for user
        Returns:
          the dictionary entry for the record. None, if record is incomplete
        """
        if int(record["flywheel_access_information_complete"]) != 2:
            return None

        authorizations = Authorizations.create_from_record(
            record["flywheel_access_activities"])
        credentials = Credentials(type=record['fw_credential_type'],
                                  id=record['fw_credential_id'])
        name = PersonName(first_name=record['firstname'],
                          last_name=record['lastname'])

        org_name = record['contact_company_name']
        center_id = record['adresearchctr']
        if not center_id.isdigit():
            center_id = '-1'
            if org_name.lower() == 'nacc':
                center_id = '0'

        return UserDirectoryEntry(org_name=org_name,
                                  adcid=int(center_id),
                                  name=name,
                                  email=record['email'].lower(),
                                  credentials=credentials,
                                  submit_time=datetime.strptime(
                                      record['fw_cred_sub_time'],
                                      "%Y-%m-%d %H:%M"),
                                  authorizations=authorizations)


class UserFormatError(Exception):
    """Exception class for user format errors."""


class DirectoryConflict(BaseModel):
    """Entries with conflicting user_id and/or emails."""
    user_id: str
    conflict_type: Literal['email', 'identifier']
    entries: List[EntryDictType]


class UserDirectory:
    """Collection of UserDirectoryEntry objects.

    NACC directory identifies entries by name and email.
    """

    def __init__(self) -> None:
        """Initializes a user directory."""
        self.__email_map: Dict[str, UserDirectoryEntry] = {}
        self.__conflict_set: Set[str] = set()
        self.__id_map: Dict[str, List[str]] = defaultdict(list)

    def add(self, entry: UserDirectoryEntry) -> None:
        """Adds a directory entry to the user directory.

        Ignores the entry if it has no ID, or another entry already has the
        email address.

        Args:
          entry: the directory entry
        """
        # check that entry has an ID
        if not entry.user_id:
            return

        # check that doesn't have duplicate email
        # (REDCap directory uses email as key)
        if self.has_entry_email(entry.email):
            return

        self.__email_map[entry.email] = entry

        # check that someone else's ID is not this entry's email
        if entry.email in self.__id_map:
            # other entry is in conflict
            for other_email in self.__id_map[entry.email]:
                self.__conflict_set.add(other_email)
            return

        if entry.email == entry.user_id:
            return

        # check that ID is not someone else's email
        if self.has_entry_email(entry.user_id):
            # new entry is in conflict
            self.__conflict_set.add(entry.email)
            return

        self.__id_map[entry.user_id].append(entry.email)

    def get_entries(self) -> List[UserDirectoryEntry]:
        """Returns the list of entries with no conflicts between email address
        and user IDs.

        Returns:
          List of UserDirectoryEntry with no email/ID conflicts
        """
        id_conflicts = set()
        for email_list in self.__id_map.values():
            if len(email_list) > 1:
                for email in email_list:
                    id_conflicts.add(email)

        non_conflicts = {
            email
            for email in self.__email_map
            if email not in self.__conflict_set and email not in id_conflicts
        }

        entries = self.__get_entry_list(non_conflicts)
        return entries

    def __get_entry_list(
            self, email_list: Iterable[str]) -> List[UserDirectoryEntry]:
        """Returns the list of entries for the emails in the email list.

        Args:
          email_list: list of email addresses
        Returns:
          Directory entries for the email addresses
        """
        return [
            entry
            for entry in [self.__email_map.get(email) for email in email_list]
            if entry
        ]

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Returns the list of conflicting directory entries.

        Conflicts occur
        - if two entries have the same ID, or
        - if an entry has an ID that is the email of another entry.

        Return:
          List of DirectoryConflict objects for entries with conflicting IDs
        """
        conflicts = []
        for user_id, email_list in self.__id_map.items():
            if len(email_list) > 1:
                log.warning("Conflict for user id %s", user_id)
                conflicts.append(
                    DirectoryConflict(
                        user_id=user_id,
                        entries=[
                            entry.as_dict()
                            for entry in self.__get_entry_list(email_list)
                        ],
                        conflict_type='identifier').model_dump())
        for entry in self.__email_map.values():
            if entry.email in self.__conflict_set:
                log.warning("Conflict for email %s", entry.email)
                conflicts.append(
                    DirectoryConflict(user_id=entry.credentials.id,
                                      entries=[entry.as_dict()],
                                      conflict_type='email').model_dump())

        return conflicts

    def has_entry_email(self, email):
        """Determines whether directory has an entry for the email address.

        Args:
          email: the email address
        Returns:
          True if there is an entry with this address, False otherwise
        """
        return email in self.__email_map
