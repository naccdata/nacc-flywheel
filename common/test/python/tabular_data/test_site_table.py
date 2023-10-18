"""Tests for tabular_data.site_table.SiteTable."""
import csv
from io import StringIO

import pytest
from tabular_data.site_table import SiteTable


@pytest.fixture(scope="function")
def site_data_stream():
    """Create data stream for table with SITE column."""
    data = [['SITE', 'BLAH'], ['alpha(ADC1)', 'blah1'],
            ['beta(ADC2)', 'blah2']]
    stream = StringIO()
    writer = csv.writer(stream,
                        delimiter=',',
                        quotechar='\"',
                        quoting=csv.QUOTE_NONNUMERIC,
                        lineterminator='\n')
    writer.writerows(data)
    stream.seek(0)
    yield stream


@pytest.fixture(scope='function')
def adcid_data_stream():
    """Create data stream for table with ADCID column."""
    data = [['ADCID', 'BLAH'], ['1', 'blah1'], ['2', 'blah2']]
    stream = StringIO()
    writer = csv.writer(stream,
                        delimiter=',',
                        quotechar='\"',
                        quoting=csv.QUOTE_NONNUMERIC,
                        lineterminator='\n')
    writer.writerows(data)
    stream.seek(0)
    yield stream


# pylint: disable=no-self-use,redefined-outer-name
class TestSiteTable:
    """Tests for SiteTable."""

    def test_create_from_site(self, site_data_stream: StringIO):
        """Test create_from with table has SITE column."""
        table = SiteTable.create_from(object_data=site_data_stream, site_id_name='SITE')
        assert table
        assert table.get_adcids() == {'1', '2'}
        assert table.select_site('1') == 'SITE,BLAH\nalpha(ADC1),blah1\n'
        assert table.select_site('2') == 'SITE,BLAH\nbeta(ADC2),blah2\n'

    def test_create_from_adcid(self, adcid_data_stream: StringIO):
        """Test create_from with table that has ADCID column."""
        table = SiteTable.create_from(object_data=adcid_data_stream)
        assert table
        assert table.get_adcids() == {'1', '2'}
        assert table.select_site('1') == 'ADCID,BLAH\n1,blah1\n'
        assert table.select_site('2') == 'ADCID,BLAH\n2,blah2\n'
