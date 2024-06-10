from flywheel import Session

from flywheel.finder import Finder


class Subject:

    def add_session(self, label: str) -> Session:
        ...

    @property
    def sessions(self) -> Finder[Session]:
        ...
