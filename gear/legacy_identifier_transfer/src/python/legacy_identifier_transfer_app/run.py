"""Entry script for legacy_identifier_transfer."""

import logging

from typing import Any, Optional, Tuple

from flywheel.models.group import Group
from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    ContextClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from legacy_identifier_transfer_app.main import run
from inputs.parameter_store import ParameterStore

log = logging.getLogger(__name__)

# This is copied from redcap_fw_transfer - should move to module?


def get_destination_group_and_project(dest_container: Any) -> Tuple[str, str]:
    """Find the flywheel group id and project id for the destination project.

    Args:
        dest_container: Flywheel container in which the gear is triggered

    Returns:
        Tuple[str, str]: group id, project id

    Raises:
        GearExecutionError if any error occurred while retrieving parent info
    """

    if not dest_container:
        raise GearExecutionError('Gear destination not set')

    if dest_container.container_type == 'project':
        project_id = dest_container.id
        group_id = dest_container.group
    elif dest_container.container_type in ('session', 'acquisition'):
        project_id = dest_container.parents.project
        group_id = dest_container.parents.group
    else:
        raise GearExecutionError(
            f'Invalid gear destination type {dest_container.container_type}')

    return group_id, project_id


class legacy_identifier_transfer(GearExecutionEnvironment):
    """Visitor for the Legacy identifier transfer gear."""

    def __init__(self, admin_id: str, client: ClientWrapper):
        super().__init__(client=client)
        self.__admin_id = admin_id

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

        admin_id = context.config.get("admin_group", "nacc")

        return legacy_identifier_transfer(
            admin_id=admin_id,
            client=client,
        )

    def __get_adcid(self, project_id: str) -> Optional[int]:
        try:
            admin_group = self.admin_group(admin_id=self.__admin_id)
            if not admin_group:
                raise GearExecutionError("No admin group found")
            return admin_group.get_adcid(project_id)
        except ApiException as error:
            log.error(f"Error getting ADCID: {error}")
            return None

    def run(self, context: GearToolkitContext) -> None:
        """Runs the legacy NACCID transfer gear.

        Args: context: The gear execution context 

        """

        assert context, "Gear context expected"

        # Get destination container
        try:
            dest_container = context.get_destination_container()
        except ApiException as error:
            raise GearExecutionError(
                f"Error getting destination container: {error}")

        if not dest_container:
            raise GearExecutionError("No destination container found")

        log.info(
            f"Destination container: {dest_container.label}")

        # Get Group and Project IDs, ADCID for group
        group_id, project_id = get_destination_group_and_project(
            dest_container)

        log.info(f"group_id: {group_id}")

        run(proxy=self.proxy, adcid=self.__get_adcid(group_id))


def main():
    """The Legacy Identifier Transfer gear reads a CSV with rows of ADCIDs."""

    # Strategy
    # pull information down from identifiers api then distribute it to center
    # runs on ingest-enrollment for a given center
    # ask db for all records that match adcid (list(adcid) in identifiers_lambda_repository.py)
    # take list of identifier objects
    # convert identifier objects into enrollment records
    # check if that enrollment record already exists on the center
    # if there's not an enrollment record for that naccid then create it using same logic as identifier-provisioning gear 2nd half

    GearEngine().run(gear_type=legacy_identifier_transfer)


if __name__ == "__main__":
    main()
