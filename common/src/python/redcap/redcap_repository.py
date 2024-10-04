import logging
from typing import Dict, Optional

from inputs.parameter_store import ParameterError, ParameterStore

from redcap.redcap_connection import (
    REDCapConnection,
    REDCapConnectionError,
    REDCapParameters,
)
from redcap.redcap_project import REDCapProject

log = logging.getLogger(__name__)


class REDCapParametersRepository:
    """Repository for REDCap connection credentials."""

    def __init__(self, redcap_params: Dict[str, REDCapParameters] = {}):
        self.__redcap_params = redcap_params

    @property
    def redcap_params(self) -> Dict[str, REDCapParameters]:
        return self.__redcap_params

    @classmethod
    def create_from_parameterstore(
            cls, param_store: ParameterStore,
            base_path: str) -> Optional['REDCapParametersRepository']:
        """Populate REDCap parameters repository from parameters stored at AWS
        parameter store.

        Args:
            param_store: SSM parameter store object
            base_path: base path at parameter store

        Return:
          REDCapParametersRepository(optional): repository object
        """
        try:
            redcap_params = param_store.get_all_redcap_parameters_at_path(
                base_path=base_path, prefix='pid_')
        except ParameterError as error:
            log.error('Error in populating REDCap parameters repository - %s',
                      error)
            return None

        return REDCapParametersRepository(redcap_params)

    def add_project_parameter(self, pid: int, parameters: REDCapParameters):
        """Add REDCap parameters to the repository.

        Args:
            pid: REDCap PID
            parameters: REDCap connection credentials
        """
        self.redcap_params[f'pid_{pid}'] = parameters

    def get_project_parameters(self, pid: int) -> Optional[REDCapParameters]:
        """Retrieve REDCap parameters for the given project.

        Args:
            pid: REDCap PID

        Returns:
            REDCapParameters(optional): REDCap connection credentials if found
        """
        return self.redcap_params.get(f'pid_{pid}', None)

    def get_redcap_project(self, pid: int) -> Optional[REDCapProject]:
        """Get an API connection to the REDCap project identified by the PID
        using parameters stored in the repo.

        Args:
            pid: REDCap PID

        Returns:
            REDCapProject(optional): REDCap project if connection is successful
        """

        redcap_params = self.get_project_parameters(pid)
        if not redcap_params:
            log.error(
                'Failed to find parameters for REDCap project %s in repository',
                pid)
            return None

        redcap_con = REDCapConnection.create_from(redcap_params)
        try:
            return redcap_con.get_project()
        except REDCapConnectionError as error:
            log.error(error)
            return None
