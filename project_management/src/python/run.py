"""Reads a YAML file with project info.

project - name of project
centers - array of centers
    center-id - "ADC" ID of center (protected info)
    name - name of center
    is-active - whether center is active, has users if True
datatypes - array of datatype names (form, dicom)
published - boolean indicating whether data is to be published
"""
import logging
import sys

from flywheel_gear_toolkit import GearToolkitContext
from inputs.arguments import build_parser
from inputs.context_parser import parse_config
from inputs.environment import get_api_key
from inputs.yaml import get_object_list
from project_main import run

log = logging.getLogger(__name__)


def main():
    """Main method to create project from the adrc_program.yaml file."""

    parser = build_parser()
    args = parser.parse_args()

    if args.gear:
        filename = 'project_file'
        with GearToolkitContext() as gear_context:
            gear_context.init_logging()
            context_args = parse_config(gear_context=gear_context,
                                        filename=filename)
            dry_run = context_args['dry_run']
            project_file = context_args[filename]
    else:
        dry_run = args.dry_run
        project_file = args.filename

    project_list = get_object_list(project_file)
    if not project_list:
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        log.error('No API key: expecting FW_API_KEY to be set')
        sys.exit(1)

    run(api_key=api_key, project_list=project_list, dry_run=dry_run)


if __name__ == "__main__":
    main()
