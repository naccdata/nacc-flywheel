"""Tests for centers.center_info."""
import pytest
import yaml

from pydantic import ValidationError

from centers.center_info import CenterInfo
from projects.study import Study, StudyVisitor


class DummyVisitor(StudyVisitor):
    """Visitor for testing apply methods."""

    def __init__(self) -> None:
        self.center_id: Optional[str] = None
        self.project_name: Optional[str] = None
        self.datatype_name: Optional[str] = None

    def visit_center(self, center_id: str) -> None:
        self.center_id = center_id

    def visit_datatype(self, datatype: str):
        self.datatype_name = datatype

    def visit_study(self, study: Study) -> None:
        self.project_name = study.name

@pytest.fixture(scope='module')
def dummy_center():
    """Generate dummy center for general testing."""
    return CenterInfo(tags=['adcid-7'],
                      name="Alpha ADRC",
                      center_id='alpha-adrc',
                      adcid=7,
                      group='alpha-group')


# pylint: disable=(no-self-use)
class TestCenterInfo:
    """Tests for centers.nacc_group.CenterInfo."""

    def test_object(self, dummy_center):
        """Sanity check on object creation and properties."""
        assert 'adcid-7' in dummy_center.tags
        assert dummy_center.name == "Alpha ADRC"
        assert dummy_center.active
        assert dummy_center.center_id == 'alpha-adrc'
        assert dummy_center.group == 'alpha-group'

    def test_create(self, dummy_center):
        """Check that model is created correctly from dict,
        and the equality matches.
        """
        center = CenterInfo(**{
            'tags': ['adcid-7'],
            'name': 'Alpha ADRC',
            'center-id': 'alpha-adrc',
            'adcid': 7,
            'is-active': True,
            'group': 'alpha-group'
        })
        assert center == dummy_center

    def test_invalid_creation(self):
        """Test invalid creation."""
        with pytest.raises(ValidationError):
            CenterInfo()

        with pytest.raises(ValidationError):
            CenterInfo(tags=['adcid-7'],
                       name="Alpha ADRC",
                       adcid=7)

    def test_apply(self, dummy_center):
        """Test that visitor applied."""
        visitor = DummyVisitor()
        dummy_center.apply(visitor)
        assert visitor.center_id == "alpha-adrc"

    def test_create_from_yaml(self, dummy_center):
        """Test creation from yaml."""
        center_yaml = ("adcid: 7\n"
                       "name: Alpha ADRC\n"
                       "center-id: alpha-adrc\n"
                       "is-active: True\n"
                       "group: alpha-group")
        center_gen = yaml.safe_load_all(center_yaml)
        center = CenterInfo(**next(iter(center_gen)))
        assert center == dummy_center

    def test_repr(self, dummy_center):
        """Test representation."""
        assert repr(dummy_center) == (
            "Center(center_id=alpha-adrc, "
            "name=Alpha ADRC, "
            "group=alpha-group, "
            "adcid=7, "
            "active=True, "
            "tags=('adcid-7',)")
