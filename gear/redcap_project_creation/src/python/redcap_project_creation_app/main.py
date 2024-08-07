"""Defines REDCap Project Creation."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import yaml
from centers.center_group import REDCapFormProject, REDCapProjectInput
from inputs.parameter_store import ParameterError, ParameterStore
from redcap.redcap_connection import (REDCapConnection, REDCapConnectionError,
                                      REDCapSuperUserConnection)

log = logging.getLogger(__name__)


def update_flywheel_metadata(updates: List[REDCapProjectInput]):
    """Update REDCap project info in center's metadata project.

    Args:
        updates: List of updates to be made
    """
    pass


def save_api_key(parameter_store: ParameterStore, base_path: str, api_key: str,
                 url: str) -> Optional[int]:
    """Save the REDCap API token for the created project in AWS parameter
    store.

    Args:
        parameter_store: AWS parameter store connection
        base_path: AWS parameter store path prefix
        api_key: REDCap API token
        url: REDCap API url

    Returns:
        Optional[int]: REDCap project PID
    """
    try:
        redcap_con = REDCapConnection(token=api_key, url=url)
    except REDCapConnectionError as error:
        log.error(error)
        return None

    try:
        parameter_store.set_redcap_project_prameters(base_path=base_path,
                                                     pid=redcap_con.pid,
                                                     url=url,
                                                     token=api_key)
    except ParameterError as error:
        log.error(error)
        return None

    return redcap_con.pid


def run(*, parameter_store: ParameterStore, base_path: str,
        redcap_super_con: REDCapSuperUserConnection, project_info: Dict[str,
                                                                        Any],
        project_xml: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Create REDCap projects using super API token, store project API token in
    AWS parameter store, update REDCap project info in Flywheel metadata.

    Args:
        parameter_store: AWS parameter store connection
        base_path (str): AWS parameter store path prefix
        redcap_super_con: REDCap super user API connection
        project_info: Info on which REDCap projects to be created
        project_xml: REDCap project XML template

    Returns:
        bool: True if there are no errors, else False
        Optional[str]: YAML text of REDCap project metadata
    """
    study_id = project_info['study-id']
    centers = project_info['centers']
    projects = project_info['projects']

    metadata_updates = []
    errors = False
    for center in centers:
        center_id = center['center-id']
        for project in projects:
            project_lbl = project['project-label']
            project_object = REDCapProjectInput(center_id=center_id,
                                                study_id=study_id,
                                                project_label=project_lbl,
                                                projects=[])

            modules = project['modules']
            for module in modules:
                redcap_prj_title = f"{center_id} {module['title']}"
                try:
                    api_key = redcap_super_con.create_project(
                        title=redcap_prj_title, project_xml=project_xml)
                except REDCapConnectionError as error:
                    log.error(error)
                    errors = True
                    continue

                redcap_pid = save_api_key(parameter_store, base_path, api_key,
                                          redcap_super_con.url)
                if redcap_pid:
                    module_obj = REDCapFormProject(redcap_pid=redcap_pid,
                                                   label=module['title'],
                                                   report_id=None)
                    project_object.projects.append(module_obj)
                else:
                    errors = True

            if len(project_object.projects) > 0:
                metadata_updates.append(project_object)

    yaml_text = None
    if len(metadata_updates) > 0:
        yaml_text = yaml.safe_dump(data=metadata_updates,
                                   allow_unicode=True,
                                   default_flow_style=False)
    return errors, yaml_text
