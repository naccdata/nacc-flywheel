"""Run method for user management."""
import logging
from datetime import datetime
from typing import List, Optional

from centers.nacc_group import NACCGroup
from coreapi_client.models.identifier import Identifier
from flywheel import User
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from notifications.email import DestinationModel, EmailClient, TemplateDataModel
from users.authorizations import AuthMap, Authorizations
from users.nacc_directory import Credentials, UserDirectoryEntry
from users.user_registry import RegistryPerson, UserRegistry

log = logging.getLogger(__name__)


def add_user(proxy: FlywheelProxy, user_entry: UserDirectoryEntry,
             registry_id: str) -> User:
    """Creates a user object from the directory entry using the registry ID.

    The user ID and email must be the same when the user is created.
    So, email must be reset after the user is in Flywheel.

    Args:
      proxy: the proxy object for the FW instance
      user_entry: the directory entry for the user
      registry_id: the registry ID
    Returns:
      the flywheel User created from the directory entry
    """
    user_entry.set_credentials(
        credentials=Credentials(type='registry', id=registry_id))
    new_id = proxy.add_user(user_entry.as_user())
    user = proxy.find_user(user_entry.user_id)
    assert user, f"Failed to find user {new_id} that was just created"
    return user


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

    Args:
      user: the user
      center_id: the center of the user
      authorizations: the user authorizations
      authorization_map: the map from authorization to FW role
      admin_group: the admin group
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


def add_to_registry(*, user_entry: UserDirectoryEntry,
                    registry: UserRegistry) -> List[Identifier]:
    """Adds a user to the registry using the user entry data.

    Note: the comanage API was not returning any identifers last checked

    Args:
      user_entry: the user directory entry
      registry: the comanage registry
    Returns:
      the list of identifiers for the new registry record
    """
    identifier_list = registry.add(
        RegistryPerson.create(firstname=user_entry.first_name,
                              lastname=user_entry.last_name,
                              email=user_entry.email,
                              coid=str(registry.coid)))

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


def run(*, proxy: FlywheelProxy, user_list: List[UserDirectoryEntry],
        admin_group: NACCGroup, authorization_map: AuthMap,
        registry: UserRegistry, email_client: EmailClient):
    """Manages users based on user list.

    Uses AWS SES email templates: 'claim', 'followup-claim' and 'user-creation'

    Args:
      proxy: Flywheel proxy object
      user_list: the list of user objects from directory yaml file
      admin_group: the NACCGroup object representing the admin group
      skip_list: the list of user IDs to skip
      authorization_map: the AuthMap object representing the authorization map
      registry: the user registry
    """

    for user_entry in user_list:
        template_data = TemplateDataModel(firstname=user_entry.first_name,
                                          email_address=user_entry.email)
        destination = DestinationModel(to_addresses=[user_entry.email])

        person_list = registry.list(email=user_entry.email)
        if not person_list:
            add_to_registry(user_entry=user_entry, registry=registry)
            email_client.send(destination=destination,
                              template="claim",
                              template_data=template_data)
            log.info('Added user %s to registry', user_entry.email)
            continue

        claimed = [person for person in person_list if person.is_claimed()]
        if claimed:
            registry_id = get_registry_id(claimed)
            if not registry_id:
                log.error('User %s has no registry ID', user_entry.email)
                continue

            user = proxy.find_user(registry_id)
            if not user:
                try:
                    user = add_user(proxy=proxy,
                                    user_entry=user_entry,
                                    registry_id=registry_id)
                    email_client.send(destination=destination,
                                      template="user-creation",
                                      template_data=template_data)
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

        # if not claimed, send an email each week
        creation_date = get_creation_date(person_list)
        if not creation_date:
            log.warning('person record for %s has no creation date',
                        user_entry.email)
            continue

        time_since_creation = creation_date - datetime.now()
        if time_since_creation.days % 7 == 0:
            email_client.send(destination=destination,
                              template="followup-claim",
                              template_data=template_data)
