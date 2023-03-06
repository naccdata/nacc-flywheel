"""Defines project management computation."""

import logging
from typing import List, Optional

import flywheel
from projects.flywheel_proxy import FlywheelProxy
from projects.project import Project
from projects.project_mapping import ProjectMappingAdaptor

log = logging.getLogger(__name__)


def run(*, proxy: FlywheelProxy, project_list,
        admin_users: List[flywheel.User],
        gear_rules: Optional[List[flywheel.Rule]]):
    """Runs project pipeline creation/management.

    Args:
      proxy: the proxy for the Flywheel instance
      project_list: the list of project input
      admin_users: the list of admin users
      gear_rules: a list of gear rules to add to the project
    """

    for project_doc in project_list:
        project = Project.create(project_doc)
        project_mapper = ProjectMappingAdaptor(project=project,
                                               flywheel_proxy=proxy,
                                               admin_users=admin_users,
                                               gear_rules=gear_rules)
        project_mapper.create_project_pipelines()

