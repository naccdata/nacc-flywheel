from typing import List

from flywheel.file_spec import FileSpec


class Acquisition:

    def __init__(self, label: str) -> None:
        ...

    @property
    def id(self) -> str:
        ...

    @property
    def label(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def group(self) -> str:
        ...

    @property
    def tags(self) -> List[str]:
        ...

    def read_file(self, name: str) -> bytes:
        ...

    def upload_file(self, file: FileSpec) -> None:
        ...
