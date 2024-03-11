"""Tests for user directory."""
from datetime import datetime

import yaml
from users.authorizations import Authorizations
from users.nacc_directory import Credentials, PersonName, UserDirectoryEntry


# pylint: disable=(no-self-use,too-few-public-methods)
class TestDirectory:
    """Tests for UserDirectoryEntry."""

    def test_object(self):
        """Tests around creating objects."""
        entry = UserDirectoryEntry(
            org_name='the center',
            adcid=0,
            name=PersonName(first_name='chip', last_name='puppy'),
            email='chip@theorg.org',
            authorizations=Authorizations(study_id='adrc',
                                          submit=['form'],
                                          audit_data=True,
                                          approve_data=True,
                                          view_reports=True),
            credentials=Credentials(type='eppn', id='chip@theorg.org'),
            submit_time=datetime.strptime('2023-01-02 1:30', "%Y-%m-%d %H:%M"))
        assert entry.authorizations.audit_data

        entry2 = UserDirectoryEntry.create_from_record({
            "record_id":
            "1",
            "contact_company_name":
            "the center",
            "adresearchctr":
            "0",
            "firstname":
            "chip",
            "lastname":
            "puppy",
            "email":
            "chip@theorg.org",
            "flywheel_access_activities":
            "a,c,d,e",
            "fw_credential_type":
            "eppn",
            "fw_credential_id":
            "chip@theorg.org",
            "fw_cred_sub_time":
            "2023-01-02 1:30",
            "flywheel_access_information_complete":
            "2"
        })
        assert entry == entry2

        entry_yaml = yaml.safe_dump(entry.as_dict())

        entry_object = yaml.safe_load(entry_yaml)
        entry3 = UserDirectoryEntry.create(entry_object)
        assert entry == entry3
