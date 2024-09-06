"""Run method for user management."""
import logging
from collections import defaultdict
from typing import Dict, List

from centers.nacc_group import NACCGroup
from flywheel import User
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from users.authorizations import AuthMap, Authorizations
from users.nacc_directory import Credentials, UserDirectoryEntry
from users.user_registry import RegistryPerson, UserRegistry

log = logging.getLogger(__name__)


def add_user(proxy: FlywheelProxy, user_entry: UserDirectoryEntry) -> User:
    """Creates a user object from the directory entry.

    Flywheel constraint (true as of version 17): the user ID and email must be
    the same even if ID is an ePPN in add_user

    Case can be an issue for IDs both with ORCID and ePPNs.
    Best we can do is assume ID from directory is correct.

    Args:
      proxy: the proxy object for the FW instance
      user_entry: the directory entry for the user
    Returns:
      the flywheel User created from the directory entry
    """
    new_id = proxy.add_user(user_entry.as_user())
    user = proxy.find_user(user_entry.user_id)
    assert user, f"Failed to find user {new_id} that was just created"
    return user


def create_user_map(
    user_list: List[UserDirectoryEntry]
) -> Dict[int, List[UserDirectoryEntry]]:
    """Creates a map from center tags to lists of nacc directory entries.

    Args:
      user_list: the list of user objects from directory yaml file
      skip_list: the list of user IDs to skip
    Returns:
      map from adcid to lists of nacc directory entries
    """
    center_map = defaultdict(list)
    for user_entry in user_list:
        center_map[int(user_entry.adcid)].append(user_entry)

    return center_map


def update_email(*, proxy: FlywheelProxy, user: User, email: str) -> None:
    """Updates user email on FW instance if email is different.

    Checks whether user email is the same as new email.

    Note: this needs to be applied after a user is created if the ID and email
    are different, because the API wont allow a creating new user with ID and
    email different.

    Args:
      proxy: Flywheel proxy object
      user: local user object
      email: email address to set
    """
    if user.email == email:
        return

    log.info('Setting user %s email to %s', user.id, email)
    proxy.set_user_email(user=user, email=email)


def authorize_user(*, user: User, center_id: int,
                   authorizations: Authorizations, admin_group: NACCGroup,
                   authorization_map: AuthMap) -> None:
    """Adds authorizations to users."""
    center_group = admin_group.get_center(center_id)
    if not center_group:
        log.warning('No center found with ID %s', center_id)
        return

    # give users access to nacc metadata project
    admin_group.add_center_user(user=user)

    # give users access to center projects
    center_group.add_user_roles(user=user,
                                authorizations=authorizations,
                                auth_map=authorization_map)


def run(*, proxy: FlywheelProxy, user_list: List[UserDirectoryEntry],
        admin_group: NACCGroup, authorization_map: AuthMap,
        registry: UserRegistry):
    """Manages users based on user list.

    Args:
      proxy: Flywheel proxy object
      user_list: the list of user objects from directory yaml file
      admin_group: the NACCGroup object representing the admin group
      skip_list: the list of user IDs to skip
      authorization_map: the AuthMap object representing the authorization map
      registry: the user registry
    """

    for user_entry in user_list:
        person_list = registry.list(email=user_entry.email)

        if not person_list:
            identifier_list = registry.add(
                RegistryPerson.create(firstname=user_entry.first_name,
                                      lastname=user_entry.last_name,
                                      email=user_entry.email,
                                      coid=str(registry.coid)))
            # TODO: send claim email
            # TODO: record claim creation for reminders
            log.info('Add user %s to registry', user_entry.email)
            continue

        claimed = [person for person in person_list if person.is_claimed()]
        if claimed:
            registered = [
                person.registry_id() for person in claimed
                if person.registry_id()
            ]
            if not registered:
                log.error('User %s has no registry ID', user_entry.email)
                continue
            if len(registered) > 1:
                log.error('Email %s has more than one registry ID %s',
                          user_entry.email, registered)
                continue

            registry_id = registered.pop()
            assert registry_id, 'registry_id should not be None'
            user = proxy.find_user(registry_id)
            if not user:
                try:
                    user_entry.set_credentials(credentials=Credentials(
                        type='registry', id=registry_id))
                    user = add_user(proxy=proxy, user_entry=user_entry)
                    # TODO: send user creation email
                    log.info('Added user %s', user.id)
                except AssertionError as error:
                    log.error('Failed to add user %s with ID %s: %s',
                              user_entry.email, registry_id, error)
                    continue

            update_email(proxy=proxy, user=user, email=user_entry.email)
            authorize_user(user=user,
                           admin_group=admin_group,
                           center_id=user_entry.adcid,
                           authorizations=user_entry.authorizations,
                           authorization_map=authorization_map)
            continue

        # not claimed
        # TODO: check time since creation is an even multiple of a week
        # TODO: email claim reminder
