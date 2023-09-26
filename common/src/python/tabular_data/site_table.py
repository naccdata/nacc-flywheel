"""Defines class for handling tabular data that needs to be split by site."""
from io import BytesIO
import logging
import re
from typing import Dict, Optional
import pandas as pd

from flywheel import FileSpec, Project

log = logging.getLogger(__name__)

class SiteTable:
    """Wrapper for data frame for table with Center ID column.

    Supports splitting table by Center ID. Center ID could be in column
    named ADCID or SITE.
    """

    def __init__(self, *, data: pd.DataFrame, site_id_column: str) -> None:
        self.__data_table = data
        self.__site_column = site_id_column

    @classmethod
    def create_from(cls, object_data: BytesIO) -> Optional['SiteTable']:
        """Creates table object and recognizes which column is used for site ID.

        Args:
          table_data: the data frame with data
        Returns:
          a wrapper object for the data frame or None if no center id column
        """
        table_data = pd.read_csv(object_data)
        
        if 'ADCID' in table_data.columns:
            site_id_name = 'ADCID'
        elif 'SITE' in table_data.columns:
            site_id_name = 'SITE'
        else:
            return None

        return SiteTable(data=table_data, site_id_column=site_id_name)

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

    def select_site(self, site_id) -> Optional[str]:
        """Selects the rows of the table for the site.

        Args:
          site_id: the ID of the table to select
        Returns:
          Data frame with rows of the table for the site_id
        """
        site_table = self.__data_table.loc[self.__data_table[self.__site_column] ==
                                     site_id]
        return site_table.to_csv(index=False)
    

def upload_split_table(*, table: SiteTable, project_map: Dict[str, Project], file_name: str) -> None:
    for site_key, project in project_map.items():
        if not project:
            log.warning('No project for site %s', site_key)
            continue

        site_table = table.select_site(site_key)
        if not site_table:
            log.error('Unable to select site data for %s', site_key)
            continue

        file_spec = FileSpec(name=file_name,
                        contents=site_table,
                        content_type='text/csv')
        project.upload_file(file_spec)
