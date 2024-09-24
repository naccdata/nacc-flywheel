from typing import Any, List, Optional

from flywheel.models.data_view import DataView


class ViewBuilder:

    def __init__(self, label: Optional[str], columns: Optional[List[Any]],
                 container: Optional[str], filename: Optional[str],
                 process_files: bool, filter: Optional[str], include_ids: bool,
                 include_labels: bool, match: Optional[str]) -> None:
        ...

    def build(self) -> DataView:
        ...

    def missing_data_strategy(self, value) -> 'ViewBuilder':
        ...
