"""Utilities for managing connection to identifier database."""
from identifiers.identifiers_tables import metadata
from inputs.parameter_store import RDSParameters
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session(parameters: RDSParameters) -> sessionmaker[Session]:
    """Creates a session factory for the identifiers database.

    Args:
        parameters: the credentials for the database connection
    Returns:
        the Session for the identifier database at the URL
    """
    port = 3306
    database = 'identifier'
    database_url = (f"mysql+mysqlconnector://{parameters['user']}:"
                    f"{parameters['password']}@{parameters['host']}:"
                    f"{port}/{database}")
    engine = create_engine(url=database_url)
    metadata.create_all(engine)
    return sessionmaker(bind=engine)
