from typing import Any, Dict

from flywheel.models.container_parents import ContainerParents


class FileEntry:

    @property
    def name(self) -> str:
        ...

    @property
    def mimetype(self) -> str:
        ...

    @property
    def hash(self) -> str:
        ...

    @property
    def parents(self) -> ContainerParents:
        ...

    def read(self) -> str:
        ...

    def get(self, key: str) -> Dict[str, Any]:
        ...
