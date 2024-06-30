from typing import Any, Dict, List, Optional


class Metadata:

    def add_qc_result(self, file: Any, name: str, state: str,
                      data: Dict[str, Any] | Any) -> None:
        ...

    def update_file(self, file: Any, tags: List[str]) -> None:
        ...
