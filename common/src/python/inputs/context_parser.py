"""Gear context parser for user management."""
from flywheel_gear_toolkit import GearToolkitContext  # type: ignore


def parse_config(*, gear_context: GearToolkitContext, filename: str):
    """Parses gear config for inputs."""
    args = {}
    args['dry_run'] = gear_context.config.get("dry_run")
    args[filename] = gear_context.get_input_path(filename)
    args['admin_group'] = gear_context.config.get('admin_group', 'nacc')

    return args
