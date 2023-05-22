from typing import Any, List

from .roles_backwards_compatible_role_assignment import RolesBackwardsCompatibleRoleAssignment

from .project_parents import ProjectParents

from .file_entry import FileEntry


class Project:
    def __init__(self, label: str, parents: ProjectParents) -> None:
        ...

    @property
    def id(self) -> str:
        ...

    @property
    def label(self) -> str:
        ...

    @property
    def description(self) -> str: ...

    @property
    def group(self) -> str:
        ...
    @property
    def tags(self) -> List[str]:
        ...
    @property
    def permissions(self) -> List[RolesBackwardsCompatibleRoleAssignment]: ...

    def add_tag(self, tag: str) -> None:
        ...
    
    def get_file(self, name: str) -> FileEntry: ...