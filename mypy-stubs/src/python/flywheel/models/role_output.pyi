class RoleOutput:

    @property
    def id(self) -> str:
        ...

    @property
    def label(self) -> str:
        ...

    @property
    def in_use(self) -> bool:
        ...