"""Module defining utilities for gear execution."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from flywheel.client import Client
from flywheel_gear_toolkit import GearToolkitContext
from inputs.parameter_store import ParameterError, ParameterStore

log = logging.getLogger(__name__)


class GearExecutionError(Exception):
    """Exception class for gear execution errors."""


class GearExecutionVisitor(ABC):
    """Abstract class defining the gear execution visitor."""

    def __init__(self) -> None:
        self.client: Optional[Client] = None

    @abstractmethod
    def run(self, gear: 'GearExecutionEngine'):
        """Run the gear after initialization by visit methods.

        Args:
            gear: The execution environment for the gear.
        """

    @abstractmethod
    def visit_context(self, context: GearToolkitContext):
        """Visit method to be implemented by subclasses.

        Args:
            context: The gear context.
        """

    @abstractmethod
    def visit_parameter_store(self, parameter_store: ParameterStore):
        """Visit method to be implemented by subclasses.

        Args:
            parameter_store: The parameter store.
        """


class GearContextVisitor(GearExecutionVisitor):

    def __init__(self):
        self.client = None
        self.dry_run = False

    def visit_context(self, context: GearToolkitContext):
        self.client = context.client
        self.dry_run = context.config.get("dry_run", False)


class GearBotExecutionVisitor(GearContextVisitor):
    """Class implementing the gear execution visitor for GearBot."""

    def __init__(self):
        self.__apikey_path_prefix = None
        super().__init__()

    def visit_context(self, context: GearToolkitContext):
        """Visit method implementation for GearBot.

        Args:
            context: The gear context to visit.
        """
        super().visit_context(context)
        self.default_client = context.client
        if not self.default_client:
            raise GearExecutionError(
                "Flywheel client required to confirm gearbot access")

        self.__apikey_path_prefix = context.config.get("apikey_path_prefix",
                                                       None)
        if not self.__apikey_path_prefix:
            raise GearExecutionError("API key path prefix required")

    def visit_parameter_store(self, parameter_store: ParameterStore):
        """Visit method implementation for GearBot."""
        assert self.__apikey_path_prefix, "API key path prefix required"
        try:
            api_key = parameter_store.get_api_key(
                path_prefix=self.__apikey_path_prefix)
        except ParameterError as error:
            raise GearExecutionError("Parameter error: %s" % error)

        host = self.default_client.api_client.configuration.host  # type: ignore
        if api_key.split(':')[0] not in host:
            raise GearExecutionError('Gearbot API key does not match host')

        self.client = Client(api_key)


class GearExecutionEngine:
    """Class defining the gear execution engine."""

    def __init__(self,
                 context: Optional[GearToolkitContext] = None,
                 parameter_store: Optional[ParameterStore] = None):
        self.parameter_store = parameter_store
        self.context = context

    def execute(self, visitor: GearExecutionVisitor):
        """Execute the gear visitor.

        Args:
            visitor: The gear execution visitor.
        """
        with GearToolkitContext() as context:
            self.context = context
            context.init_logging()
            context.log_config()
            visitor.visit_context(context)
            if self.parameter_store:
                visitor.visit_parameter_store(self.parameter_store)
            visitor.run(self)
