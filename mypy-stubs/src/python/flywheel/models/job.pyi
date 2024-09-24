class Job:

    @property
    def id(self) -> str:
        ...

    @property
    def state(self) -> str:
        ...

    def reload(self) -> Job:
        ...
