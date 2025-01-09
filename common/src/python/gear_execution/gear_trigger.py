"""
Common code to handle triggering of gears.
"""
import logging
from flywheel.rest import ApiException
from json.decoder import JSONDecodeError
from pydantic import BaseModel, ConfigDict, ValidationError
from typing import List, Optional

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from gear_execution.gear_execution import GearExecutionError

log = logging.getLogger(__name__)


class GearConfigs(BaseModel):
    """Class to represent base gear configs"""
    model_config = ConfigDict(population_by_name=True)

    apikey_path_prefix: str
    dry_run: bool


class GearInfo(BaseModel):
    """Class to represent gear information."""
    model_config = ConfigDict(populate_by_name=True)

    gear_name: str
    configs: GearConfigs

    @classmethod
    def load_from_file(cls, configs_file_path: str) -> Optional[BaseModel]:
        """Load GearInfo from configs file

        Args:
            configs_file_path: The path to the configs JSON file
        Returns:
            The GearInfo object with gear name and config, if valid
        """
        try:
            with open(configs_file_path, mode='r', encoding='utf-8') as file_obj:
                config_data = json.load(file_obj)
        except (FileNotFoundError, JSONDecodeError, TypeError) as error:
            log.error('Failed to read the gear configs file %s - %s',
                      configs_file_path, error)
            return None

        try:
            gear_configs = cls.model_validate(config_data)
        except ValidationError as error:
            log.error('Gear config data not in expected format - %s', error)
            return None

        return gear_configs

    def check_instance_by_state(self,
                                proxy: FlywheelProxy,
                                states_list: List[str],
                                project_id: Optional[str] = None) -> bool:
        """Check if an instance of this gear matches the given state.

        Args:
            proxy: the proxy for the Flywheel instance
            states_list: List of states to check for
            project_id: The project ID to check for gears; if not specified,
                will match any gear instance in any project

        Returns:
            True if an instance of this gear matches the specified state,
            False otherwise.
        """
        search_str = f'gear_info.name=|{[self.gear_name]},state=|{states_list}'
        if project_id:
            search_str = f'parents.project={project_id},{search_str}'

        log.info(f"Checking job state with the following search str: {search_str}")
        return proxy.find_job(search_str)

    def trigger_gear(self,
                     proxy: FlywheelProxy,
                     **kwargs) -> str:
        """Trigger the gear.

        Args:
            proxy: the proxy for the Flywheel instance
            kwargs: keyword arguments to pass to gear.run, which include:
                inputs: The inputs to pass to the gear
                destination: The destination container
                analysis_label: The label of the analysis, if running an analysis gear
                tags: The list of tags to set for the job
        Returns:
            The job or analysis ID
        """
        try:
            gear = self.__proxy.lookup_gear(self.gear_name)
        except ApiException as error:
            raise GearExecutionError(error) from error

        return gear.run(config=self.configs.model_dump(),
                        **kwargs)
