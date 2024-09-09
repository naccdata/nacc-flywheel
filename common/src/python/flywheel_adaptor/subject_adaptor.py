"""This is a wrapper class for flywheel Subject class to simplify building
specialized subject wrappers."""

import logging
from typing import Any, Dict, List, Optional

from centers.center_group import kebab_case
from flywheel.finder import Finder
from flywheel.models.session import Session
from flywheel.models.subject import Subject
from pydantic import AliasGenerator, BaseModel, ConfigDict, Field, ValidationError

log = logging.getLogger(__name__)

DATE_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class SubjectError(Exception):
    """Exception class for errors related Flywheel subject."""


class VisitInfo(BaseModel):
    """Class to represent file information for a particpant visit."""
    model_config = ConfigDict(populate_by_name=True,
                              alias_generator=AliasGenerator(alias=kebab_case))

    filename: str
    file_id: Optional[str] = None  # Flywheel File ID
    visitdate: str = Field(pattern=DATE_PATTERN)


class ParticipantVisits(BaseModel):
    """Class to represent visits for a given participant for a given module."""
    model_config = ConfigDict(populate_by_name=True,
                              alias_generator=AliasGenerator(alias=kebab_case))

    participant: str  # Flywheel subject label
    module: str  # module label (Flywheel aquisition label)
    visits: List[VisitInfo]


class SubjectAdaptor:
    """Base wrapper class for flywheel subject."""

    def __init__(self, subject: Subject) -> None:
        self._subject = subject

    @property
    def info(self) -> Dict[str, Any]:
        """Returns the info object for this subject."""
        self._subject = self._subject.reload()
        return self._subject.info

    @property
    def label(self) -> str:
        """Returns the label for this subject."""
        return self._subject.label

    @property
    def sessions(self) -> Finder:
        """Returns the finder object for the sessions of this subject."""
        return self._subject.sessions

    @property
    def id(self) -> str:
        """Returns the ID for this subject."""
        return self._subject.id

    def add_session(self, label: str) -> Session:
        """Adds and returns a new session for this subject.

        Args:
          label: the label for the session
        Returns:
          the added session
        """
        return self._subject.add_session(label=label)

    def update(self, info: Dict[str, Any]) -> None:
        """Updates the info object for this subject.

        Args:
          info: the info dictionary for update
        """
        self._subject.update(info=info)

    def get_last_failed_visit(self, module: str) -> Optional[VisitInfo]:
        """Returns the last failed visit for this subject for the given module.

        Args:
            module: module label (Flywheel aquisition label)

        Returns:
            Optional[VisitInfo]: Last failed visit if exists

         Raises:
          SubjectError if required metadata is missing
        """
        qc_info = self.info.get('qc', None)
        if not qc_info:
            return None

        module_info = qc_info.get(module.lower(), None)
        if not module_info:
            return None

        last_approved = qc_info.get('failed', None)
        if not last_approved:
            return None

        try:
            return VisitInfo.model_validate(last_approved)
        except ValidationError as error:
            raise SubjectError('Incomplete failed visit metadata for subject '
                               f'{self.label}/{module} - {error}')

    def set_last_failed_visit(self, module: str, failed_visit: VisitInfo):
        """Update last failed visit info for this subject for the given module.

        Args:
            module: module label (Flywheel aquisition label)
            failed_visit: failed visit info
        """
        qc = {'qc': {module.lower(): {'failed': failed_visit.model_dump()}}}
        self.update(info=qc)
