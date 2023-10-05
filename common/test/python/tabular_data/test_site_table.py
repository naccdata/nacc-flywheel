"""Tests for tabular_data.site_table.SiteTable."""
import csv
from io import StringIO

import pytest
from tabular_data.site_table import SiteTable


@pytest.fixture(scope="function")
def site_data_stream():
    data = [[u'SITE', u'BLAH'], [u'alpha(ADC1)', u'blah1'],
            [u'beta(ADC2)', u'blah2']]
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
    data = [[u'ADCID', u'BLAH'], [u'1', u'blah1'], [u'2', u'blah2']]
    stream = StringIO()
    writer = csv.writer(stream,
                        delimiter=',',
                        quotechar='\"',
                        quoting=csv.QUOTE_NONNUMERIC,
                        lineterminator='\n')
    writer.writerows(data)
    stream.seek(0)
    yield stream


class TestSiteTable:

    def test_create_from_site(self, site_data_stream):
        table = SiteTable.create_from(site_data_stream)
        assert table
        assert table.get_adcids() == {'1', '2'}
        assert table.select_site('1') == 'SITE,BLAH\nalpha(ADC1),blah1\n'
        assert table.select_site('2') == 'SITE,BLAH\nbeta(ADC2),blah2\n'

    def test_create_from_adcid(self, adcid_data_stream):
        table = SiteTable.create_from(adcid_data_stream)
        assert table
        assert table.get_adcids() == {'1', '2'}
        assert table.select_site('1') == 'ADCID,BLAH\n1,blah1\n'
        assert table.select_site('2') == 'ADCID,BLAH\n2,blah2\n'
