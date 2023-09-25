"""Pulls SCAN metadata from LONI."""

import logging
import re
from io import BytesIO
from typing import Dict, List, Optional

import pandas as pd
from flywheel import FileSpec, Group, Project
from flywheel_adaptor.flywheel_proxy import FlywheelProxy

log = logging.getLogger(__name__)


class SCANTable:
    """Wrapper for data frame for SCAN metadata table.

    Supports splitting table by Center ID. Center ID could be in column
    named ADCID or SITE.
    """

    def __init__(self, *, data: pd.DataFrame, site_id_column: str) -> None:
        self.__data_table = data
        self.__site_column = site_id_column

    @classmethod
    def create_from(cls, table_data: pd.DataFrame) -> Optional['SCANTable']:
        """Recognizes which column is used for site ID.

        Args:
          table_data: the data frame with data
        Returns:
          a wrapper object for the data frame or None if no center id column
        """
        if 'ADCID' in table_data.columns:
            site_id_name = 'ADCID'
        elif 'SITE' in table_data.columns:
            site_id_name = 'SITE'
        else:
            return None

        return SCANTable(data=table_data, site_id_column=site_id_name)

    def site_keys(self) -> Dict[str, Optional[str]]:
        """Returns a map from site column values to the ADCID.

        Note: it is possible that an ADCID may not be found, in which case
        returns None.

        Returns:
          dictionary mapping from site column value to ADCID or None
        """
        site_ids = self.__data_table.loc(self.__site_column)
        return {site_key: self.get_adcid(site_key) for site_key in site_ids}

    def get_adcid(self, key) -> Optional[str]:
        """Returns the ADCID for the site column ID value.

        Args:
          key: the column key value
        Returns:
          the corresponding ADCID or None if none
        """
        if self.__site_column == 'ADCID':
            return key

        match = re.search(r"([^(]+)\(ADC\s?(\d+)\)", key)
        if not match:
            return None
        return match.group(2).strip()

    def select_site(self, site_id) -> pd.DataFrame:
        """Selects the rows of the table for the site.

        Args:
          site_id: the ID of the table to select
        Returns:
          Data frame with rows of the table for the site_id
        """
        return self.__data_table.loc[self.__data_table[self.__site_column] ==
                                     site_id]


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


def upload_file(*, project: Project, site_table: pd.DataFrame,
                file_name: str) -> None:
    """Creates CSV file and uploads to Flywheel project.

    Args:
      project: the Flywheel project
      site_table: the table for site data
      file_name: the name of the file on Flywheel
    """
    csv_data = site_table.to_csv(index=False)
    file_spec = FileSpec(name=file_name,
                         contents=csv_data,
                         content_type='text/csv')
    project.upload_file(file_spec)


# pylint: disable=(too-many-locals)
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

        table = SCANTable.create_from(load_table(data))
        if not table:
            log.error(
                'Table %s does not have a column with recognized center ID',
                table_name)
            continue

        log.info("Splitting table %s", table_name)
        site_map = table.site_keys()
        for site_key, adcid in site_map.items():
            if not adcid:
                log.warning('Site %s has no matching ADCID', site_key)
                continue

            site_table = table.select_site(site_key)
            center_group = center_map.get(f'adcid-{adcid}')
            if not center_group:
                log.error('Did not find group for ADCID %s', adcid)
                continue

            project = proxy.get_project(group=center_group,
                                        project_label=destination_label)
            if not project:
                log.error('Unable to access project %s', destination_label)
                continue

            upload_file(project=project,
                        site_table=site_table,
                        file_name=filename)
