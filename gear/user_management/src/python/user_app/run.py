"""The run script for the user management gear."""

import logging
from io import StringIO
from typing import Any, List, Optional, Set

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from inputs.parameter_store import ParameterStore
from inputs.yaml import YAMLReadError, get_object_lists_from_stream, load_from_stream
from pydantic import ValidationError
from users.authorizations import AuthMap
from users.nacc_directory import UserDirectoryEntry, UserFormatError

from user_app.main import run

log = logging.getLogger(__name__)


def read_yaml_file(file_bytes: bytes) -> Optional[List[Any]]:
    """Reads user objects from YAML user file in the source project.

    Args:
      file_bytes: The file input stream
    Returns:
      List of user objects
    """
    entry_docs = get_object_lists_from_stream(
        StringIO(file_bytes.decode('utf-8')))
    if not entry_docs or not entry_docs[0]:
        return None

    return entry_docs[0]


class UserManagementVisitor(GearExecutionEnvironment):
    """Defines the user management gear."""

    def __init__(self, admin_id: str, client: ClientWrapper,
                 user_filepath: str, auth_filepath: str):
        super().__init__(client=client)
        self.__admin_id = admin_id
        self.__user_filepath = user_filepath
        self.__auth_filepath = auth_filepath

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'UserManagementVisitor':
        """Visits the gear context to gather inputs.

        Args:
            context (GearToolkitContext): The gear context.
        """
        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)

        user_filepath = context.get_input_path('user_file')
        if not user_filepath:
            raise GearExecutionError('No user directory file provided')
        auth_filepath = context.get_input_path('auth_file')
        if not auth_filepath:
            raise GearExecutionError('No user role file provided')

        return UserManagementVisitor(admin_id=context.config.get(
            "admin_group", "nacc"),
                                     client=client,
                                     user_filepath=user_filepath,
                                     auth_filepath=auth_filepath)

    def run(self, context: GearToolkitContext) -> None:
        """Executes the gear.

        Args:
            context: the gear execution context
        """
        assert self.__user_filepath, 'User directory file required'
        assert self.__auth_filepath, 'User role file required'
        assert self.__admin_id, 'Admin group ID required'

        auth_map = self.__get_auth_map(self.__auth_filepath)
        admin_group = self.admin_group(admin_id=self.__admin_id)
        admin_users = admin_group.get_group_users(access='admin')
        user_list = self.__get_user_list(
            self.__user_filepath,
            skip_list={user.id
                       for user in admin_users if user.id})
        run(proxy=self.proxy,
            user_list=user_list,
            admin_group=admin_group,
            authorization_map=auth_map)

    # pylint: disable=no-self-use
    def __get_user_list(self, user_file_path: str,
                        skip_list: Set[str]) -> List[UserDirectoryEntry]:
        """Get the user objects from the user file.

        Args:
            user_file_path: The path to the user file.
        Returns:
            List of user objects
        """
        try:
            with open(user_file_path, 'r', encoding='utf-8') as user_file:
                object_list = load_from_stream(user_file)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'No users read from user file {user_file_path}: {error}'
            ) from error
        if not object_list:
            raise GearExecutionError('No users found in user file')

        user_list = []
        for user_doc in object_list:
            try:
                user_entry = UserDirectoryEntry.create(user_doc)
            except UserFormatError as error:
                log.error('Error creating user entry: %s', error)
                continue
            if user_entry.user_id in skip_list:
                log.info('Skipping user: %s', user_entry.user_id)
                continue

            user_list.append(user_entry)

        return user_list

    # pylint: disable=no-self-use
    def __get_auth_map(self, auth_file_path: str) -> AuthMap:
        """Get the authorization map from the auth file.

        Args:
            auth_file_path: The path to the auth file.
        Returns:
            The authorization map
        """
        try:
            with open(auth_file_path, 'r', encoding='utf-8') as auth_file:
                auth_object = load_from_stream(auth_file)
                auth_map = AuthMap(project_authorizations=auth_object)
        except YAMLReadError as error:
            raise GearExecutionError('No authorizations read from auth file'
                                     f'{auth_file_path}: {error}') from error
        except ValidationError as error:
            raise GearExecutionError(
                f'Unexpected format in auth file {auth_file_path}: {error}'
            ) from error
        return auth_map


# pylint: disable=too-many-locals
def main() -> None:
    """Main method to manage users."""

    GearEngine.create_with_parameter_store().run(
        gear_type=UserManagementVisitor)


if __name__ == "__main__":
    main()
