"""Entry script for csv_center_splitter."""

import logging

from typing import Optional

from centers.nacc_group import NACCGroup
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, ContextClient,
                                           GearEngine,
                                           GearExecutionEnvironment)
from csv_center_splitter_app.main import run
from inputs.parameter_store import ParameterStore

log = logging.getLogger(__name__)

class csv_center_splitter(GearExecutionEnvironment):
    """Visitor for the templating gear."""

    def __init__(self, admin_id: str, client: ClientWrapper, new_only: bool):
        super().__init__(client=client, admin_id=admin_id)

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'csv_center_splitter':
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

        return csv_center_splitter(
            admin_id=context.config.get("admin_group", "nacc"),
            client=client,
            new_only=context.config.get("new_only", False))

    def run(self, context: GearToolkitContext) -> None:
        run(proxy=self.proxy,
            new_only=.self.__new_only)
        
def main():
    """Main method for csv_center_splitter."""

    GearEngine().run(gear_type=csv_center_splitter)

if __name__ == "__main__":
    main()
