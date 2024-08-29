"""Main function for running template push process."""
import logging
from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from fw_client import FWClient
from gear_execution.gear_execution import (
    ClientWrapper,
    ContextClient,
    GearEngine,
    GearExecutionEnvironment,
)
from inputs.context_parser import get_api_key
from inputs.parameter_store import ParameterStore
from inputs.templates import get_template_projects

from template_app.main import run

log = logging.getLogger(__name__)


class TemplatingVisitor(GearExecutionEnvironment):
    """Visitor for the templating gear."""

    def __init__(self, admin_id: str, client: ClientWrapper, new_only: bool):
        super().__init__(client=client)
        self.__admin_id = admin_id
        self.__new_only = new_only

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'TemplatingVisitor':
        """Creates a templating execution visitor.

        Args:
            context: The gear context.
        Returns:
          the templating visitor
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        client = ContextClient.create(context=context)

        # Need fw-client because the SDK doesn't properly implement
        # ViewerApp type used for copying viewer apps from template projects.
        api_key = get_api_key(context)
        client.set_fw_client(
            FWClient(api_key=api_key, client_name="push-template"))

        return TemplatingVisitor(
            admin_id=context.config.get("admin_group", "nacc"),
            client=client,
            new_only=context.config.get("new_only", False))

    def run(self, context: GearToolkitContext) -> None:
        template_map = get_template_projects(group=self.admin_group(
            admin_id=self.__admin_id))
        run(proxy=self.proxy,
            center_tag_pattern=r'adcid-\d+',
            new_only=self.__new_only,
            template_map=template_map)


def main():
    """Main method to run template copy gear."""

    GearEngine().run(gear_type=TemplatingVisitor)


if __name__ == "__main__":
    main()
