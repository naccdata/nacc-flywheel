# COPIED FROM ANOTHER PROJECT. MUST BE ALTERED FOR PULL SCAN PROJECT

"""Main function for running template push process."""
import logging
import sys

# from flywheel_gear_toolkit import GearToolkitContext
from scan_metadata_app.main import run

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    """
    Uses command line argument `gear` to indicate whether being run as a gear.
    If running as a gear, the arguments are taken from the gear context.
    Otherwise, arguments are taken from the command line.
    """
    # parser = build_base_parser()
    # args = parser.parse_args()

    # if args.gear:
    #     with GearToolkitContext() as gear_context:
    #         gear_context.init_logging()

    run()


if __name__ == "__main__":
    main()
