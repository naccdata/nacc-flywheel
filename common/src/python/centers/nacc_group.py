"""Singleton class representing NACC with a FW group."""

from typing import Dict, Optional

from centers.center_group import CenterGroup
from flywheel.models.group import Group
from flywheel_adaptor.flywheel_proxy import (FlywheelProxy, GroupAdaptor,
                                             ProjectAdaptor)


class NACCGroup(GroupAdaptor):

    def __init__(self, *, group: Group, proxy: FlywheelProxy) -> None:
        self.__metadata: Optional[ProjectAdaptor] = None
        super().__init__(group=group, proxy=proxy)

    @classmethod
    def create(cls,
               *,
               proxy: FlywheelProxy,
               group_label: str = 'nacc') -> 'NACCGroup':
        """Creates a NACCGroup object for the group on the flywheel instance.

        Args:
          proxy: the flywheel instance proxy object
          group_label: the label for NACC group (optional)
        Returns:
          the NACCGroup object
        """
        group = proxy.get_group(group_label="NACC", group_id=group_label)
        return NACCGroup(group=group, proxy=proxy)

    def get_metadata(self) -> ProjectAdaptor:
        """Returns the metadata project.

        Returns:
          The metadata object
        """
        if not self.__metadata:
            project = self.get_project('metadata')
            assert project, "expecting metadata project"
            self.__metadata = ProjectAdaptor(project=project,
                                             proxy=self.proxy())

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
        """
        center_map = self.get_center_map()
        metadata = self.get_metadata()
        center_map[adcid] = {
            'acdid': adcid,
            'name': group_label,
            'group': group_id
        }
        metadata.update_info({'centers': center_map})

    def get_center_map(self) -> Dict[int, Dict[str, str | int]]:
        """Returns the adcid-group map.

        Returns:
          dictionary mapping adcid to adcid-group label correspondence
        """
        project = self.get_metadata()
        info = project.get_info()

        return info.get('centers', {})
