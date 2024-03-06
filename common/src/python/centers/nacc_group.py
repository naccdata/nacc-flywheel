"""Singleton class representing NACC with a FW group."""

from typing import Dict, Optional

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
            assert self.__metadata, "expecting metadata project"

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
        center_map = self.get_center_map()
        metadata = self.get_metadata()
        center_map[adcid] = CenterInfo(adcid=adcid,
                                       name=group_label,
                                       group=group_id)
        metadata.update_info({'centers': center_map})

    def get_center_map(self) -> Dict[int, CenterInfo]:
        """Returns the adcid-group map.

        Returns:
          dictionary mapping adcid to adcid-group label correspondence
        """
        project = self.get_metadata()
        info = project.get_info()

        if not info:
            return {}

        try:
            center_map = CenterMapInfo.model_validate(info.get('centers', {}))
        except ValidationError:
            center_map = CenterMapInfo(centers={})

        return center_map.centers

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
        group_info = center_map.get(adcid, None)
        if not group_info:
            return None

        group_id = group_info.group
        group = self.__fw.find_group(group_id=str(group_id))
        if not group:
            return None

        return CenterGroup.create_from_group_adaptor(adaptor=group,
                                                     proxy=self.__fw)

    def add_center_user(self, user: User) -> None:
        """Authorizes a user to access the metadata project of nacc group.

        Args:
          user: the user object
        """
        assert user.id, "User must have user ID"

        metadata_project = self.get_metadata()
        read_only_role = self.__fw.get_role('read-only')
        assert read_only_role, "Expecting read-only role to exist"

        metadata_project.add_user_role(user=user,
                                       role=read_only_role)