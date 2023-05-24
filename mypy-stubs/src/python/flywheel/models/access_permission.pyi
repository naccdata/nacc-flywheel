from .access_level import AccessLevel


class AccessPermission:

    @property
    def id(self) -> str:
        ...

    @property
    def access(self) -> AccessLevel:
        ...
