from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ..context import GearToolkitContext


def create_qc_result_dict(name: str, state: str, **data) -> Dict:
    ...


class Metadata:

    def __init__(
        self,
        context: Optional['GearToolkitContext'] = None,
        name_override: str = "",
        version_override: str = "",
    ):
        ...

    def add_qc_result(self, file: Any, name: str, state: str,
                      data: Dict[str, Any] | Any) -> None:
        ...

    def update_file(self, file: Any, tags: List[str]) -> None:
        ...

    def update_file_metadata(self,
                             file_: Any,
                             deep: bool = True,
                             container_type: Optional[str] = None,
                             **kwargs) -> None:
        ...

    def add_gear_info(
        self,
        top_level: str,
        cont_: Any,
        **kwargs: Any,
    ) -> Dict:
        ...

    def add_file_tags(self, file_: Any, tags: Union[str,
                                                    Iterable[str]]) -> None:
        ...
