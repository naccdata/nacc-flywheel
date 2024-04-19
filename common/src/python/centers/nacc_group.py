"""Singleton class representing NACC with a FW group."""

from typing import Dict, List, Optional

from centers.center_group import CenterGroup
from flywheel.models.group import Group
from flywheel.models.user import User
from flywheel_adaptor.flywheel_proxy import (FlywheelProxy, GroupAdaptor,
                                             ProjectAdaptor)
from pydantic import BaseModel, ValidationError


class CenterInfo(BaseModel):
    """Represents information about a center in nacc/metadata project.

    Attributes:
        adcid (int): The ADC ID of the center.
        name (str): The name of the center.
        group (str): The group ID of the center.
    """
    adcid: int
    name: str
    group: str


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


class NACCGroup(GroupAdaptor):
    """Manages group for NACC."""

    def __init__(self, *, group: Group, proxy: FlywheelProxy) -> None:
        self.__metadata: Optional[ProjectAdaptor] = None
        super().__init__(group=group, proxy=proxy)

    @classmethod
    def create(cls,
               *,
               proxy: FlywheelProxy,
               group_id: str = 'nacc') -> 'NACCGroup':
        """Creates a NACCGroup object for the group on the flywheel instance.

        Args:
          proxy: the flywheel instance proxy object
          group_id: the label for NACC group (optional)
        Returns:
          the NACCGroup object
        """
        group = proxy.get_group(group_label="NACC", group_id=group_id)
        return NACCGroup(group=group, proxy=proxy)

    def get_metadata(self) -> ProjectAdaptor:
        """Returns the metadata project.

        Returns:
          The metadata object
        """
        if not self.__metadata:
            self.__metadata = self.get_project('metadata')
            assert self.__metadata, ("Expecting metadata project. "
                                     "Check user has permissions.")

        return self.__metadata

    def add_center(self, center_group: CenterGroup) -> None:
        """Adds the metadata for the center.

        Args:
          center_group: the CenterGroup object for the center
        """
        self.add_adcid(adcid=center_group.adcid,
                       group_label=center_group.label,
                       group_id=center_group.id)

    def add_adcid(self, adcid: int, group_label: str, group_id: str) -> None:
        """Adds the adcid-group correspondence.

        Args:
          adcid: the ADC ID
          group_label: the label for the center group
          group_id: the ID for the center group
        """
        metadata = self.get_metadata()
        center_map = self.get_center_map()
        center_map.add(
            adcid, CenterInfo(adcid=adcid, name=group_label, group=group_id))
        metadata.update_info(center_map.model_dump())

    def get_center_map(self) -> CenterMapInfo:
        """Returns the adcid-group map.

        Returns:
          dictionary mapping adcid to adcid-group label correspondence
        """
        project = self.get_metadata()
        info = project.get_info()

        if not info:
            return CenterMapInfo(centers={})

        try:
            center_map = CenterMapInfo.model_validate(info)
        except ValidationError:
            center_map = CenterMapInfo(centers={})

        return center_map

    def get_adcid(self, group_id: str) -> Optional[int]:
        """Returns the ADCID for the center group.

        Args:
          group_id: the ID for the center group
        Returns:
          the ADCID for the center
        """
        center_map = self.get_center_map()
        for adcid, center_info in center_map.centers.items():
            if center_info.group == group_id:
                return adcid
        return None

    def get_center(self, adcid: int) -> Optional[CenterGroup]:
        """Returns the center group for the given ADCID.

        Args:
            adcid: The ADCID of the center group to retrieve.

        Returns:
            The CenterGroup for the center. None if no group is found.

        Raises:
            AssertionError: If no center is found for the given ADCID.
        """
        center_map = self.get_center_map()
        center_info = center_map.get(adcid)
        if not center_info:
            return None

        group_id = center_info.group
        group = self._fw.find_group(group_id=str(group_id))
        if not group:
            return None

        return CenterGroup.create_from_group_adaptor(adaptor=group)

    def get_centers(self) -> List[CenterGroup]:
        """Returns the center groups for all centers.

        Returns:
            The list of center groups.
        """
        centers = []
        center_map = self.get_center_map()
        for center_info in center_map.centers.values():
            group_id = center_info.group
            group = self._fw.find_group(group_id=(group_id))
            if group:
                center = CenterGroup.create_from_group_adaptor(group)
                centers.append(center)

        return centers

    def add_center_user(self, user: User) -> None:
        """Authorizes a user to access the metadata project of nacc group.

        Args:
          user: the user object
        """
        assert user.id, "User must have user ID"

        metadata_project = self.get_metadata()
        read_only_role = self._fw.get_role('read-only')
        assert read_only_role, "Expecting read-only role to exist"

        metadata_project.add_user_role(user=user, role=read_only_role)
