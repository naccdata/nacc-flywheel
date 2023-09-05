from flywheel_gear_toolkit.context import GearToolkitContext


class Curator:

    @property
    def context(self) -> GearToolkitContext:
        ...


class FileCurator(Curator):
    ...
