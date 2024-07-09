from typing import Any, Dict
from flywheel.finder import Finder
from flywheel.models.acquisition import Acquisition


class Session:

    @property
    def label(self) -> str:
        ...

    @property
    def info(self) -> object:
        ...

    def update(self, map: Dict[str, Any]):
        ...

    @property
    def acquisitions(self) -> Finder[Acquisition]:
        ...

    def add_acquisition(self, label: str) -> Acquisition:
        ...
