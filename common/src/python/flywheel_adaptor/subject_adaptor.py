"""This is a wrapper class for flywheel Subject class to simplify building
specialized subject wrappers."""

from typing import Any, Dict

from flywheel.finder import Finder
from flywheel.models.session import Session
from flywheel.models.subject import Subject


class SubjectAdaptor:
    """Base wrapper class for flywheel subject."""

    def __init__(self, subject: Subject) -> None:
        self._subject = subject

    @property
    def info(self) -> Dict[str, Any]:
        """Returns the info object for this subject."""
        return self._subject.info

    @property
    def label(self) -> str:
        """Returns the label for this subject."""
        return self._subject.label

    @property
    def sessions(self) -> Finder:
        """Returns the finder object for the sessions of this subject."""
        return self._subject.sessions

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
