"""Handles emailing user on completion of their submission pipeline."""
import logging

from flywheel.models.file_output import FileOutput  # type: ignore
from flywheel.models.project_output import ProjectOutput  # type: ignore
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from inputs.parameter_store import URLParameter
from notifications.email import (
    BaseTemplateModel,
    DestinationModel,
    EmailClient,
)

log = logging.getLogger(__name__)


class SubmissionCompleteTemplateModel(BaseTemplateModel):
    """Submission complete template model."""
    first_name: str
    file_name: str
    center_name: str
    portal_url: str


def send_email(proxy: FlywheelProxy, email_client: EmailClient,
               file: FileOutput, project: ProjectOutput,
               portal_url: URLParameter) -> None:  # type: ignore
    """Sends an email notifying user that their submission pipeline has
    completed.

    Args:
        proxy: the proxy for the Flywheel instance
        email_client: EmailClient to send emails from
        file: The FileOutput; will pull details from it
        project: The ProjectOutput; will pull details from it
        portal_url: The portal URL
    """
    # If the user does not exist, we cannot send an email
    user = proxy.find_user(file.origin.id)
    if not user:
        log.warning(
            "Owner of the file does not match a user on Flywheel, will " +
            "not send completion email")
        return

    # lookup the user's email; if not set fall back to the file origin id
    target_email = user.email if user.email else file.origin.id

    # look up the center name
    group = proxy.find_group(project.group)
    group_label = "your center" if not group else group.label

    template_data = SubmissionCompleteTemplateModel(
        first_name=user.firstname,  # type: ignore
        file_name=file.name,
        center_name=group_label,
        portal_url=portal_url['url'])

    destination = DestinationModel(to_addresses=[target_email])

    email_client.send(configuration_set_name='submission-pipeline',
                      destination=destination,
                      template="submission-pipeline-complete",
                      template_data=template_data)
