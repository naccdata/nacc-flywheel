"""Utilities to pull NACCIDs."""

# based on https://github.com/naccdata/loni-table-data/blob/main/loni-api-pull/loni_table_data.py

from inputs.parameter_store import RDSParameters
from pandas import DataFrame, read_sql
from sqlalchemy import Engine, MetaData, Table, create_engine


def get_db_engine(parameter_values: RDSParameters, db_name: str) -> Engine:
    """Creates a sqlalchemy connector and Table object.

    Parameters
    ----------
    table_name : str
        Name of the database table to get

    Returns
    -------
    sqlalchemy.Table
        Table object for the requested table
    sqlalchemy.Connection
        MySQL sqlalchemy connector object for table queries
    """
    # Get connection parameters from ssm
    # parameter_values = get_parameters('/prod/mysql/')

    db_config = {
        'host': parameter_values['host'],
        'user': parameter_values['user'],
        'password': parameter_values['password'],
        'database': db_name,
        'port': 3306,
    }

    db_url = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    db_engine = create_engine(db_url)

    return db_engine


def get_nacc_identifiers() -> DataFrame:
    """Gets all ADCIDs and NACCIDs from RDS.

    Returns
    -------
    pd.DataFrame
        DataFrame of all ADCIDs and NACCIDs
    """
    # Get db connector
    db_engine = get_db_engine(parameter_values=parameters,
                              db_name='identifier')

    connector = db_engine.connect()

    metadata = MetaData()
    id_table = Table('identifier', metadata, autoload_with=db_engine)

    # Get identifiers from rds
    select_statement = id_table.select()

    df = read_sql(select_statement, connector)
    df = df[['nacc_id', 'adc_id']]

    # Rename columns to match LONI tables
    df.rename(columns={'nacc_id': 'NACCID', 'adc_id': 'ADCID'}, inplace=True)

    # Transform identifiers nacc_id to match standard NACCID
    df['NACCID'] = df['NACCID'].astype(str)
    df['NACCID'] = df['NACCID'].str.zfill(6)
    df['NACCID'] = 'NACC' + df['NACCID'].astype(str)

    # Close connection
    connector.close()

    return df
