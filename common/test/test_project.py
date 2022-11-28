"""Tests for projects.*"""
from projects.project import Center, Project, ProjectVisitor


class DummyVisitor(ProjectVisitor):
    """Visitor for testing apply methods."""

    def __init__(self) -> None:
        self.center_name = None

    def visit_center(self, center: Center) -> None:
        self.center_name = center.name

    def visit_datatype(self, datatype: str):
        return

    def visit_project(self, project: Project) -> None:
        return


# pylint: disable=(no-self-use)
class TestCenter:
    """Tests for projects.Center."""

    def test_object(self):
        """Sanity check on object creation and properties."""
        center = Center(adcid=7, name="Alpha ADRC")
        assert center.adcid == 7
        assert center.name == "Alpha ADRC"
        assert center.is_active()
        assert center.center_id == 'alpha-adrc'

    def test_create(self):
        """Check that create method creates object correctly."""
        center = Center.create({
            'adc-id': 7,
            'name': "Alpha ADRC",
            'is-active': True
        })
        center2 = Center(adcid=7, name="Alpha ADRC")
        assert center == center2

    def test_apply(self):
        """Test that visitor applied."""
        visitor = DummyVisitor()
        center = Center(adcid=1, name="Dummy Center")
        center.apply(visitor)
        assert visitor.center_name == "Dummy Center"
