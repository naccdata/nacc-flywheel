"""Classes for representing NACC projects."""
import re
from abc import ABC, abstractmethod
from typing import Any, List, Mapping


def convert_to_slug(name: str) -> str:
    """Converts center name to a slug for use as a human-readable ID.

    Removes non-word, non-whitespace characters, replaces runs of
    whitespace with a single hyphen, and returns in lower case.

    Args:
      name: the name of the center

    Returns:
      The transformed name.
    """
    name = re.sub(r"[/]", ' ', name)
    name = re.sub(r"[^\w\s]", '', name)
    name = re.sub(r"\s+", '-', name)
    return name.lower()


class ProjectVisitor(ABC):
    """Abstract class for a visitor object for projects."""

    @abstractmethod
    def visit_project(self, project: "Project") -> None:
        """Method to visit the given project.

        Args:
          project: the project to visit.
        """

    @abstractmethod
    def visit_center(self, center: "Center") -> None:
        """Method to visit the given center within a project.

        Args:
          center: the center to visit
        """

    @abstractmethod
    def visit_datatype(self, datatype: str):
        """Method to visit the given datatype within a project.

        Args:
          datatype: the name of the datatype within a project.
        """


class Center:
    """Represents a center with data managed at NACC."""

    def __init__(self,
                 *,
                 adcid: int,
                 name: str,
                 center_id: str,
                 active: bool = True) -> None:
        self._adcid = adcid
        self._name = name
        self._active = active
        self._center_id = center_id

    def __repr__(self) -> str:
        return (f"Center(adcid={self.adcid}, "
                f"center_id={self.center_id}, "
                f"name={self.name}, "
                f"active={self.is_active()})")

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Center):
            return False
        return (self._adcid == __o._adcid and self._active == __o._active
                and self.name == __o.name)

    @property
    def name(self) -> str:
        """Center name property."""
        return self._name

    def is_active(self) -> bool:
        """Indicates whether the center is active."""
        return self._active

    @property
    def adcid(self) -> int:
        """Center ADC ID property."""
        return self._adcid

    @property
    def center_id(self):
        """Center text ID property."""
        return self._center_id

    def apply(self, visitor):
        """Applies visitor to this Center."""
        visitor.visit_center(self)

    @classmethod
    def create(cls, center: dict) -> "Center":
        """Creates a Center from the given dictionary."""
        return Center(adcid=center['adc-id'],
                      name=center['name'],
                      center_id=center['center-id'],
                      active=center['is-active'])


class Project:
    """Represents a Project with data managed at NACC."""

    def __init__(self,
                 *,
                 name: str,
                 project_id: str,
                 centers: List[Center],
                 datatypes: List[str],
                 published: bool = False,
                 primary: bool = False) -> None:
        self._name = name
        self._centers = centers
        self._datatypes = datatypes
        self._published = published
        self._primary = primary
        self._project_id = project_id

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Project):
            return False
        return (__o.name == self._name and __o._centers == self._centers
                and __o._datatypes == self._datatypes
                and __o._published == self._published
                and __o._primary == self._primary)

    def __repr__(self) -> str:
        return ("Project("
                f"name={self._name},"
                f"project_id={self._project_id},"
                f"centers={self._centers},"
                f"datatypes={self._datatypes},"
                f"published={self._published},"
                f"primary={self._primary}"
                ")")

    @property
    def project_id(self) -> str:
        """Project ID property."""
        return self._project_id

    @property
    def name(self) -> str:
        """Project Name property."""
        return self._name

    @property
    def centers(self) -> List[Center]:
        """Project centers property."""
        return self._centers

    @property
    def datatypes(self) -> List[str]:
        """Project datatypes property."""
        return self._datatypes

    def is_published(self) -> bool:
        """Project published predicate."""
        return self._published

    def is_primary(self) -> bool:
        """Predicate to indicate whether is the main project of coordinating
        center."""
        return self._primary

    def apply(self, visitor) -> None:
        """Apply visitor to this Project."""
        visitor.visit_project(self)

    @classmethod
    def create(cls, project: Mapping[str, Any]) -> "Project":
        """Create Project from given mapping."""
        primary_project = False
        if 'primary' in project:
            primary_project = project['primary']

        return Project(
            name=project['project'],
            project_id=project['project-id'],
            centers=[Center.create(center) for center in project['centers']],
            datatypes=project['datatypes'],
            published=project['published'],
            primary=primary_project)
