"""Tests for projects.*"""
from typing import Optional

import pytest
import yaml
from projects.study import Center, Study, StudyVisitor


class DummyVisitor(StudyVisitor):
    """Visitor for testing apply methods."""

    def __init__(self) -> None:
        self.center_name: Optional[str] = None
        self.project_name: Optional[str] = None
        self.datatype_name: Optional[str] = None

    def visit_center(self, center: Center) -> None:
        self.center_name = center.name

    def visit_datatype(self, datatype: str):
        self.datatype_name = datatype

    def visit_study(self, study: Study) -> None:
        self.project_name = study.name


# pylint: disable=(no-self-use)
class TestCenter:
    """Tests for projects.Center."""

    def test_object(self):
        """Sanity check on object creation and properties."""
        center = Center(tags=['adcid-7'],
                        name="Alpha ADRC",
                        center_id='alpha-adrc',
                        adcid=7)
        assert 'adcid-7' in center.tags
        assert center.name == "Alpha ADRC"
        assert center.is_active()
        assert center.center_id == 'alpha-adrc'

    def test_create(self):
        """Check that create method creates object correctly."""
        center = Center.create({
            'tags': ['adcid-7'],
            'name': 'Alpha ADRC',
            'center-id': 'alpha-adrc',
            'adcid': 7,
            'is-active': True
        })
        center2 = Center(tags=['adcid-7'],
                         name="Alpha ADRC",
                         center_id='alpha-adrc',
                         adcid=7)
        assert center == center2

        with pytest.raises(KeyError):
            Center.create({})

    def test_apply(self):
        """Test that visitor applied."""
        visitor = DummyVisitor()
        center = Center(tags=['adcid-1'],
                        name="Dummy Center",
                        center_id="dummy",
                        adcid=1)
        center.apply(visitor)
        assert visitor.center_name == "Dummy Center"

    def test_create_from_yaml(self):
        center_yaml = ("adcid: 16\n"
                       "name: University of California, Davis\n"
                       "center-id: ucdavis\n"
                       "is-active: True")
        center_gen = yaml.safe_load_all(center_yaml)
        center = Center.create(next(iter(center_gen)))
        center2 = Center(tags=['adcid-16'],
                         name="University of California, Davis",
                         center_id='ucdavis',
                         adcid=16)
        assert center == center2


class TestStudy:
    """Tests for Project class."""

    def test_object(self):
        """Tests for object creation."""
        project = Study(name="Project Alpha",
                        study_id='project-alpha',
                        centers=['ac'],
                        datatypes=['dicom'],
                        mode='aggregation',
                        published=True,
                        primary=True)
        assert project.study_id == "project-alpha"
        assert project.centers == ['ac']
        assert project.datatypes == ['dicom']
        assert project.mode == 'aggregation'
        assert project.is_published()
        assert project.is_primary()

        project2 = Study.create({
            'study': 'Project Alpha',
            'study-id': 'project-alpha',
            'centers': ['ac'],
            'datatypes': ['dicom'],
            'mode': 'aggregation',
            'published': True,
            'primary': True
        })
        assert project == project2

        with pytest.raises(KeyError):
            Study.create({})

    def test_apply(self):
        """Test project apply method."""
        visitor = DummyVisitor()
        project = Study(name='Project Beta',
                        study_id='beta',
                        centers=[],
                        datatypes=[],
                        mode='aggregation',
                        published=True)
        project.apply(visitor)
        assert visitor.project_name == 'Project Beta'
