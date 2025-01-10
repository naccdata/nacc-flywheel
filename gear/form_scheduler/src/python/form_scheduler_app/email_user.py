"""Handles emailing user on completion of their submission pipeline."""
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


def send_email(email_client: EmailClient, target_email: str,
               file_name: str, portal_url: URLParameter) -> None:  # type: ignore
    """Sends an email notifying user that their submission pipeline has
    completed.

    Args:
        email_client: EmailClient to send emails from
        target_email: Target email to send to
        file_name: Name of the file
        portal_url: The portal URL
    """
    template_data = SubmissionCompleteTemplateModel(
        file_name=file_name,
        email_address=target_email,
        portal_url=portal_url['url'])

    destination = DestinationModel(to_addresses=[target_email])

    email_client.send(configuration_set_name='submission-pipeline',
                      destination=destination,
                      template="submission-pipeline-complete",
                      template_data=template_data)
