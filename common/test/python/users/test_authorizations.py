"""Tests for authorization module."""

import pytest
import yaml
from pydantic import ValidationError
from users.authorizations import AuthMap, Authorizations


@pytest.fixture
def empty_auth():
    """Empty authorizations."""
    yield Authorizations(study_id='dummy',
                         submit=[],
                         audit_data=False,
                         approve_data=False,
                         view_reports=False)


@pytest.fixture
def auth_map_alpha():
    """AuthMap object."""
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
    """AuthMap object in YAML format."""
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
    """Authorizations object."""
    yield Authorizations(study_id='dummy',
                         submit=['form'],
                         audit_data=True,
                         approve_data=True,
                         view_reports=True)


@pytest.fixture
def beta_authorizations():
    """Authorizations object."""
    yield Authorizations(study_id='dummy',
                         submit=['dicom'],
                         audit_data=False,
                         approve_data=True,
                         view_reports=False)


class TestAuthMap:
    """Tests for AuthMap."""

    # pylint: disable=(redefined-outer-name,no-self-use)
    def test_empty_map(self, empty_auth: Authorizations):
        """Test empty map."""
        auth_map = AuthMap(project_authorizations={})
        assert auth_map.get(project_id='dummy',
                            authorizations=empty_auth) == set()

    # pylint: disable=(redefined-outer-name,no-self-use)
    def test_authmap(self, alpha_authorizations: Authorizations,
                     beta_authorizations: Authorizations,
                     auth_map_alpha: AuthMap):
        """Test authmap."""
        assert auth_map_alpha.get(project_id='accepted',
                                  authorizations=alpha_authorizations) == {
                                      'read-only'
                                  }
        assert auth_map_alpha.get(project_id='ingest-form',
                                  authorizations=alpha_authorizations) == {
                                      'read-only', 'upload'
                                  }
        assert auth_map_alpha.get(
            project_id='ingest-image',
            authorizations=alpha_authorizations) == set()
        assert auth_map_alpha.get(project_id='sandbox-form',
                                  authorizations=alpha_authorizations) == {
                                      'upload'
                                  }

        assert auth_map_alpha.get(project_id='accepted',
                                  authorizations=beta_authorizations) == {
                                      'read-only'
                                  }
        assert auth_map_alpha.get(project_id='ingest-form',
                                  authorizations=beta_authorizations) == {
                                      'read-only'
                                  }
        assert auth_map_alpha.get(project_id='ingest-image',
                                  authorizations=beta_authorizations) == set()
        assert auth_map_alpha.get(project_id='sandbox-form',
                                  authorizations=beta_authorizations) == set()

    # pylint: disable=(redefined-outer-name,no-self-use)
    def test_yaml(self, auth_map_alpha: AuthMap, auth_map_alpha_yaml: str):
        """Test YAML conversion."""
        yaml_object = yaml.safe_load(auth_map_alpha_yaml)
        load_map = AuthMap(project_authorizations=yaml_object)
        assert load_map == auth_map_alpha

        yaml_list = yaml.safe_load("---\n- blah\n- blah\n")
        with pytest.raises(ValidationError):
            AuthMap(project_authorizations=yaml_list)
