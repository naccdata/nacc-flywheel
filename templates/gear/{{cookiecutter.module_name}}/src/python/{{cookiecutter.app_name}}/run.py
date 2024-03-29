"""Entry script for {{cookiecutter.gear_name}}."""

import logging

from typing import Optional

from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, ContextClient,
                                           GearEngine,
                                           GearExecutionEnvironment)
from {{cookiecutter.app_name}}.main import run
from inputs.parameter_store import ParameterStore
from inputs.yaml import YAMLReadError, get_object_lists

log = logging.getLogger(__name__)

class ExampleGear(GearExecutionEnvironment):
    """Visitor for the templating gear."""

    def __init__(self, admin_id: str, client: ClientWrapper, new_only: bool):
        self.__admin_id = admin_id
        self.__client = client
        self.__new_only = new_only

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'ExampleGear':
        """Creates a gear execution object.

        Args:
            context: The gear context.
            parameter_store: The parameter store
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        client = ContextClient.create(context=context)

        return ExampleGear(
            admin_id=context.config.get("admin_group", "nacc"),
            client=client,
            new_only=context.config.get("new_only", False))

    def run(self, context: GearToolkitContext) -> None:
        proxy = self.__client.get_proxy()
        run(proxy=proxy,
            new_only=.self.__new_only)
        
def main():
    """Main method for {{cookiecutter.gear_name}}."""

    GearEngine().run(gear_type=ExampleGear)

if __name__ == "__main__":
    main()
