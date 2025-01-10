"""Handles emailing user on completion of their submission pipeline."""
from flywheel.models.file_output import FileOutput  # type: ignore
from flywheel.models.project_output import ProjectOutput  # type: ignore

from inputs.parameter_store import URLParameter
from notifications.email import (
    BaseTemplateModel,
    DestinationModel,
    EmailClient,
)


class SubmissionCompleteTemplateModel(BaseTemplateModel):
    """Submission complete template model."""
    file_name: str
    portal_url: str
    center_name: str


def send_email(email_client: EmailClient,
               file: FileOutput,
               project: ProjectOutput,
               portal_url: URLParameter) -> None:  # type: ignore
    """Sends an email notifying user that their submission pipeline has
    completed.

    Args:
        email_client: EmailClient to send emails from
        file: The FileOutput; will pull details from it
        project: The ProjectOutput; will pull details from it
        portal_url: The portal URL
    """
    template_data = SubmissionCompleteTemplateModel(
        file_name=file.name,
        center_name=project.group,
        portal_url=portal_url['url'])

    destination = DestinationModel(to_addresses=[files.origin.id])

    email_client.send(configuration_set_name='submission-pipeline',
                      destination=destination,
                      template="submission-pipeline-complete",
                      template_data=template_data)
