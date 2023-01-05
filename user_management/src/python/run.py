"""The run script for the user management gear."""

import logging
import sys

from inputs.context_parser import parse_config
from inputs.environment import get_api_key
from flywheel_gear_toolkit import GearToolkitContext
from inputs.arguments import build_parser
from inputs.yaml import get_object_list
from main import run

log = logging.getLogger(__name__)

def main() -> None:
    """Check arguments."""

    parser = build_parser()
    args = parser.parse_args()

    if args.gear:
        filename = 'user_file'
        with GearToolkitContext() as gear_context:
            gear_context.init_logging()
            context_args = parse_config(gear_context=gear_context, filename=filename)
            dry_run = context_args['dry_run']
            user_file = context_args[filename]
    else:
        dry_run = args.dry_run
        user_file = args.filename

    user_list = get_object_list(user_file)
    if not user_list:
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        log.error('No API key: expecting FW_API_KEY to be set')
        sys.exit(1)

    run(api_key=api_key, user_list=user_list, dry_run=dry_run)


if __name__ == "__main__":
    main()
