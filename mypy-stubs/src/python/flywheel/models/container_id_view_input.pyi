from typing import List

from .data_strategy import DataStrategy

from .group_by import GroupBy
from .column import Column

class ContainerIdViewInput:
    def __init__(self, parent:str, label:str,description:str, columns:List[Column], group_by: GroupBy, filter: str, file_spec: object, include_ids: bool, include_labels: bool, error_column:bool, missing_data_strategy: DataStrategy, sort: bool, id: str) -> None: ...
