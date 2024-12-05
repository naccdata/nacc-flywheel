"""Models representing center information and center mappings."""
from typing import Dict, List, Optional, Tuple

from projects.study import StudyVisitor
from pydantic import AliasChoices, BaseModel, Field, validator


class CenterInfo(BaseModel):
    """Represents a center with data managed at NACC.

    Attributes:
        adcid (int): The ADC ID of the center.
        name (str): The name of the center.
        center_id (str): The symbolic ID for the center,
                         can also be aliased to group

        active (bool): Optional, active or inactive status. Defaults to True.
        tags (Tuple[str]): Optional, list of tags for the center
    """
    adcid: int
    name: str
    center_id: str = Field(validation_alias=AliasChoices('center_id',
                                                         'center-id',
                                                         'group'))
    active: Optional[bool] = Field(validation_alias=AliasChoices('active',
                                                                 'is-active',
                                                                 'is_active'),
                                   default=True)
    tags: Optional[Tuple[str, ...]] = ()

    def __repr__(self) -> str:
        return (f"Center(center_id={self.center_id}, "
                f"name={self.name}, "
                f"adcid={self.adcid}, "
                f"active={self.active}, "
                f"tags={self.tags}")

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, CenterInfo):
            return False
        # compare everything except tags
        return (self.adcid == __o.adcid and self.center_id == __o.center_id
                and self.name == __o.name and self.active == __o.active)

    @validator("tags")
    def set_tags(cls, tags: Tuple[Tuple[str], List[str]]) -> Tuple[str]:
        if not tags:
            return ()
        return tuple(tags)

    def apply(self, visitor: StudyVisitor):
        """Applies visitor to this Center."""
        visitor.visit_center(self.center_id)


class CenterMapInfo(BaseModel):
    """Represents the center map in nacc/metadata project."""
    centers: Dict[int, CenterInfo]

    def add(self, adcid: int, center_info: CenterInfo) -> None:
        """Adds the center info to the map.

        Args:
            adcid: The ADC ID of the center.
            center_info: The center info object.
        """
        self.centers[adcid] = center_info

    def get(self, adcid: int) -> Optional[CenterInfo]:
        """Gets the center info for the given ADCID.

        Args:
            adcid: The ADC ID of the center.
        Returns:
            The center info for the center. None if no info is found.
        """
        return self.centers.get(adcid, None)
