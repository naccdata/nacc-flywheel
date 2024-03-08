"""Tests for authorization module."""

import pytest
import yaml
from pydantic import ValidationError
from users.authorizations import AuthMap, Authorizations


@pytest.fixture
def empty_auth():
    yield Authorizations(study_id='dummy',
                         submit=[],
                         audit_data=False,
                         approve_data=False,
                         view_reports=False)


@pytest.fixture
def auth_map_alpha():
    auth_map = AuthMap(
        project_authorizations={
            'accepted': {
                'approve-data': 'read-only',
                'audit-data': 'read-only',
                'view-reports': 'read-only',
                'submit-form': 'read-only',
                'submit-image': 'read-only'
            },
            'ingest-form': {
                'approve-data': 'read-only',
                'audit-data': 'read-only',
                'view-reports': 'read-only',
                'submit-form': 'upload'
            },
            'sandbox-form': {
                'submit-form': 'upload'
            }
        })
    yield auth_map


@pytest.fixture
def auth_map_alpha_yaml():
    yield ('---\n'
           'accepted:\n'
           '  approve-data: read-only\n'
           '  audit-data: read-only\n'
           '  view-reports: read-only\n'
           '  submit-form: read-only\n'
           '  submit-image: read-only\n'
           'ingest-form:\n'
           '  approve-data: read-only\n'
           '  audit-data: read-only\n'
           '  view-reports: read-only\n'
           '  submit-form: upload\n'
           'sandbox-form:\n'
           '  submit-form: upload\n')


@pytest.fixture
def alpha_authorizations():
    yield Authorizations(study_id='dummy',
                         submit=['form'],
                         audit_data=True,
                         approve_data=True,
                         view_reports=True)


@pytest.fixture
def beta_authorizations():
    yield Authorizations(study_id='dummy',
                         submit=['dicom'],
                         audit_data=False,
                         approve_data=True,
                         view_reports=False)


class TestAuthMap:
    """Tests for AuthMap."""

    def test_empty_map(self, empty_auth):
        auth_map = AuthMap(project_authorizations={})
        assert auth_map.get('dummy', empty_auth) == set()

    def test_authmap(self, alpha_authorizations, beta_authorizations,
                     auth_map_alpha):
        assert auth_map_alpha.get('accepted',
                                  alpha_authorizations) == {'read-only'}
        assert auth_map_alpha.get(
            'ingest-form', alpha_authorizations) == {'read-only', 'upload'}
        assert auth_map_alpha.get('ingest-image',
                                  alpha_authorizations) == set()
        assert auth_map_alpha.get('sandbox-form',
                                  alpha_authorizations) == {'upload'}

        assert auth_map_alpha.get('accepted',
                                  beta_authorizations) == {'read-only'}
        assert auth_map_alpha.get('ingest-form',
                                  beta_authorizations) == {'read-only'}
        assert auth_map_alpha.get('ingest-image', beta_authorizations) == set()
        assert auth_map_alpha.get('sandbox-form', beta_authorizations) == set()

    def test_yaml(self, auth_map_alpha, auth_map_alpha_yaml):
        yaml_object = yaml.safe_load(auth_map_alpha_yaml)
        load_map = AuthMap(project_authorizations=yaml_object)
        assert load_map == auth_map_alpha
