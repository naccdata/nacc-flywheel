"""Classes for representing NACC studies (or, if you must, projects)."""
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional


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


class StudyVisitor(ABC):
    """Abstract class for a visitor object for studies."""

    @abstractmethod
    def visit_study(self, study: "Study") -> None:
        """Method to visit the given study.

        Args:
          study: the study to visit.
        """

    @abstractmethod
    def visit_center(self, center_id: str) -> None:
        """Method to visit the given center within a study.

        Args:
          center_id: the ID of the center to visit
        """

    @abstractmethod
    def visit_datatype(self, datatype: str):
        """Method to visit the given datatype within a study.

        Args:
          datatype: the name of the datatype within a study.
        """


class Center:
    """Represents a center with data managed at NACC."""

    def __init__(self,
                 *,
                 name: str,
                 center_id: str,
                 adcid: int,
                 active: bool = True,
                 tags: Optional[List[str]] = None) -> None:
        """Initializes a center object.

        Args:
          name: the name of the center
          center_id: symbolic ID for center
          adcid: the numeric ADC ID for center used in data
          active: whether the center is active
          tags: list of tags for the center
        """
        self.__name = name
        self.__active = active
        self.__center_id = center_id
        self.__adcid = adcid
        if tags is None:
            tags = []
        self.__tags = tags

    def __repr__(self) -> str:
        return (f"Center(center_id={self.center_id}, "
                f"name={self.name}, "
                f"adcid={self.adcid}, "
                f"active={self.is_active()}, "
                f"tags={self.tags}")

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Center):
            return False
        return (self.__center_id == __o.center_id and self.__adcid == __o.adcid
                and self.__active == __o.is_active() and self.name == __o.name)

    @property
    def name(self) -> str:
        """Center name property."""
        return self.__name

    def is_active(self) -> bool:
        """Indicates whether the center is active."""
        return self.__active

    @property
    def center_id(self) -> str:
        """Center text ID property."""
        return self.__center_id

    @property
    def adcid(self) -> int:
        """ADC ID property."""
        return self.__adcid

    @property
    def tags(self) -> Iterable[str]:
        """Center tags property."""
        return tuple(self.__tags)

    def apply(self, visitor: StudyVisitor):
        """Applies visitor to this Center."""
        visitor.visit_center(self.center_id)

    @classmethod
    def create(cls, center: Dict[str, Any]) -> "Center":
        """Creates a Center from the given dictionary."""

        tags: List[str] = []
        if 'tags' in center:
            tags = center['tags']

        return Center(name=center['name'],
                      center_id=center['center-id'],
                      adcid=int(center['adcid']),
                      active=center['is-active'],
                      tags=tags)


StudyMode = Literal['aggregation', 'distribution']


class Study:
    """Represents a study with data managed at NACC."""

    def __init__(self,
                 *,
                 name: str,
                 study_id: str,
                 centers: List[str],
                 datatypes: List[str],
                 mode: StudyMode,
                 published: bool = False,
                 primary: bool = False) -> None:
        """Initializes a study object.

        Args:
          name: the name of the study
          study_id: the symbolic ID of study
          centers: the list of ids for centers in the study
          mode: whether the study aggregates or distributes data
          published: whether the data for the study is to be released
          primary: whether this is the primary study of the coordinating center
        """
        self.__name = name
        self.__centers = centers
        self.__datatypes = datatypes
        self.__mode: StudyMode = mode
        self.__published = published
        self.__primary = primary
        self.__study_id = study_id

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Study):
            return False
        return (__o.name == self.__name and __o.centers == self.centers
                and __o.datatypes == self.datatypes
                and __o.__mode == self.__mode
                and __o.is_published() == self.is_published()
                and __o.is_primary() == self.is_primary())

    def __repr__(self) -> str:
        return ("Study("
                f"name={self.__name},"
                f"study_id={self.__study_id},"
                f"centers={self.__centers},"
                f"datatypes={self.__datatypes},"
                f"mode={self.__mode},"
                f"published={self.__published},"
                f"primary={self.__primary}"
                ")")

    @property
    def study_id(self) -> str:
        """Study ID property."""
        return self.__study_id

    @property
    def name(self) -> str:
        """Study Name property."""
        return self.__name

    @property
    def centers(self) -> List[str]:
        """Study centers property."""
        return self.__centers

    @property
    def datatypes(self) -> List[str]:
        """Study datatypes property."""
        return self.__datatypes

    @property
    def mode(self) -> StudyMode:
        """Study mode property."""
        return self.__mode

    def is_published(self) -> bool:
        """Study published predicate."""
        return self.__published

    def is_primary(self) -> bool:
        """Predicate to indicate whether is the main study of coordinating
        center."""
        return self.__primary

    def apply(self, visitor: StudyVisitor) -> None:
        """Apply visitor to this Study."""
        visitor.visit_study(self)

    def project_suffix(self) -> str:
        """Creates the suffix that should be added to study pipelines."""
        if self.is_primary():
            return ''

        return f"-{self.study_id}"

    @classmethod
    def create(cls, study: Mapping[str, Any]) -> "Study":
        """Create study from given mapping."""
        primary_study = False
        if 'primary' in study:
            primary_study = study['primary']

        study_mode: StudyMode = study.get('mode', 'aggregation')
        return Study(name=study['study'],
                     study_id=study['study-id'],
                     centers=study['centers'],
                     datatypes=study['datatypes'],
                     mode=study_mode,
                     published=study['published'],
                     primary=primary_study)
