"""Classes for NACC directory user credentials."""

import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, NewType, Optional, Set, TypedDict

log = logging.getLogger(__name__)


class Authorizations(TypedDict):
    """Type class for authorizations."""
    submit: List[str]
    audit_data: bool
    approve_data: bool
    view_reports: bool


class Credentials(TypedDict):
    """Type class for credentials."""
    type: str
    id: str


class PersonName(TypedDict):
    """Type class for a person's name."""
    first_name: str
    last_name: str


EntryDictType = NewType(
    'EntryDictType',
    Dict[str,
         str | int | PersonName | Authorizations | Credentials | datetime])


class UserDirectoryEntry:
    """A user entry from Flywheel access report of the NACC directory."""

    def __init__(self, *, org_name: str, center_id: int, name: PersonName,
                 email: str, authorizations: Authorizations,
                 credentials: Credentials, submit_time: datetime) -> None:
        self.__org_name = org_name
        self.__center_id = center_id
        self.__name = name
        self.__email = email
        self.__authorizations = authorizations
        self.__credentials = credentials
        self.__submit_time = submit_time

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, UserDirectoryEntry):
            return False

        return (self.__org_name == __value.org_name
                and self.__center_id == __value.center_id
                and self.__name == __value.name
                and self.__email == __value.email
                and self.__authorizations == __value.authorizations
                and self.__credentials == __value.credentials)

    @property
    def org_name(self) -> str:
        """The name of the user's organization."""
        return self.__org_name

    @property
    def center_id(self) -> int:
        """The ID for the user's center."""
        return self.__center_id

    @property
    def name(self) -> PersonName:
        """The user's name."""
        return self.__name

    @property
    def email(self) -> str:
        """The user's organizational email."""
        return self.__email

    @property
    def authorizations(self) -> Authorizations:
        """The users authorizations for data access."""
        return self.__authorizations

    @property
    def credentials(self) -> Credentials:
        """The users CILogon credentials."""
        return self.__credentials

    @property
    def submit_time(self) -> datetime:
        """The submission time for credentials."""
        return self.__submit_time

    def as_dict(self) -> EntryDictType:
        """Builds a dictionary for this directory entry.

        Returns:
          A dictionary with values of this entry
        """
        result: EntryDictType = {}  # type: ignore
        result['org_name'] = self.__org_name
        result['center_id'] = self.__center_id
        result['name'] = self.__name
        result['email'] = self.__email
        result['authorizations'] = self.__authorizations
        result['credentials'] = self.__credentials
        result['submit_time'] = self.__submit_time
        return result

    @classmethod
    def create(cls, entry: Dict[str, Any]) -> "UserDirectoryEntry":
        """Creates an object from a dictionary. Expects dictionary to match
        output of `as_dict`

        Args:
          entry: the dictionary for entry
        Returns:
          The dictionary object
        """
        return UserDirectoryEntry(org_name=entry['org_name'],
                                  center_id=entry['center_id'],
                                  name=entry['name'],
                                  email=entry['email'],
                                  authorizations=entry['authorizations'],
                                  credentials=entry['credentials'],
                                  submit_time=entry['submit_time'])

    @classmethod
    def create_from_record(
            cls, record: Dict[str, str]) -> Optional['UserDirectoryEntry']:
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

        modalities = []
        activities = record["flywheel_access_activities"]
        if 'a' in activities:
            modalities.append('form')
        if 'b' in activities:
            modalities.append('image')

        authorizations: Authorizations = {
            "submit": modalities,
            "audit_data": bool('c' in activities),
            "approve_data": bool('d' in activities),
            "view_reports": bool('e' in activities)
        }

        credentials: Credentials = {
            "type": record['fw_credential_type'],
            "id": record['fw_credential_id']
        }

        name: PersonName = {
            "first_name": record['firstname'],
            "last_name": record['lastname']
        }

        org_name = record['contact_company_name']
        center_id = record['adresearchctr']
        if not center_id.isdigit():
            center_id = '-1'
            if org_name.lower() == 'nacc':
                center_id = '0'

        return UserDirectoryEntry(org_name=org_name,
                                  center_id=int(center_id),
                                  name=name,
                                  email=record['email'].lower(),
                                  credentials=credentials,
                                  submit_time=datetime.strptime(
                                      record['fw_cred_sub_time'],
                                      "%Y-%m-%d %H:%M"),
                                  authorizations=authorizations)


class ConflictEnum(Enum):
    """Enumerated type for directory conflicts."""
    EMAIL = 1
    IDENTIFIER = 2


class DirectoryConflict(TypedDict):
    """Entries with conflicting user_id and/or emails."""
    user_id: str
    conflict_type: ConflictEnum
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
        if not entry.credentials['id']:
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

        if entry.email == entry.credentials['id']:
            return

        # check that ID is not someone else's email
        if self.has_entry_email(entry.credentials['id']):
            # new entry is in conflict
            self.__conflict_set.add(entry.email)
            return

        self.__id_map[entry.credentials['id']].append(entry.email)

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

    def get_conflicts(self) -> List[DirectoryConflict]:
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
                        conflict_type=ConflictEnum.IDENTIFIER))
        for entry in self.__email_map.values():
            if entry.email in self.__conflict_set:
                log.warning("Conflict for email %s", entry.email)
                conflicts.append(
                    DirectoryConflict(user_id=entry.credentials['id'],
                                      entries=[entry.as_dict()],
                                      conflict_type=ConflictEnum.EMAIL))

        return conflicts

    def has_entry_email(self, email):
        """Determines whether directory has an entry for the email address.

        Args:
          email: the email address
        Returns:
          True if there is an entry with this address, False otherwise
        """
        return email in self.__email_map
