from typing import Any
from flywheel.models.group import Group


class ContainerParents:

    @property
    def group(self) -> Group:
        ...


    def get(self, key: str) -> Any:
        ...
