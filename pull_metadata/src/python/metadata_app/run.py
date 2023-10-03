"""Main function for running template push process."""
import logging
import re
import sys
from typing import Dict

from flywheel import Client, Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_gear_toolkit import GearToolkitContext
from inputs.api_key import get_api_key
from inputs.context_parser import parse_config
from inputs.parameter_store import get_parameter_store
from s3.s3_client import get_s3_client
from metadata_app.main import run

log = logging.getLogger(__name__)


# TODO: link to CenterGroup (?)
def build_project_map(*, proxy: FlywheelProxy, center_tag_pattern: str,
                      destination_label: str) -> Dict[str, Project]:
    """Builds a map from adcid to the project of center group with the given
    label.

    Args:
      proxy: the flywheel instance proxy
      center_tag_pattern: the regex for adcid-tags
      destination_label: the project of center to map to
    Returns:
      dictionary mapping from adcid to group
    """
    group_list = proxy.find_groups_by_tag(center_tag_pattern)
    if not group_list:
        log.warning('no centers found matching tag pattern %s',
                    center_tag_pattern)
        return {}

    project_map = {}
    for group in group_list:
        project = proxy.get_project(group=group,
                                    project_label=destination_label)
        if not project:
            continue

        pattern = re.compile(center_tag_pattern)
        tags = list(filter(pattern.match, group.tags))
        for tag in tags:
            project_map[tag] = project

    return project_map


def main():
    """Main method to distribute metadata from S3 bucket to center
    projects."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()
        context_args = parse_config(gear_context=gear_context, filename=None)
        dry_run = context_args['dry_run']
        s3_param_path = gear_context.config.get('s3_param_path')
        if not s3_param_path:
            log.error('Incomplete configuration, no S3 path')
            sys.exit(1)

        bucket_name = gear_context.config.get('bucket_name')
        if not bucket_name:
            log.error('Incomplete configuration, no bucket name')
            sys.exit(1)

        destination_label = gear_context.config.get('destination_label')
        if not destination_label:
            log.error('Incomplete configuration, no destination label')
            sys.exit(1)

        table_list = gear_context.config.get('table_list')
        if not table_list:
            log.error('Incomplete configuration, no table names')
            sys.exit(1)
        
    parameter_store = get_parameter_store()
    if not parameter_store:
        log.error('Unable to connect to parameter store')
        sys.exit(1)

    api_key = get_api_key(parameter_store)
    if not api_key:
        log.error('No API key found. Check API key configuration')
        sys.exit(1)

    proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)
    project_map = build_project_map(proxy=proxy,
                                    center_tag_pattern=r'adcid-\d+',
                                    destination_label=destination_label)
    if not project_map:
        log.error('No ADCID groups found')
        sys.exit(1)

    s3_client = get_s3_client(store=parameter_store, param_path=s3_param_path)
    if not s3_client:
        log.error('Unable to connect to S3')
        sys.exit(1)

    log.info('Pulling metadata from S3 bucket %s into center %s projects', bucket_name, destination_label)
    log.info('Including files %s', table_list)

    run(table_list=table_list,
        s3_client=s3_client,
        bucket_name=bucket_name,
        project_map=project_map)


if __name__ == "__main__":
    main()
