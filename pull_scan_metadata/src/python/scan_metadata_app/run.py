# COPIED FROM ANOTHER PROJECT. MUST BE ALTERED FOR PULL SCAN PROJECT

"""Main function for running template push process."""
import logging
import sys

from flywheel_gear_toolkit import GearToolkitContext
from scan_metadata_app.main import run


def main():
    with GearToolkitContext() as gear_context:
         gear_context.init_logging()

    run()


if __name__ == "__main__":
    main()
