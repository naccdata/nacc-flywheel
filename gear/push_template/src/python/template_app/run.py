"""Main function for running template push process."""
import logging
from typing import Optional

from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from fw_client import FWClient
from gear_execution.gear_execution import (ClientWrapper, ContextClient,
                                           GearEngine,
                                           GearExecutionEnvironment)
from inputs.context_parser import get_api_key
from inputs.parameter_store import ParameterStore
from inputs.templates import get_template_projects
from template_app.main import run

log = logging.getLogger(__name__)


class TemplatingVisitor(GearExecutionEnvironment):
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
        proxy = self.__client.get_proxy()
        admin_group = NACCGroup.create(proxy=proxy, group_id=self.__admin_id)
        template_map = get_template_projects(group=admin_group)
        run(proxy=proxy,
            center_tag_pattern=r'adcid-\d+',
            new_only=self.__new_only,
            template_map=template_map)


def main():
    """Main method to copy template projects to center projects.

    Arguments are taken from the gear context.
    Arguments are
      * admin_group: the name of the admin group in the instance
        default is `nacc`
      * dry_run: whether to run as a dry run, default is False
      * new_only: whether to only run on groups tagged as new

    Gear pushes contents from the template projects in the admin group.
    These projects are expected to be named `<datatype>-<stage>-template`,
    where `datatype` is one of the datatypes that occur in the project file,
    and `stage` is one of 'accepted', 'ingest' or 'retrospective'.
    (These are pipeline stages that can be created for the project)
    """

    GearEngine().run(gear_type=TemplatingVisitor)


if __name__ == "__main__":
    main()
