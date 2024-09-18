"""Tests for UserDirectory class."""

from typing import List, Optional

from users.authorizations import DatatypeNameType
from users.nacc_directory import (
    ActiveUserEntry,
    Authorizations,
    PersonName,
    UserDirectory,
)


# pylint: disable=too-many-arguments
def user_entry(email: str,
               name: Optional[PersonName] = None,
               user_id: Optional[str] = None,
               submit: Optional[List[DatatypeNameType]] = None,
               audit_data=False,
               approve_data=False,
               view_reports=False):
    """Creates a dummy UserEntry object.

    Args:
      email: email address to use in entry
      name: name to use in entry
      user_id: user ID to use
      submit: list of submission authorizations
    Returns:
      Dummy user entry object with specific parameters set
    """
    if user_id is None:
        user_id = email
    if not name:
        name = PersonName(first_name='dummy', last_name='name')

    authorizations = Authorizations(study_id='dummy',
                                    submit=submit if submit else [],
                                    audit_data=audit_data,
                                    approve_data=approve_data,
                                    view_reports=view_reports)
    return ActiveUserEntry(org_name='dummy',
                           adcid=0,
                           name=name,
                           email=email,
                           authorizations=authorizations,
                           active=True,
                           auth_email=email)


# pylint: disable=no-self-use
class TestNACCDirectory:
    """Tests for UserDirectory."""

    def test_empty(self):
        """Test empty directory."""
        directory = UserDirectory()
        assert not directory.has_entry_email('email@email.org')
        entries = directory.get_entries()
        assert not entries

    def test_add_to_empty(self):
        """Test adding entry to empty directory."""
        new_entry = user_entry('bah@one.org')
        directory = UserDirectory()
        directory.add(new_entry)
        entries = directory.get_entries()
        assert entries
        assert entries[0].email == 'bah@one.org'

    def test_add_twice(self):
        """Test adding two records with same email to directory."""
        common_email = 'bah@one.org'
        first_entry = user_entry(common_email)
        second_entry = user_entry(
            common_email, PersonName(first_name='bah', last_name='bah'))
        assert second_entry.name, 'Name is set in second entry'
        directory = UserDirectory()
        directory.add(first_entry)
        assert directory.has_entry_email(common_email)
        entries1 = directory.get_entries()
        assert len(entries1) == 1
        assert entries1[0].email == common_email
