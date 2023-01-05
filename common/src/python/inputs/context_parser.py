"""Gear context parser for user management."""
from flywheel_gear_toolkit import GearToolkitContext


def parse_config(*, gear_context: GearToolkitContext, filename: str):
    """Parses gear config for inputs."""
    args = dict()
    args['dry_run'] = gear_context.config.get("dry_run")
    args[filename] = gear_context.get_input_path(filename)
    
    return args
