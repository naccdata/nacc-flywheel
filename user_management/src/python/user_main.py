import logging
from typing import List

import flywheel
from projects.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)


def run(*, proxy: FlywheelProxy, user_list, admin_users: List[flywheel.User]):
    """does the work."""

    for user in admin_users:
        log.info("User: %s", user)

    # visitor = FlywheelProjectArtifactCreator(flywheel_proxy)
    for user_doc in user_list:
        # project = Project.create(user_doc)
        # project.apply(visitor)
        pass
