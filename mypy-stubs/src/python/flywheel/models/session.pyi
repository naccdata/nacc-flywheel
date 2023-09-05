from typing import Any, Dict


class Session:

    @property
    def label(self) -> str:
        ...

    @property
    def info(self) -> object:
        ...

    def update(self, map: Dict[str, Any]):
        ...
