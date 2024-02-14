from flywheel.models.group import Group
from flywheel.models.project import Project

class ContainerParents:

    @property
    def group(self) -> str:
        ...

    @property
    def project(self) -> str:
        ...