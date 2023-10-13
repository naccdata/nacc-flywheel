"""Run method for user management."""
import logging
from collections import defaultdict
from typing import Set, TypedDict

from flywheel import RolesRoleAssignment, User
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_adaptor.group_adaptor import GroupAdaptor
from flywheel_adaptor.project_adaptor import ProjectAdaptor
from redcap.nacc_directory import Authorizations, UserDirectoryEntry

log = logging.getLogger(__name__)


def create_user(proxy: FlywheelProxy, user_entry: UserDirectoryEntry) -> User:
    """Creates a user object from the directory entry.

    Flywheel constraints (true as of version 17):
    1. user IDs should be lowercase b/c FW treats them as case sensitive.
    2. the user ID and email must be the same even if ID is an ePPN in add_user

    Args:
      proxy: the proxy object for the FW instance
      user_entry: the directory entry for the user
    Returns:
      the flywheel User with the ID in directory entry
    """

    user_id = user_entry.credentials['id'].lower()
    user = proxy.find_user(user_id)
    if user:
        return user

    new_id = proxy.add_user(
        User(id=user_id,
             firstname=user_entry.name['first_name'],
             lastname=user_entry.name['last_name'],
             email=user_id))
    user = proxy.find_user(new_id)
    assert user, f"Just created user {new_id}, should exist but is None"

    return user


class UserAuthorizations(TypedDict):
    """User-authorizations pair for."""
    user: User
    authorizations: Authorizations


# pylint: disable=(too-many-locals)
def run(*, proxy: FlywheelProxy, user_list, skip_list: Set[str]):
    """Manages users based on user list."""

    # gather users by center
    center_prefix = 'adcid-'
    center_map = defaultdict(list)
    for user_doc in user_list:
        user_entry = UserDirectoryEntry.create(user_doc)
        if user_entry.credentials['id'] in skip_list:
            log.info('Skipping admin user: %s', user_entry.credentials['id'])
            continue

        user = create_user(proxy=proxy, user_entry=user_entry)
        center_map[f"{center_prefix}{user_entry.center_id}"].append(
            UserAuthorizations(user=user,
                               authorizations=user_entry.authorizations))

    roles_map = proxy.get_roles()
    read_only_role = roles_map.get('read-only')
    if not read_only_role:
        log.error('Could not find read-only role, cannot add permissions')
        return

    for center_tag, center_users in center_map.items():
        group_list = proxy.find_groups_by_tag(center_tag)
        if len(group_list) > 1:
            log.error('Error: expecting only one center for tag %s',
                      center_tag)
            continue
        center_group = GroupAdaptor(group=group_list[0], proxy=proxy)

        # for now, just giving all users read-only access to 'ingest-scan'
        project_label = 'ingest-scan'
        project = center_group.get_project(project_label)
        if not project:
            log.warning('center %s does not have project %s',
                        center_group.label, project_label)
            continue

        project_adaptor = ProjectAdaptor(project=project, proxy=proxy)
        for user_authorization in center_users:
            project_adaptor.add_user_roles(
                RolesRoleAssignment(id=user_authorization['user'].id,
                                    role_ids=[read_only_role.id]))
