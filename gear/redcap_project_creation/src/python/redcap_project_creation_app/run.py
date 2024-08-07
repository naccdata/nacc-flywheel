"""Entry script for REDCap Project Creation."""

import logging
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, GearBotClient,
                                           GearEngine,
                                           GearExecutionEnvironment,
                                           GearExecutionError)
from inputs.context_parser import ConfigParseError, get_config
from inputs.parameter_store import ParameterStore, REDCapParameters
from inputs.yaml import YAMLReadError, load_from_stream
from redcap.redcap_connection import REDCapSuperUserConnection
from redcap_project_creation_app.main import run

log = logging.getLogger(__name__)


class REDCapProjectCreation(GearExecutionEnvironment):
    """Visitor for the templating gear."""

    def __init__(self, client: ClientWrapper, parameter_store: ParameterStore):
        super().__init__(client=client)
        self.__param_store = parameter_store
        self.__out_file = 'redcap-projects.yml'

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'REDCapProjectCreation':
        """Creates a gear execution object.

        Args:
            context: The gear context.
            parameter_store: The parameter store
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        assert parameter_store, "Parameter store expected"

        client_wrapper = GearBotClient.create(context=context,
                                              parameter_store=parameter_store)

        return REDCapProjectCreation(client=client_wrapper,
                                     parameter_store=parameter_store)

    def run(self, context: GearToolkitContext) -> None:
        """Invoke the redcap project creation app.

        Args:
            context: the gear execution context

        Raises:
            GearExecutionError if errors occur while creating the projects
        """
        projects_file_path = context.get_input_path('projects_file')
        if not projects_file_path:
            raise GearExecutionError('No input file provided')

        try:
            with open(projects_file_path, 'r',
                      encoding='utf-8 ') as template_file:
                project_info = load_from_stream(template_file)
        except YAMLReadError as error:
            raise GearExecutionError(
                f'No REDCap project info read from input: {error}') from error

        if not project_info:
            raise GearExecutionError(
                'No REDCap project info read from input file')

        try:
            super_token_path: str = get_config(gear_context=context,
                                               key='super_token_path')
            token_path_prefix: str = get_config(gear_context=context,
                                                key='project_token_path',
                                                default='/redcap/aws')
        except ConfigParseError as error:
            raise GearExecutionError(
                f'Incomplete configuration: {error.message}') from error
        super_credentials = self.__param_store.get_parameters(
            param_type=REDCapParameters, parameter_path=super_token_path)
        redcap_super_con = REDCapSuperUserConnection.create_from(
            super_credentials)

        xml_template = None
        template_file_path = context.get_input_path('redcap_template')
        if template_file_path:
            with open(projects_file_path, 'r',
                      encoding='utf-8') as template_file:
                xml_template = template_file.read()

        errors, fw_metadata = run(parameter_store=self.__param_store,
                                  base_path=token_path_prefix,
                                  redcap_super_con=redcap_super_con,
                                  project_info=project_info,
                                  project_xml=xml_template)

        if fw_metadata:
            with context.open_output(self.__out_file,
                                     mode='w',
                                     encoding='utf-8') as out_file:
                out_file.write(fw_metadata)

        if errors:
            raise GearExecutionError(
                'Errors occurred while creating REDCap projects')


def main():
    """Main method for REDCap Project Creation."""

    GearEngine().run(gear_type=REDCapProjectCreation)


if __name__ == "__main__":
    main()
