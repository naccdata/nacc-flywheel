"""The run script for the user management gear."""

import logging
from typing import List, Optional

from coreapi_client.api.default_api import DefaultApi
from coreapi_client.api_client import ApiClient
from coreapi_client.configuration import Configuration
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from inputs.parameter_store import ParameterError, ParameterStore
from inputs.yaml import YAMLReadError, load_from_stream
from notifications.email import EmailClient, create_ses_client
from pydantic import ValidationError
from users.authorizations import AuthMap
from users.nacc_directory import ActiveUserEntry, UserFormatError
from users.user_registry import UserRegistry

from user_app.main import run

log = logging.getLogger(__name__)


class UserManagementVisitor(GearExecutionEnvironment):
    """Defines the user management gear."""

    def __init__(self, admin_id: str, client: ClientWrapper,
                 user_filepath: str, auth_filepath: str, email_source: str,
                 comanage_config: Configuration, comanage_coid: int):
        super().__init__(client=client)
        self.__admin_id = admin_id
        self.__user_filepath = user_filepath
        self.__auth_filepath = auth_filepath
        self.__email_source = email_source
        self.__comanage_config = comanage_config
        self.__comanage_coid = comanage_coid

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
        assert parameter_store, "Parameter store expected"

        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)

        user_filepath = context.get_input_path('user_file')
        if not user_filepath:
            raise GearExecutionError('No user directory file provided')
        auth_filepath = context.get_input_path('auth_file')
        if not auth_filepath:
            raise GearExecutionError('No user role file provided')

        comanage_path = context.config.get('comanage_parameter_path')
        if not comanage_path:
            raise GearExecutionError("No CoManage parameter path")
        sender_path = context.config.get('sender_path')
        if not sender_path:
            raise GearExecutionError('No email sender parameter path')

        try:
            comanage_parameters = parameter_store.get_comanage_parameters(
                comanage_path)
            sender_parameters = parameter_store.get_notification_parameters(
                sender_path)
        except ParameterError as error:
            raise GearExecutionError(f'Parameter error: {error}') from error

        return UserManagementVisitor(
            admin_id=context.config.get("admin_group", "nacc"),
            client=client,
            user_filepath=user_filepath,
            auth_filepath=auth_filepath,
            email_source=sender_parameters['sender'],
            comanage_coid=int(comanage_parameters['coid']),
            comanage_config=Configuration(
                host=comanage_parameters['host'],
                username=comanage_parameters['username'],
                password=comanage_parameters['apikey']))

    def run(self, context: GearToolkitContext) -> None:
        """Executes the gear.

        Args:
            context: the gear execution context
        """
        assert self.__user_filepath, 'User directory file required'
        assert self.__auth_filepath, 'User role file required'
        assert self.__admin_id, 'Admin group ID required'
        assert self.__email_source, 'Sender email address required'

        auth_map = self.__get_auth_map(self.__auth_filepath)
        admin_group = self.admin_group(admin_id=self.__admin_id)
        user_list = self.__get_user_list(self.__user_filepath)
        with ApiClient(
                configuration=self.__comanage_config) as comanage_client:
            comanage_api = DefaultApi(comanage_client)
            run(proxy=self.proxy,
                user_list=user_list,
                admin_group=admin_group,
                authorization_map=auth_map,
                email_client=EmailClient(client=create_ses_client(),
                                         source=self.__email_source),
                registry=UserRegistry(api_instance=comanage_api,
                                      coid=self.__comanage_coid))

    def __get_user_list(self, user_file_path: str) -> List[ActiveUserEntry]:
        """Get the active user objects from the user file.

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
            if not user_doc.get('active'):
                continue

            try:
                user_entry = ActiveUserEntry.create(user_doc)
                user_list.append(user_entry)
            except UserFormatError as error:
                log.error('Error creating user entry: %s', error)
                continue

        return user_list

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


def main() -> None:
    """Main method to manage users."""

    GearEngine.create_with_parameter_store().run(
        gear_type=UserManagementVisitor)


if __name__ == "__main__":
    main()
