from typing import Dict, Optional

from inputs.parameter_store import ParameterStore
from redcap.redcap_connection import REDCapParameters


class REDCapRepository:
    """Repository for REDCap connection credentials."""

    redcap_params: Dict[str, REDCapParameters] = {}

    def populate_registry(self, param_store: ParameterStore, base_path: str):
        """Populate REDCap parameters repository from parameters stored at AWS
        parameter store.

        Args:
            param_store: SSM parameter store object
            base_path: base path at parameter store

        Raises:
          ParameterError: if errors occur while retrieving parameters
        """
        self.redcap_params = param_store.get_all_redcap_parameters_at_path(
            base_path=base_path, prefix='pid_')

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
