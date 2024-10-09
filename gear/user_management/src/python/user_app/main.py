"""Run method for user management."""
import logging
from datetime import datetime
from typing import List, Optional

from centers.nacc_group import NACCGroup
from coreapi_client.models.identifier import Identifier
from flywheel import User
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from users.authorizations import AuthMap, Authorizations
from users.nacc_directory import ActiveUserEntry, UserEntry
from users.user_registry import RegistryPerson, UserRegistry

from user_app.notification_client import NotificationClient

log = logging.getLogger(__name__)


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
    """Adds authorizations to the user.

    Users are granted access to nacc/metadata and projects per authorizations.

    Args:
      user: the user
      center_id: the center of the user
      authorizations: the user authorizations
      admin_group: the admin group
      authorization_map: the map from authorization to FW role
    """
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


def add_to_registry(*, user_entry: UserEntry,
                    registry: UserRegistry) -> List[Identifier]:
    """Adds a user to the registry using the user entry data.

    Note: the comanage API was not returning any identifers last checked

    Args:
      user_entry: the user directory entry
      registry: the comanage registry
    Returns:
      the list of identifiers for the new registry record
    """
    assert user_entry.auth_email, "user entry must have auth email"
    identifier_list = registry.add(
        RegistryPerson.create(firstname=user_entry.first_name,
                              lastname=user_entry.last_name,
                              email=user_entry.auth_email,
                              coid=registry.coid))

    return identifier_list


def get_registry_id(claimed_list: List[RegistryPerson]) -> Optional[str]:
    """Gets the registry ID for the person in the list.

    Args:
      claimed_list: person objects that are claimed
    Returns:
      registry ID from person object. None if none is found.
    """
    registered = [
        person.registry_id() for person in claimed_list
        if person.registry_id()
    ]
    if not registered:
        return None
    if len(registered) > 1:
        log.error('More than one registry ID found')
        return None

    return registered.pop()


def get_creation_date(person_list: List[RegistryPerson]) -> Optional[datetime]:
    """Gets the most recent creation date from the person objects in the list.

    A person object will not have a creation date if was created locally.

    Args:
      person_list: the list of person objects
    Return:
      the max creation date if there is one. None, otherwise.
    """
    dates = [
        person.creation_date for person in person_list if person.creation_date
    ]
    if not dates:
        return None

    return max(dates)


def run(*, proxy: FlywheelProxy, user_list: List[ActiveUserEntry],
        admin_group: NACCGroup, authorization_map: AuthMap,
        registry: UserRegistry, notification_client: NotificationClient,
        force_notifications: bool):
    """Manages users based on user list.

    Uses AWS SES email templates: 'claim', 'followup-claim' and 'user-creation'

    Args:
      proxy: Flywheel proxy object
      user_list: the list of user objects from directory yaml file
      admin_group: the NACCGroup object representing the admin group
      authorization_map: the AuthMap object representing the authorization map
      registry: the user registry
      notification_client: client for sending notification emails
      force_notifications: whether to force send claim notification
    """
    for user_entry in user_list:
        if not user_entry.auth_email:
            log.info("user %s has no auth email", user_entry.email)
            continue

        person_list = registry.list(email=user_entry.auth_email)
        if not person_list:
            log.info('User %s not in registry', user_entry.email)
            add_to_registry(user_entry=user_entry, registry=registry)
            notification_client.send_claim_email(user_entry)
            log.info('Added user %s to registry using email %s',
                     user_entry.email, user_entry.auth_email)
            continue

        claimed = [person for person in person_list if person.is_claimed()]
        if claimed:
            log.info('User %s claimed in registry', user_entry.email)
            registry_id = get_registry_id(claimed)
            if not registry_id:
                log.error('User %s has no registry ID', user_entry.email)
                continue

            user = proxy.find_user(registry_id)
            if not user:
                log.info('User %s has flywheel user with ID: %s',
                         user_entry.email, registry_id)
                proxy.add_user(user_entry.register(registry_id).as_user())
                user = proxy.find_user(registry_id)
                if not user:
                    log.error('Failed to add user %s with ID %s',
                              user_entry.email, registry_id)
                    continue

                notification_client.send_creation_email(user_entry)
                log.info('Added user %s', user.id)

            log.info('Changing user %s email to %s', registry_id,
                     user_entry.email)
            update_email(proxy=proxy, user=user, email=user_entry.email)
            authorize_user(user=user,
                           admin_group=admin_group,
                           center_id=user_entry.adcid,
                           authorizations=user_entry.authorizations,
                           authorization_map=authorization_map)
            continue

        # registry record is not claimed
        log.info('User %s not claimed in registry', user_entry.email)

        if force_notifications:
            # At least initially, we need to force notifications on users
            # whose comanage records were created independently of this gear
            # So, sending the claim email instead of followup
            # TODO: change to send followup once backlog of users is cleared
            notification_client.send_claim_email(user_entry)

        if send_notification(user_entry=user_entry, person_list=person_list):
            notification_client.send_followup_claim_email(user_entry)


def send_notification(*, user_entry: ActiveUserEntry,
                      person_list: List[RegistryPerson]) -> bool:
    """Determines whether to send a notification based on time since date of
    registry record creation.

    Args:
      user_entry: the directory entry for user
      person_list: the registry person objects for user email
    Returns:
      True if number of days since creation is a multiple of 7. False, otherwise.
    """
    creation_date = get_creation_date(person_list)
    if not creation_date:
        log.warning('person record for %s has no creation date',
                    user_entry.email)
        return False

    time_since_creation = creation_date - datetime.now()
    return time_since_creation.days % 7 == 0
