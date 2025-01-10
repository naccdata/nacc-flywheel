"""Entry script for form_scheduler."""
import logging
from typing import List, Optional

from flywheel.rest import ApiException
from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
)
from inputs.parameter_store import ParameterStore

from form_scheduler_app.main import FormSchedulerQueue, run

log = logging.getLogger(__name__)


class FormSchedulerVisitor(GearExecutionEnvironment):
    """Visitor for the Form Scheduler gear."""

    def __init__(self, client: ClientWrapper,
                 queue_tags: List[str],
                 submission_pipeline: List[str],
                 module_order: List[str],
                 source_email: Optional[str] = None):
        super().__init__(client=client)

        self.__submission_pipeline = submission_pipeline
        self.__module_order = module_order
        self.__queue_tags = queue_tags
        self.__source_email = source_email

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'FormSchedulerVisitor':
        """Creates a gear execution object.

        Args:
            context: The gear context.
            parameter_store: The parameter store
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)

        submission_pipeline = context.config.get('submission_pipeline', None)
        accepted_modules = context.config.get('accepted_modules', None)
        prioritized_modules = context.config.get('prioritized_modules', None)
        queue_tags = context.config.get('queue_tags', None)
        source_email = context.config.get('source_email', None)

        if not submission_pipeline:
            raise GearExecutionError("No submission pipeline provided")
        if not accepted_modules:
            raise GearExecutionError("No accepted modules provided")
        if not queue_tags:
            raise GearExecutionError("No queue tags to search for provided")

        # figure out the module order based on accepted and prioritized modules
        prioritized_modules = prioritized_modules if prioritized_modules else []
        if not set(prioritized_modules).issubset(accepted_modules):
            raise GearExecutionError("prioritized_modules is not a subset of "
                                     + "accepted_modules")

        module_order = prioritized_modules.extend(
            [x for x in accepted_modules if x not in prioritized_modules])

        return FormSchedulerVisitor(
            client=client,
            submission_pipeline=
                [x.strip().lower() for x in submission_pipeline.split(',')],
            module_order=module_order,
            queue_tags=[x.strip().lower() for x in queue_tags.split(',')],
            source_email=source_email)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the Form Scheduler app."""
        try:
            dest_container = context.get_destination_container()
        except ApiException as error:
            raise GearExecutionError(
                f'Cannot find destination container: {error}') from error

        if not dest_container.container_type == 'project':
            raise GearExecutionError("Destination container must be a project")

        queue = FormSchedulerQueue(proxy=self.proxy,
                                   project_id=dest_container.id,
                                   module_order=self.__module_order,
                                   queue_tags=self.__queue_tags,
                                   source_email=self.__source_email)
        run(proxy=self.proxy,
            queue=queue,
            submission_pipeline=self.__submission_pipeline)


def main():
    """Main method for FormSchedulerVisitor.

    Queues files for the submission pipeline.
    """

    GearEngine.create_with_parameter_store().run(
        gear_type=FormSchedulerVisitor)


if __name__ == "__main__":
    main()
