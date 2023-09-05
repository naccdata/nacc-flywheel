from typing import Any, Dict


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

    def read(self) -> str:
        ...

    def get(self, key: str) -> Dict[str, Any]:
        ...
