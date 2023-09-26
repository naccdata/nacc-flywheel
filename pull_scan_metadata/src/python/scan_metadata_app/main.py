"""Pulls SCAN metadata from LONI."""

import logging
import re
from typing import Dict, List, Optional

from flywheel import Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from tabular_data.site_table import SiteTable, upload_split_table

log = logging.getLogger(__name__)


def read_data(*, s3_client, bucket_name: str, file_name: str):
    """Reads the file object from S3 with bucket name and file name.

    Args:
      s3_client: client for S3
      bucket_name: bucket prefix
      file_name: name of file
    """
    response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    return response['Body'].read()


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


def build_site_map(*, site_map: Dict[str, Optional[str]],
                   project_map: Dict[str, Project]) -> Dict[str, Project]:
    """Composes the site and project maps to create mapping that can be used to
    split a site table and upload partitions to projects.

    Args:
      proxy: the proxy object for Flywheel instance
      site_map: the map from site keys to adcids
      center_map: the map from adcid tags to center groups
      filename: the name of the file to use
      destination_label: the name of the project in center group
    """
    project_map = {}
    for site_key, adcid in site_map.items():
        if not adcid:
            log.warning('Site %s has no matching ADCID', site_key)
            continue

        project = project_map.get(f'adcid-{adcid}')
        if not project:
            log.error('Did not find project for ADCID %s', adcid)
            continue

        project_map[site_key] = project

    return project_map


def run(*, proxy: FlywheelProxy, table_list: List[str], s3_client,
        center_tag_pattern: str, bucket_name: str,
        destination_label: str) -> None:
    """Pulls SCAN metadata from S3, splits the data by center, and uploads the
    data to the center-specific FW project.

    Args:
      proxy: the proxy for the Flywheel instance
      table_list: the list of metadata table names
      s3_client: the S3 client for accessing files
      center_tag_pattern: regex pattern to match center tags
      bucket_name: name of the source bucket
      destination_label: label for destination project w/in each center group
    """

    project_map = build_project_map(proxy=proxy,
                                   center_tag_pattern=center_tag_pattern,
                                   destination_label=destination_label)

    for table_name in table_list:
        log.info("Downloading %s from S3", table_name)
        filename = f"{table_name}.csv"
        try:
            data = read_data(s3_client=s3_client,
                             bucket_name=bucket_name,
                             file_name=filename)
        except s3_client.exceptions.NoSuchKey:
            log.error('File %s not found in bucket %s', filename, bucket_name)
            continue
        except s3_client.exceptions.InvalidObjectState as obj_error:
            log.error('Unable to access file %s: %s', filename, obj_error)
            continue

        table = SiteTable.create_from(data)
        if not table:
            log.error(
                'Table %s does not have a column with recognized center ID',
                table_name)
            continue

        log.info("Splitting table %s", table_name)
        project_map = build_site_map(
            site_map=table.site_keys(),
            project_map=project_map,
        )
        upload_split_table(table=table,
                           project_map=project_map,
                           file_name=filename)
