"""Defines project management computation."""

from projects.flywheel_proxy import FlywheelProxy
from projects.project import Project
from projects.project_mapping import ProjectMappingAdaptor


def run(*, api_key: str, project_list, dry_run: bool = False):
    """Parses file and does the work."""

    flywheel_proxy = FlywheelProxy(api_key=api_key, dry_run=dry_run)

    for project_doc in project_list:
        project = Project.create(project_doc)
        project_mapper = ProjectMappingAdaptor(project=project,
                                               flywheel_proxy=flywheel_proxy)
        project_mapper.create_project_pipelines()
