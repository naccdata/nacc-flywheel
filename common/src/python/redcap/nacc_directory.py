"""Classes for NACC directory user credentials."""

from datetime import datetime
from typing import Dict, List, Optional, TypedDict


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


class UserDirectoryEntry:
    """A user entry from Flywheel access report of the NACC directory."""

    def __init__(self, *, org_name: str, center_id: int, name: PersonName,
                 email: str, authorizations: Authorizations,
                 credentials: Credentials, submit_time) -> None:
        self.__org_name = org_name
        self.__center_id = center_id
        self.__name = name
        self.__email = email
        self.__authorizations = authorizations
        self.__credentials = credentials
        self.__submit_time = submit_time

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
    def credential(self) -> Credentials:
        """The users CILogon credentials."""
        return self.__credentials

    @property
    def submit_time(self) -> datetime:
        """The submission time for credentials."""
        return self.__submit_time

    @classmethod
    def create_from_record(
            cls, record: Dict[str, str]) -> Optional['UserDirectoryEntry']:
        """Creates a DirectoryEntry from a Flywheel Access report record from
        the NACC Directory in REDCap.

        Ignores records that are incomplete or unverified

        Args:
          record: a dictionary containing report record for user
        """
        if record["flywheel_access_information_complete"] != 2:
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

        return UserDirectoryEntry(org_name=record['contact_company_name'],
                              center_id=int(record['adresearchctr']),
                              name=name,
                              email=record['email'],
                              credentials=credentials,
                              submit_time=datetime.strptime(
                                  record['fw_cred_sub_time'],
                                  "%Y-%m-%d %H:%M"),
                              authorizations=authorizations)
