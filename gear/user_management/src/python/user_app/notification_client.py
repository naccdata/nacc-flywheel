from notifications.email import DestinationModel, EmailClient, TemplateDataModel
from users.nacc_directory import ActiveUserEntry


class NotificationClient:
    """Wrapper for the email client to send email notifications for the user
    enrollment flow."""

    def __init__(self, email_client: EmailClient,
                 configuration_set_name: str) -> None:
        self.__client = email_client
        self.__configuration_set_name = configuration_set_name

    def __claim_template(self,
                         user_entry: ActiveUserEntry) -> TemplateDataModel:
        """Creates the email data template from the user entry for a registry
        claim email.

        The user entry must have the auth email address set.

        Args:
          user_entry: the user entry
        Returns:
          the template model with first name and auth email address
        """
        assert user_entry.auth_email, "user entry must have auth email"
        return TemplateDataModel(firstname=user_entry.first_name,
                                 email_address=user_entry.auth_email)

    def __claim_destination(self,
                            user_entry: ActiveUserEntry) -> DestinationModel:
        """Creates the email destination from the user entry for a registry
        claim email.

        The user entry must have the auth email address set.

        Args:
          user_entry: the user entry
        Returns:
          the destination model with auth email address.
        """
        assert user_entry.auth_email, "user entry must have auth email"
        return DestinationModel(to_addresses=[user_entry.auth_email])

    def send_claim_email(self, user_entry: ActiveUserEntry) -> None:
        """Sends the initial claim email to the auth email of the user.

        The user entry must have the auth email address set.

        Args:
          user_entry: the user entry for the user
        """
        self.__client.send(
            configuration_set_name=self.__configuration_set_name,
            destination=self.__claim_destination(user_entry),
            template="claim",
            template_data=self.__claim_template(user_entry))

    def send_followup_claim_email(self, user_entry: ActiveUserEntry) -> None:
        """Sends the followup claim email to the auth email of the user.

        The user entry must have the auth email address set.

        Args:
          user_entry: the user entry for the user
        """
        self.__client.send(
            configuration_set_name=self.__configuration_set_name,
            destination=self.__claim_destination(user_entry),
            template="followup-claim",
            template_data=self.__claim_template(user_entry))

    def send_creation_email(self, user_entry: ActiveUserEntry) -> None:
        """Sends the user creation email to the email of the user.

        Args:
          user_entry: the user entry for the user
        """
        self.__client.send(
            configuration_set_name=self.__configuration_set_name,
            destination=DestinationModel(to_addresses=[user_entry.email]),
            template="user-creation",
            template_data=TemplateDataModel(firstname=user_entry.first_name,
                                            email_address=user_entry.email))
