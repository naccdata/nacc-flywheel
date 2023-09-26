"""Pulls SCAN metadata from LONI."""

import logging
import re
from io import BytesIO
from typing import Dict, List

import pandas as pd
from flywheel import FileSpec, Group, Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from tabular_data.site_table import SiteTable

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


def load_table(object_data) -> pd.DataFrame:
    """Converts the data to a DataFrame.

    Args:
      object_data: CSV file object from S3
    Returns:
      DataFrame containing data
    """
    return pd.read_csv(BytesIO(object_data))


def build_center_map(*, proxy: FlywheelProxy,
                     center_tag_pattern: str) -> Dict[str, Group]:
    """Builds a map from adcid to group.

    Args:
      center_tag_pattern:
      proxy: the flywheel instance proxy
    Returns:
      dictionary mapping from adcid to group
    """
    group_list = proxy.find_groups_by_tag(center_tag_pattern)
    if not group_list:
        log.warning('no centers found matching tag pattern %s',
                    center_tag_pattern)
        return {}

    center_map = {}
    for group in group_list:
        pattern = re.compile(center_tag_pattern)
        tags = list(filter(pattern.match, group.tags))
        for tag in tags:
            center_map[tag] = group

    return center_map


def split_table(*, proxy: FlywheelProxy, table: SiteTable,
                center_map: Dict[str, Group], filename: str,
                destination_label: str) -> None:
    """Splits the table by center ID and uploads to matching projects in FW.

    Args:
      proxy: the proxy object for Flywheel instance
      table: the table to split
      center_map: the map from adcid tags to center groups
      filename: the name of the file to use
      destination_label: the name of the project in center group
    """
    site_map = table.site_keys()
    for site_key, adcid in site_map.items():
        if not adcid:
            log.warning('Site %s has no matching ADCID', site_key)
            continue

        site_table = table.select_site(site_key)
        if not site_table:
            log.error('Unable to select site data for ADCID %s', adcid)
            continue

        center_group = center_map.get(f'adcid-{adcid}')
        if not center_group:
            log.error('Did not find group for ADCID %s', adcid)
            continue

        project = proxy.get_project(group=center_group,
                                    project_label=destination_label)
        if not project:
            log.error('Unable to access project %s', destination_label)
            continue

        log.info("Uploading file %s for adcid %s", filename, adcid)
        upload_file(project=project, site_table=site_table, file_name=filename)


def upload_file(*, project: Project, site_table: str, file_name: str) -> None:
    """Creates CSV file and uploads to Flywheel project.

    Args:
      project: the Flywheel project
      site_table: the CSV site data
      file_name: the name of the file on Flywheel
    """
    file_spec = FileSpec(name=file_name,
                         contents=site_table,
                         content_type='text/csv')
    project.upload_file(file_spec)


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

    center_map = build_center_map(proxy=proxy,
                                  center_tag_pattern=center_tag_pattern)

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

        table = SiteTable.create_from(load_table(data))
        if not table:
            log.error(
                'Table %s does not have a column with recognized center ID',
                table_name)
            continue

        log.info("Splitting table %s", table_name)
        split_table(proxy=proxy,
                    table=table,
                    center_map=center_map,
                    filename=filename,
                    destination_label=destination_label)
