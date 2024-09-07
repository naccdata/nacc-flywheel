from typing import Any, Dict, List, Optional


class Metadata:

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
