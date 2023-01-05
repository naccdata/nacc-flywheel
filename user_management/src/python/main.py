
import logging

log = logging.getLogger(__name__)

def run(*, api_key: str, user_list, dry_run: bool = False):
    """does the work."""

    # flywheel_proxy = FlywheelProxy(api_key=api_key, dry_run=dry_run)
    # visitor = FlywheelProjectArtifactCreator(flywheel_proxy)
    for user_doc in user_list:
        # project = Project.create(user_doc)
        # project.apply(visitor)
        pass


