from typing import Any
from flywheel.models.group import Group


class ContainerParents:

    @property
    def group(self) -> str:
        ...


    def get(self, key: str) -> Any:
        ...
