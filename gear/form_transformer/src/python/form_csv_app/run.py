"""Entry script for Form CSV to JSON Transformer."""

import logging
from typing import Dict, Optional

from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from flywheel_gear_toolkit.context.context import GearToolkitContext
from gear_execution.gear_execution import (
    ClientWrapper,
    GearBotClient,
    GearEngine,
    GearExecutionEnvironment,
    GearExecutionError,
    InputFileWrapper,
)
from inputs.parameter_store import ParameterStore
from outputs.errors import ListErrorWriter
from pydantic import ValidationError
from transform.transformer import FieldTransformations, TransformerFactory

from form_csv_app.main import run

log = logging.getLogger(__name__)


class FormCSVtoJSONTransformer(GearExecutionEnvironment):
    """Visitor for the templating gear."""

    def __init__(self, client: ClientWrapper, file_input: InputFileWrapper,
                 transform_input: Optional[InputFileWrapper],
                 hierarchy_labels: Dict[str, str]) -> None:
        self.__client = client
        self.__file_input = file_input
        self.__hierarchy_labels = hierarchy_labels
        self.__transform_input = transform_input

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'FormCSVtoJSONTransformer':
        """Creates a gear execution object.

        Args:
            context: The gear context.
            parameter_store: The parameter store

        Returns:
          the execution environment

        Raises:
          GearExecutionError if any expected inputs are missing
        """
        assert parameter_store, "Parameter store expected"

        client = GearBotClient.create(context=context,
                                      parameter_store=parameter_store)

        file_input = InputFileWrapper.create(input_name='input_file',
                                             context=context)
        assert file_input, "create raises exception if missing expected input"

        transform_input = InputFileWrapper.create(input_name='transform_file',
                                                  context=context)

        hierarchy_labels = context.config.get('hierarchy_labels')
        if not hierarchy_labels:
            raise GearExecutionError("Expecting non-empty label templates")

        return FormCSVtoJSONTransformer(client=client,
                                        file_input=file_input,
                                        transform_input=transform_input,
                                        hierarchy_labels=hierarchy_labels)

    def run(self, context: GearToolkitContext) -> None:
        """Runs the CSV to JSON Transformer app.

        Args:
          context: the gear execution context
        """

        proxy = self.__client.get_proxy()
        file_id = self.__file_input.file_id
        try:
            file = proxy.get_file(file_id)
        except ApiException as error:
            raise GearExecutionError(
                f'Failed to find the input file: {error}') from error

        project = proxy.get_project_by_id(file.parents.project)
        if not project:
            raise GearExecutionError(
                f'Failed to find the project with ID {file.parents.project}')

        with open(self.__file_input.filepath, mode='r',
                  encoding='utf-8') as csv_file:
            error_writer = ListErrorWriter(container_id=file_id,
                                           fw_path=proxy.get_lookup_path(file))
            success = run(input_file=csv_file,
                          destination=ProjectAdaptor(project=project,
                                                     proxy=proxy),
                          transformer_factory=self.__build_transformer(
                              self.__transform_input),
                          error_writer=error_writer)

            context.metadata.add_qc_result(self.__file_input.file_input,
                                           name='validation',
                                           state='PASS' if success else 'FAIL',
                                           data=error_writer.errors())

            context.metadata.add_file_tags(self.__file_input.file_input,
                                           tags=context.manifest.get(
                                               'name', 'form-transformer'))

    def __build_transformer(
            self, transformer_input: Optional[InputFileWrapper]
    ) -> TransformerFactory:
        """Loads the transformation file and creates a transformer factory.

        If the input is None, returns a factory for empty transformations.
        Otherwise, loads the file as a FileTransformations object and creates
        a factory using those.

        Args:
          transformer_input: the input file wrapper
        Returns:
          the TransformerFactory for the input
        """
        if not transformer_input:
            return TransformerFactory(FieldTransformations())

        with open(transformer_input.filepath, mode='r',
                  encoding='utf-8') as json_file:
            try:
                return TransformerFactory(
                    FieldTransformations.model_validate_json(json_file.read()))
            except ValidationError as error:
                raise GearExecutionError('Error reading transformation file'
                                         f'{error}') from error


def main():
    """Main method for Form CSV to JSON Transformer."""

    GearEngine().run(gear_type=FormCSVtoJSONTransformer)


if __name__ == "__main__":
    main()
