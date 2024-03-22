"""Main function for running template push process."""
import logging
import sys

from centers.nacc_group import NACCGroup
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from fw_client import FWClient
from gear_execution.gear_execution import (GearContextVisitor,
                                           GearExecutionEngine,
                                           GearExecutionError)
from inputs.context_parser import get_api_key
from inputs.parameter_store import ParameterStore
from inputs.templates import get_template_projects
from template_app.main import run

log = logging.getLogger(__name__)


class TemplatingVisitor(GearContextVisitor):
    """Visitor for the templating gear."""

    def __init__(self):
        super().__init__()
        self.admin_group_id = None
        self.new_only = False
        self.fw_client = None

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visit context to accumulate inputs for the gear.

        Args:
            context: The gear context.
        """
        super().visit_context(context)
        if not self.client:
            raise GearExecutionError("Flywheel client required")

        # Need fw-client because the SDK doesn't properly implement
        # ViewerApp type used for copying viewer apps from template projects.
        api_key = get_api_key(context)
        self.fw_client = FWClient(api_key=api_key, client_name="push-template")

        self.admin_group_id = context.config.get("admin_group", "nacc")
        self.new_only = context.config.get("new_only", False)

    def get_proxy(self) -> FlywheelProxy:
        """Get a proxy that uses the FWClient for copying viewer apps.

        Returns:
            the flywheel proxy
        """
        assert self.client, "Flywheel client required"
        return FlywheelProxy(client=self.client,
                             fw_client=self.fw_client,
                             dry_run=self.dry_run)

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """dummy instantiation of absract method."""

    def run(self, engine: 'GearExecutionEngine') -> None:
        proxy = self.get_proxy()
        admin_group = self.get_admin_group()
        template_map = get_template_projects(group=admin_group)
        run(proxy=proxy,
            center_tag_pattern=r'adcid-\d+',
            new_only=self.new_only,
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

    engine = GearExecutionEngine()
    try:
        engine.execute(TemplatingVisitor())
    except GearExecutionError as error:
        log.error('Error: %s', error)
        sys.exit(1)


if __name__ == "__main__":
    main()
