"""Entry script for legacy_identifier_transfer."""

import logging

from typing import Optional

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    ContextClient,
    GearEngine,
    GearExecutionEnvironment,
    InputFileWrapper
)
from legacy_identifier_transfer_app.main import run
from inputs.parameter_store import ParameterStore

log = logging.getLogger(__name__)


class legacy_identifier_transfer(GearExecutionEnvironment):
    """Visitor for the Legacy identifier transfer gear."""

    def __init__(self, admin_id: str, client: ClientWrapper):
        super().__init__(client=client)

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'legacy_identifier_transfer':
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

        # file_input = InputFileWrapper.create(input_name='input_file',
        #                                      context=context)

        admin_id = context.config.get("admin_group", "nacc")

        return legacy_identifier_transfer(
            admin_id=admin_id,
            client=client,
            # file_input=file_input,
        )

    def run(self, context: GearToolkitContext) -> None:
        run(proxy=self.proxy)


def main():
    """The Legacy Identifier Transfer gear reads a CSV with rows of ADCIDs."""

    # Strategy
    # pull information down from identifiers api then distribute it
    # we have a gear that runs in ingest-enrollment for a given center
    # ask db for all records that match adcid (list(adcid) in identifiers_lambda_repository.py)
    # take list of identifier objects
    # convert identifier objects into enrollment records
    # check if that enrollment record already exists on the center
    # if there's not an enrollment record for that naccid then create it using same logic as identifier-provisioning gear 2nd half

    GearEngine().run(gear_type=legacy_identifier_transfer)


if __name__ == "__main__":
    main()
