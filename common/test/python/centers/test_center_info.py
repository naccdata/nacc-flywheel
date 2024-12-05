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


# pylint: disable=(no-self-use)
class TestCenterInfo:
    """Tests for centers.nacc_group.CenterInfo."""

    def test_object(self):
        """Sanity check on object creation and properties."""
        center = CenterInfo(tags=['adcid-7'],
                            name="Alpha ADRC",
                            center_id='alpha-adrc',
                            adcid=7,
                            group='dummy-group')
        assert 'adcid-7' in center.tags
        assert center.name == "Alpha ADRC"
        assert center.active
        assert center.center_id == 'alpha-adrc'
        assert center.group == 'dummy-group'

    def test_create(self):
        """Check that model is created correctly from dict,
        and the equality matches.
        """
        center = CenterInfo(**{
            'tags': ['adcid-7'],
            'name': 'Alpha ADRC',
            'center-id': 'alpha-adrc',
            'adcid': 7,
            'is-active': True,
            'group': 'dummy-group'
        })
        center2 = CenterInfo(tags=['adcid-7'],
                             name="Alpha ADRC",
                             center_id='alpha-adrc',
                             adcid=7,
                             group='dummy-group')
        assert center == center2

    def test_invalid_creation(self):
        """Test invalid creation."""
        with pytest.raises(ValidationError):
            CenterInfo()

        with pytest.raises(ValidationError):
            CenterInfo(tags=['adcid-7'],
                       name="Alpha ADRC",
                       adcid=7,
                       group='dummy-group')

    def test_apply(self):
        """Test that visitor applied."""
        visitor = DummyVisitor()
        center = CenterInfo(tags=['adcid-1'],
                            name="Dummy CenterInfo",
                            center_id="dummy",
                            adcid=1,
                            group='dummy-group')
        center.apply(visitor)
        assert visitor.center_id == "dummy"

    def test_create_from_yaml(self):
        """Test creation from yaml."""
        center_yaml = ("adcid: 16\n"
                       "name: University of California, Davis\n"
                       "center-id: ucdavis\n"
                       "is-active: True\n"
                       "group: dummy-group")
        center_gen = yaml.safe_load_all(center_yaml)
        center = CenterInfo(**next(iter(center_gen)))
        center2 = CenterInfo(tags=['adcid-16'],
                             name="University of California, Davis",
                             center_id='ucdavis',
                             adcid=16,
                             group='dummy-group')
        assert center == center2
