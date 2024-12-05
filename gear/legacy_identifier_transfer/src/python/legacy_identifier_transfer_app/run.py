"""Entry script for legacy_identifier_transfer."""

import logging

from typing import Any, Dict, Optional, Tuple

from flywheel.models.group import Group
from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from identifiers.identifiers_lambda_repository import IdentifiersLambdaRepository, IdentifiersMode
from identifiers.identifiers_repository import IdentifierRepository, IdentifierRepositoryError
from identifiers.model import IdentifierObject
from lambdas.lambda_function import LambdaClient, create_lambda_client
from legacy_identifier_transfer_app.main import run
from inputs.parameter_store import ParameterStore

log = logging.getLogger(__name__)

# This is copied from identifier_lookup - should move to module?


def get_identifiers(identifiers_repo: IdentifierRepository,
                    adcid: int) -> Dict[str, IdentifierObject]:
    """Gets all of the Identifier objects from the identifier database using
    the RDSParameters.

    Args:
      rds_parameters: the credentials for RDS MySQL with identifiers database
      adcid: the center ID
    Returns:
      the dictionary mapping from PTID to Identifier object
    """
    identifiers = {}
    center_identifiers = identifiers_repo.list(adcid=adcid)
    if center_identifiers:
        # pylint: disable=(not-an-iterable)
        identifiers = {
            identifier.ptid: identifier
            for identifier in center_identifiers
        }

    return identifiers


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

    def __init__(self, admin_id: str, client: ClientWrapper, identifiers_mode: IdentifiersMode):
        super().__init__(client=client)
        self.__admin_id = admin_id
        self.__identifiers_mode: IdentifiersMode = identifiers_mode

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore]
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
        assert parameter_store, "Parameter store expected"

        client = GearBotClient.create(
            context=context, parameter_store=parameter_store)

        admin_id = context.config.get("admin_group", "nacc")
        mode = context.config.get("identifiers_mode", "dev")

        return legacy_identifier_transfer(
            admin_id=admin_id,
            client=client,
            identifiers_mode=mode
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

        adcid = self.__get_adcid(group_id)
        log.info(f"ADCID: {adcid}")

        if adcid is None:
            raise GearExecutionError('Unable to determine center ID for group')

        # Get all identifiers for adcid
        # try:
        #     identifiers = get_identifiers(
        #         identifiers_repo=IdentifiersLambdaRepository(
        #             client=LambdaClient(client=create_lambda_client()),
        #             mode=self.__identifiers_mode),
        #         adcid=adcid)
        # except IdentifierRepositoryError as error:
        #     raise GearExecutionError(error) from error

        # if not identifiers:
        #     raise GearExecutionError('Unable to load center participant IDs')

        run(proxy=self.proxy, adcid=adcid, identifiers={})


def main():
    """The Legacy NACCID transfer gear looks up all of the NACCIDs for
    a center. If the center does not already have a Subject with a given
    NACCID, it creates a new subject at that center for that participant.
    """

    # Strategy
    # pull information down from identifiers api then distribute it to center
    # runs on ingest-enrollment for a given center
    # ask db for all records that match adcid (list(adcid) in identifiers_lambda_repository.py)
    # take list of identifier objects
    # convert identifier objects into enrollment records
    # check if that enrollment record already exists on the center
    # if there's not an enrollment record for that naccid then create it using same logic as identifier-provisioning gear 2nd half

    GearEngine().create_with_parameter_store().run(
        gear_type=legacy_identifier_transfer)


if __name__ == "__main__":
    main()
