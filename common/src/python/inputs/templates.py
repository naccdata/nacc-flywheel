"""Functions to pull information from template projects."""
import logging
import re
from collections import defaultdict
from typing import Dict

from flywheel_adaptor.flywheel_proxy import GroupAdaptor
from projects.template_project import TemplateProject

log = logging.getLogger(__name__)


def get_template_projects(
        group: GroupAdaptor) -> Dict[str, Dict[str, TemplateProject]]:
    """Returns template projects from the group on the indicated FW instance.

    Expects template project names to match `<datatype>-<stage>-template`.

    Organizes projects by stage name, and then by datatype name.

    Args:
      group: the flywheel group containing the template projects
      proxy: the proxy for the flywheel instance
    Returns:
      dictionary of template projects indexed by stage and datatype
    """
    template_map: Dict[str, Dict[str, TemplateProject]] = defaultdict(dict)
    if not group:
        return template_map

    template_matcher = re.compile(r"^((\w+)-)?(\w+)-template$")
    # match group for pipeline datatype
    datatype_group = 2
    # match group for pipeline stage
    stage_group = 3

    for project in group.projects():
        match = template_matcher.match(project.label)
        if not match:
            continue

        datatype = match.group(datatype_group)
        if not datatype:
            # accepted stage has no datatype, set to 'all'
            datatype = 'all'
        stage = match.group(stage_group)

        stage_map = template_map[datatype]
        stage_map[stage] = TemplateProject(project=project,
                                           proxy=group.proxy())
        template_map[datatype] = stage_map

    return template_map
