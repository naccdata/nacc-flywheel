from typing import List

from .project import Project


class Group:

    def __init__(self, id: str, label: str) -> None:
        ...

    @property
    def label(self) -> str:
        ...

    @property
    def id(self) -> str:
        ...

    def add_project(self, label: str) -> Project:
        ...

    @property
    def roles(self) -> List[str]:
        ...
