from typing import Generic, List, Optional, TypeVar

T = TypeVar('T')


class Finder(Generic[T]):

    def find(self, args: str) -> List[T]:
        ...

    def find_first(self, args: str) -> Optional[T]:
        ...
