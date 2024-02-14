"""Tests for UserDirectory class."""

import io
from csv import DictReader
from datetime import datetime
from typing import List, Literal, Optional

import yaml
from redcap.nacc_directory import (Authorizations, Credentials, PersonName,
                                   UserDirectory, UserDirectoryEntry)


def user_entry(email: str,
               name: Optional[PersonName] = None,
               user_id: Optional[str] = None,
               submit: Optional[List[Literal['form', 'image']]] = None,
               audit_data=False,
               approve_data=False,
               view_reports=False):
    """Creates a dummy UserDirectoryEntry object.

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

    authorizations = Authorizations(submit=submit if submit else [],
                                    audit_data=audit_data,
                                    approve_data=approve_data,
                                    view_reports=view_reports)
    dummytime = datetime(2023, 1, 1)
    return UserDirectoryEntry(org_name='dummy',
                              adcid=0,
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
        assert len(entries) == 1
        assert entries[0].email == 'bah@one.org'
        conflicts = directory.get_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0]['entries'][0]['email'] == 'cah@one.org'

    def test_id_id_conflict(self):
        """Test adding record with conflicting ids."""
        directory = UserDirectory()
        first_entry = user_entry(email='aah@two.org', user_id='1111@two.org')
        directory.add(first_entry)
        second_entry = user_entry(email='bah@two.org', user_id='1111@two.org')
        directory.add(second_entry)
        assert not directory.get_entries()
        conflicts = directory.get_conflicts()
        assert conflicts[0]['entries'][0]['email'] == 'aah@two.org'
        assert conflicts[0]['entries'][1]['email'] == 'bah@two.org'
        assert yaml.safe_dump(data=conflicts,
                              allow_unicode=True,
                              default_flow_style=False)

    def test_missing_id(self):
        """Test record with missing ID is not added."""
        directory = UserDirectory()
        no_id_entry = user_entry(email='bah@two.org', user_id='')
        directory.add(no_id_entry)
        assert not directory.get_entries()

    def test_conflict_from_create_from(self):
        """Test dumping conflicts."""
        input_csv = (
            "record_id,contact_company_name,adresearchctr,firstname,lastname,email,flywheel_access_activities,fw_credential_type,fw_credential_id,fw_cred_sub_time,flywheel_access_information_complete,fw_access_survey_link\n"
            "222,\"Beta University ADRC\",999,Alpha,Tau,alpha@beta.edu,\"a,b,c,d,e\",eppn,conflict@beta.edu,\"2023-08-16 07:33\",2,\"<a href=\"https://dummy.dummy.dummy\">Flywheel Access Information</a>\n"
            "333,\"Beta University ADRC\",999,Gamma,Zeta,gamma@beta.edu,\"a,b,c,d,e\",eppn,conflict@beta.edu,\"2023-08-16 07:45\",2,\"<a href=\"https://dummy.dummy.dummy\">Flywheel Access Information</a>"
        )
        reader = DictReader(io.StringIO(input_csv))
        directory = UserDirectory()
        for row in reader:
            print(row)
            entry = UserDirectoryEntry.create_from_record(row)
            assert entry
            directory.add(entry)

        conflicts = directory.get_conflicts()
        assert conflicts
        conflict_yaml = yaml.safe_dump(data=conflicts,
                                       allow_unicode=True,
                                       default_flow_style=False)
        assert 'id: conflict@beta.edu' in conflict_yaml, (
            "expecting conflicing ID in output")
