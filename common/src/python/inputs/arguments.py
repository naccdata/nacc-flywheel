"""Provides commandline argument parsing for script used in a gear that is
expecting a file and a dry run flag.

Includes gear flag so that script knows to look for arguments in gear
context.
"""
import argparse


def build_parser():
    """Builds and returns the argument parser."""
    parser = argparse.ArgumentParser(
        description="Create FW structures for Project")
    parser.add_argument('-g',
                        '--gear',
                        help='whether to read arguments from gear input',
                        default=False,
                        action='store_true')
    parser.add_argument('-d',
                        '--dry_run',
                        help='do a dry run to check input file',
                        default=False,
                        action='store_true')
    parser.add_argument('filename', help='path of input file')
    return parser
