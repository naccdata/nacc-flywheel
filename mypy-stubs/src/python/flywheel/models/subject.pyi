from typing import Any, Dict
from flywheel import Session

from flywheel.finder import Finder


class Subject:

    def add_session(self, label: str) -> Session:
        ...

    @property
    def sessions(self) -> Finder[Session]:
        ...

    def update(self, info: Dict[str, Any]) -> None:
        ...

    @property
    def info(self) -> Dict[str, Any]:
        ...

    @property
    def label(self) -> str:
        ...
