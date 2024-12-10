"""Maps ADCID to projects."""
import logging
import re
from typing import Dict, List, Optional

from centers.center_group import CenterError, CenterGroup
from centers.nacc_group import NACCGroup
from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor

log = logging.getLogger(__name__)


def build_project_map(
        *,
        proxy: FlywheelProxy,
        destination_label: str,
        centers: Optional[List[int]] = None) -> Dict[str, ProjectAdaptor]:
    """Builds a map from adcid to the project of center group with the given
    label.

    Args:
      proxy: the flywheel instance proxy
      destination_label: the project of center to map to
      centers: the subset of centers to return; if not specified, returns all
    Returns:
      dictionary mapping from adcid to group
    """
    # create center info mapping from NACCGroup, filter down to centers we need
    center_map = NACCGroup.create(proxy=proxy).get_center_map()
    if centers:
        center_map = [x for x in center_map if x.adcid in centers]

    # convert map to group

    try:
        group_list = [
            CenterGroup.create_from_center(group=group, proxy=proxy)
            for group in center_map
        ]
    except CenterError as error:
        log.error('failed to create center from group: %s', error.message)
        return {}

    if not group_list:
        log.warning('no centers found')
        return {}

    project_map = {}
    for group in group_list:
        project = group.find_project(destination_label)
        if not project:
            continue

        pattern = re.compile(center_tag_pattern)
        tags = list(filter(pattern.match, group.get_tags()))
        for tag in tags:
            project_map[tag] = project

    return project_map
