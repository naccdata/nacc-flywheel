"""Main function for running template push process."""
import logging
import re
import sys
from typing import Dict

from centers.center_group import CenterError, CenterGroup
from flywheel import Client
from flywheel_adaptor.flywheel_proxy import FlywheelProxy, ProjectAdaptor
from flywheel_gear_toolkit import GearToolkitContext
from inputs.context_parser import ConfigParseError, get_config
from inputs.parameter_store import ParameterError, ParameterStore
from metadata_app.main import run
from s3.s3_client import S3BucketReader

log = logging.getLogger(__name__)


def build_project_map(*, proxy: FlywheelProxy, center_tag_pattern: str,
                      destination_label: str) -> Dict[str, ProjectAdaptor]:
    """Builds a map from adcid to the project of center group with the given
    label.

    Args:
      proxy: the flywheel instance proxy
      center_tag_pattern: the regex for adcid-tags
      destination_label: the project of center to map to
    Returns:
      dictionary mapping from adcid to group
    """
    try:
        group_list = [
            CenterGroup.create_from_group(group=group, proxy=proxy)
            for group in proxy.find_groups_by_tag(center_tag_pattern)
        ]
    except CenterError as error:
        log.error('failed to create center from group: %s', error.message)
        return {}

    if not group_list:
        log.warning('no centers found matching tag pattern %s',
                    center_tag_pattern)
        return {}

    project_map = {}
    for group in group_list:
        project = group.find_project(destination_label)
        if not project:
            continue

        pattern = re.compile(center_tag_pattern)
        tags = list(filter(pattern.match, group.get_tags()))
        for tag in tags:
            project_map[tag] = project

    return project_map


def main():
    """Main method to distribute metadata from S3 bucket to center projects."""

    with GearToolkitContext() as gear_context:
        gear_context.init_logging()

        try:
            s3_param_path = get_config(gear_context=gear_context,
                                       key='s3_param_path')
            destination_label = get_config(gear_context=gear_context,
                                           key='destination_label')
            table_list = get_config(gear_context=gear_context,
                                    key='table_list')
        except ConfigParseError as error:
            log.error('Incomplete configuration: %s', error.message)
            sys.exit(1)

        apikey_path_prefix = gear_context.config.get("apikey_path_prefix",
                                                     "/prod/flywheel/gearbot")
        log.info('Running gearbot with API key from %s/apikey',
                 apikey_path_prefix)
        try:
            parameter_store = ParameterStore.create_from_environment()
            api_key = parameter_store.get_api_key(
                path_prefix=apikey_path_prefix)
            s3_parameters = parameter_store.get_s3_parameters(
                param_path=s3_param_path)
        except ParameterError as error:
            log.error('Parameter error: %s', error)
            sys.exit(1)

        dry_run = gear_context.config.get("dry_run", False)
        proxy = FlywheelProxy(client=Client(api_key), dry_run=dry_run)

        project_map = build_project_map(proxy=proxy,
                                        center_tag_pattern=r'adcid-\d+',
                                        destination_label=destination_label)
        if not project_map:
            log.error('No ADCID groups found')
            sys.exit(1)

        s3_client = S3BucketReader.create_from(s3_parameters)
        if not s3_client:
            log.error('Unable to connect to S3')
            sys.exit(1)

        log.info('Pulling metadata from S3 bucket %s into center %s projects',
                 s3_client.bucket_name, destination_label)
        if dry_run:
            log.info('Performing dry run')
        log.info('Including files %s', table_list)

        run(table_list=table_list,
            s3_client=s3_client,
            project_map=project_map,
            dry_run=dry_run)


if __name__ == "__main__":
    main()
