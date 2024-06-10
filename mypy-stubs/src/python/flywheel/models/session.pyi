from flywheel.finder import Finder
from flywheel.models.acquisition import Acquisition


class Session:

    @property
    def acquisitions(self) -> Finder[Acquisition]:
        ...

    def add_acquisition(self, label: str) -> Acquisition:
        ...
