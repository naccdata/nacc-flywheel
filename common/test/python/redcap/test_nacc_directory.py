"""Tests for UserDirectory class."""

from datetime import datetime
from typing import Optional

from redcap.nacc_directory import (Authorizations, Credentials, PersonName,
                                   UserDirectory, UserDirectoryEntry)


def user_entry(email: str,
               name: Optional[PersonName] = None,
               user_id: Optional[str] = None):
    """Creates a dummy UserDirectoryEntry object.

    Args:
      email: email address to use in entry
      name: name to use in entry
      user_id: user ID to use
    Returns:
      Dummy user entry object with specific parameters set
    """
    if not user_id:
        user_id = email
    if not name:
        name = PersonName(first_name='dummy', last_name='name')
    authorizations = Authorizations(submit=[],
                                    audit_data=False,
                                    approve_data=False,
                                    view_reports=False)
    dummytime = datetime(2023, 1, 1)
    return UserDirectoryEntry(org_name='dummy',
                              center_id=0,
                              name=name,
                              email=email,
                              authorizations=authorizations,
                              credentials=Credentials(type='orcid',
                                                      id=user_id),
                              submit_time=dummytime)


# pylint: disable=no-self-use
class TestNACCDirectory:
    """Tests for UserDirectory."""

    def test_empty(self):
        """Test empty directory."""
        directory = UserDirectory()
        assert not directory.has_entry_email('email@email.org')
        non_conflicts = directory.get_entries()
        assert not non_conflicts
        conflicts = directory.get_conflicts()
        assert not conflicts

    def test_add_to_empty(self):
        """Test adding entry to empty directory."""
        new_entry = user_entry('bah@one.org')
        directory = UserDirectory()
        directory.add(new_entry)
        entries = directory.get_entries()
        assert entries
        assert entries[0].email == 'bah@one.org'
        conflicts = directory.get_conflicts()
        assert not conflicts

    def test_add_twice(self):
        """Test adding two records with same email to directory."""
        first_entry = user_entry('bah@one.org')
        second_entry = user_entry(
            'bah@one.org', PersonName(first_name='bah', last_name='bah'))
        assert second_entry.name, 'Name is set in second entry'
        directory = UserDirectory()
        directory.add(first_entry)
        entries1 = directory.get_entries()
        assert len(entries1) == 1
        assert entries1[0].email == 'bah@one.org'
        directory.add(second_entry)
        entries2 = directory.get_entries()
        assert entries1 == entries2
        assert not directory.get_conflicts()

    def test_add_id_email_conflict(self):
        """Test adding records with conflicting id to directory."""
        directory = UserDirectory()
        first_entry = user_entry(email='bah@one.org')
        directory.add(first_entry)
        second_entry = user_entry(email='cah@one.org', user_id='bah@one.org')
        directory.add(second_entry)
        entries = directory.get_entries()
        assert not entries
        conflicts = directory.get_conflicts()
        assert len(conflicts) == 1
