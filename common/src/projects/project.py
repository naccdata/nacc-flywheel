"""
Classes for representing NACC projects.
"""
from abc import ABC, abstractmethod
from typing import List, Mapping, TypeVar

from slugify import slugify


class ProjectVisitor(ABC):
    """
    Abstract class for a visitor object for projects.
    """
    @abstractmethod
    def visit_project(self, project: "Project") -> None:
        """
        Method to visit the given project.

        Args:
          project: the project to visit.
        """

    @abstractmethod
    def visit_center(self, center: "Center") -> None:
        """
        Method to visit the given center within a project.

        Args:
          center: the center to visit
        """

    @abstractmethod
    def visit_datatype(self, datatype: str):
        """
        Method to visit the given datatype within a project.

        Args:
          datatype: the name of the datatype within a project.
        """


class Center:
    """Represents a center with data managed at NACC"""

    def __init__(self, *, adcid: int, name: str, active: bool = True) -> None:
        self._adcid = adcid
        self._name = name
        self._active = active

    def __repr__(self) -> str:
        return f"Center(adcid={self.adcid}, center_id={self.center_id}, name={self.name})"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Center):
            return False
        return (self._adcid == __o._adcid and
                self._active == __o._active and
                self.name == __o.name)

    @property
    def name(self):
        return self._name

    @property
    def adcid(self):
        return self._adcid

    @property
    def center_id(self):
        return slugify(self._name)

    def apply(self, visitor):
        visitor.visit_center(self)

    @classmethod
    def create(cls, center: dict) -> "Center":
        return Center(adcid=center['adc-id'], name=center['name'], active=center['is-active'])


class Project:
    """Represents a Project with data managed at NACC"""

    def __init__(self, *, name: str, centers: List[Center], datatypes: List[str], published: bool = False) -> None:
        self._name = name
        self._centers = centers
        self._datatypes = datatypes
        self._published = published

    @property
    def project_id(self) -> str:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    @property
    def centers(self) -> List[Center]:
        return self._centers

    @property
    def datatypes(self) -> List[str]:
        return self._datatypes

    @property
    def published(self) -> bool:
        return self.published

    def apply(self, visitor) -> None:
        visitor.visit_project(self)

    T = TypeVar('T')

    @classmethod
    def create(cls, project: Mapping[str, T]) -> "Project":
        # is this actually a list ?
        return Project(name=project['project'], centers=project['centers'], datatypes=project['datatypes'], published=project['published'])
