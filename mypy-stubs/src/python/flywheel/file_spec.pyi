class FileSpec:

    def __init__(self, name: str, contents: str, content_type: str) -> None:
        ...

    @property
    def name(self) -> str:
        ...
