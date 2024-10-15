"""This is a wrapper class for flywheel Subject class to simplify building
specialized subject wrappers."""

import logging
from typing import Any, Dict, List, Optional

from flywheel.finder import Finder
from flywheel.models.session import Session
from flywheel.models.subject import Subject
from pydantic import AliasGenerator, BaseModel, ConfigDict, Field, ValidationError
from serialization.case import kebab_case

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

        module_info = self.info.get(module, {})
        last_failed = module_info.get('failed', None)
        if not last_failed:
            return None

        try:
            return VisitInfo.model_validate(last_failed)
        except ValidationError as error:
            raise SubjectError('Incomplete failed visit metadata for subject '
                               f'{self.label}/{module} - {error}') from error

    def set_last_failed_visit(self, module: str, failed_visit: VisitInfo):
        """Update last failed visit info for this subject for the given module.

        Args:
            module: module label (Flywheel aquisition label)
            failed_visit: failed visit info
        """

        # make sure to load the existing metadata first and then modify
        # update_info() will replace everything under the top-level key
        module_info = self.info.get(module, {})
        module_info['failed'] = failed_visit.model_dump()
        updates = {module: module_info}
        self._subject.update_info(updates)

    def reset_last_failed_visit(self, module: str):
        """Reset last failed visit info for this subject for the given module.

        Args:
            module: module label (Flywheel aquisition label)
        """

        # make sure to load the existing metadata first and then modify
        # update_info() will replace everything under the top-level key
        module_info = self.info.get(module, {})
        module_info['failed'] = {}
        updates = {module: module_info}
        # Note: have to use update_info() here for reset to take effect
        # Using update() will not delete any exsisting data
        self._subject.update_info(updates)
