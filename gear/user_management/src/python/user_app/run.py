"""The run script for the user management gear."""

import logging
import sys
from io import StringIO
from typing import Any, List, Optional

from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (GearContextVisitor,
                                           GearExecutionEngine,
                                           GearExecutionError)
from inputs.parameter_store import ParameterStore
from inputs.yaml import (YAMLReadError, get_object_lists_from_stream,
                         load_from_stream)
from pydantic import ValidationError
from user_app.main import run
from users.authorizations import AuthMap

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


class UserManagementVisitor(GearContextVisitor):
    """Defines the user management gear."""

    def __init__(self):
        super().__init__()
        self.admin_group_id = None
        self.user_file_path = None
        self.auth_file_path = None

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visits the gear context to gather inputs.

        Args:
            context (GearToolkitContext): The gear context.
        """
        super().visit_context(context)
        if not self.client:
            raise GearExecutionError("Flywheel client required")
        self.admin_group_id = context.config.get("admin_group", "nacc")
        self.user_file_path = context.get_input_path('user_file')
        if not self.user_file_path:
            raise GearExecutionError('No user directory file provided')
        self.auth_file_path = context.get_input_path('auth_file')
        if not self.auth_file_path:
            raise GearExecutionError('No user role file provided')

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """dummy instantiation of abstract method."""

    def run(self, gear: 'GearExecutionEngine') -> None:
        """Executes the gear.

        Args:
            gear (GearExecutionEngine): The gear execution environment.
        """
        assert self.user_file_path, 'User directory file required'
        assert self.auth_file_path, 'User role file required'
        assert self.admin_group_id, 'Admin group ID required'
        proxy = self.get_proxy()
        admin_group = NACCGroup.create(proxy=proxy,
                                       group_id=self.admin_group_id)
        user_list = self.__get_user_list(self.user_file_path)
        auth_map = self.__get_auth_map(self.auth_file_path)
        admin_users = admin_group.get_group_users(access='admin')
        admin_set = {user.id for user in admin_users if user.id}
        run(proxy=proxy,
            user_list=user_list,
            admin_group=admin_group,
            skip_list=admin_set,
            authorization_map=auth_map)

    # pylint: disable=no-self-use
    def __get_user_list(self, user_file_path: str) -> List[Any]:
        """Get the user objects from the user file.

        Args:
            user_file_path: The path to the user file.
        Returns:
            List of user objects
        """
        try:
            with open(user_file_path, 'r', encoding='utf-8') as user_file:
                user_list = load_from_stream(user_file)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'No users read from user file {user_file_path}: {error}'
            ) from error
        if not user_list:
            raise GearExecutionError('No users found in user file')
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

    engine = GearExecutionEngine()
    try:
        engine.execute(UserManagementVisitor())
    except GearExecutionError as error:
        log.error(error)
        sys.exit(1)


if __name__ == "__main__":
    main()
