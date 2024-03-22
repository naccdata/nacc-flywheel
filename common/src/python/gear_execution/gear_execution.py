"""Module defining utilities for gear execution."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from centers.nacc_group import NACCGroup
from flywheel.client import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
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
    def run(self, engine: 'GearExecutionEngine') -> None:
        """Run the gear after initialization by visit methods.

        Note: expects both visit_context and visit_parameter_store to be called
        before this method.

        Args:
            engine: The execution environment for the gear.
        """

    @abstractmethod
    def visit_context(self, context: GearToolkitContext) -> None:
        """Visit method to be implemented by subclasses.

        Args:
            context: The gear context.
        """

    @abstractmethod
    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """Visit method to be implemented by subclasses.

        Args:
            parameter_store: The parameter store.
        """


class GearContextVisitor(GearExecutionVisitor):
    """Visitor that sets the client from the gear context."""

    def __init__(self):
        self.dry_run = False
        self.admin_group_id = None
        super().__init__()

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """Dummy instantiation of abstract method."""

    def get_proxy(self) -> FlywheelProxy:
        """Get the proxy for the gear execution visitor.

        Note: assumes that the client has been set by calling visit_context.

        Returns:
            The Flywheel proxy object.
        Raises:
            GearExecutionError if the client is not set.
        """
        if not self.client:
            raise GearExecutionError("Flywheel client required")
        return FlywheelProxy(client=self.client, dry_run=self.dry_run)

    def get_admin_group(self) -> NACCGroup:
        """Get the admin group.

        Note: visit_context must be called before this method.

        Returns:
            The NACC group object.
        Raises:
            GearExecutionError if the client and admin group ID are not set.
        """
        assert self.admin_group_id, "Admin group ID required"
        proxy = self.get_proxy()
        return NACCGroup.create(group_id=self.admin_group_id, proxy=proxy)

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visits the context and gathers the client and dry run settings.

        Args:
            context: The gear context.
        """
        self.client = context.client
        self.dry_run = context.config.get("dry_run", False)
        self.admin_group_id = context.config.get("admin_group", "nacc")


class GearBotExecutionVisitor(GearContextVisitor):
    """Class implementing the gear execution visitor for GearBot."""

    def __init__(self):
        self.__apikey_path_prefix = None
        self.__default_client = None
        super().__init__()

    def visit_context(self, context: GearToolkitContext) -> None:
        """Visit method implementation for GearBot.

        Args:
            context: The gear context to visit.
        """
        super().visit_context(context)
        self.__default_client = context.client
        if not self.__default_client:
            raise GearExecutionError(
                "Flywheel client required to confirm gearbot access")

        self.__apikey_path_prefix = context.config.get("apikey_path_prefix",
                                                       None)
        if not self.__apikey_path_prefix:
            raise GearExecutionError("API key path prefix required")

    def visit_parameter_store(self, parameter_store: ParameterStore) -> None:
        """Visit method implementation for GearBot.

        Note: visit_context must be called before this method.

        Args:
            parameter_store: The parameter store to visit.
        Raises:
            GearExecutionError: If the API key path prefix is not set.
        """
        assert self.__apikey_path_prefix, "API key path prefix required"
        try:
            api_key = parameter_store.get_api_key(
                path_prefix=self.__apikey_path_prefix)
        except ParameterError as error:
            raise GearExecutionError(f"Parameter error: {error}") from error

        api_client = self.__default_client.api_client  # type: ignore
        host = api_client.configuration.host
        if api_key.split(':')[0] not in host:
            raise GearExecutionError('Gearbot API key does not match host')

        self.client = Client(api_key)


# pylint: disable=too-few-public-methods
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
