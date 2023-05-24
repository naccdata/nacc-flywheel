from .access_level import AccessLevel


class AccessPermission:
    def __init__(self, id: str, access: AccessLevel) -> None: ...
    @property
    def id(self) -> str:
        ...

    @property
    def access(self) -> AccessLevel:
        ...
