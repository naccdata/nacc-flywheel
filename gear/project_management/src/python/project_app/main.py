"""Defines project management computation."""

import logging
from typing import List

from centers.nacc_group import NACCGroup
from flywheel import AccessPermission
from flywheel.models.group_role import GroupRole
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from projects.study import Study
from projects.study_mapping import StudyMappingAdaptor

log = logging.getLogger(__name__)


def get_project_roles(flywheel_proxy,
                      role_names: List[str]) -> List[GroupRole]:
    """Get the named roles.

    Returns all roles matching a name in the list.
    Logs a warning if a name is not matched.

    Args:
      role_names: the role names
    Returns:
      the list of roles with the names
    """
    role_list = []
    for name in role_names:
        role = flywheel_proxy.get_role(name)
        if role:
            role_list.append(GroupRole(id=role.id))
        else:
            log.warning('no such role %s', name)
    return role_list


def run(*,
        proxy: FlywheelProxy,
        project_list,
        admin_access: List[AccessPermission],
        role_names: List[str],
        new_only: bool = False):
    """Runs project pipeline creation/management.

    Args:
      proxy: the proxy for the Flywheel instance
      project_list: the list of project input
      admin_access: the list of user access permissions for admin group
      role_names: list of project role names
      new_only: whether to only create centers with new tag
    """

    nacc = NACCGroup.create(proxy=proxy, group_id='nacc')
    center_roles = get_project_roles(proxy, role_names)

    for study_doc in project_list:
        study = Study.create(study_doc)
        mapper = StudyMappingAdaptor(study=study,
                                     flywheel_proxy=proxy,
                                     nacc_group=nacc,
                                     admin_access=admin_access,
                                     center_roles=center_roles,
                                     new_only=new_only)
        mapper.create_study_pipelines()
