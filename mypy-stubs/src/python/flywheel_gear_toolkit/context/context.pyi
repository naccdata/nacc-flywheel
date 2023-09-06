from typing import Any, Dict, Optional, Union
from flywheel.client import Client
from flywheel.models.acquisition import Acquisition
from flywheel.models.group import Group
from flywheel.models.session import Session

# container type names are listed in flywheel.models.container_type
Container = Union[Acquisition, Session, Group]


class GearToolkitContext:
    # TODO: this is probably wrong,
    def get_container_from_ref(self, ref: str) -> Container:
        ...

    def get_input_filename(self, name: str) -> str:
        ...

    @property
    def client(self) -> Client:
        ...

    @property
    def config(self) -> Dict[str, Any]:
        ...

    def get_input(self, name: str) -> Optional[Dict[str, Any]]:
        ...

    def get_input_path(self, name: str) -> Optional[str]:
        ...

    def __enter__(self) -> GearToolkitContext:
        ...

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        ...

    def init_logging(self):
        ...