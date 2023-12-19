"""Utilities for managing connection to identifier database."""
from identifiers.identifiers_tables import metadata
from inputs.parameter_store import RDSParameters
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_from(parameters: RDSParameters) -> Session:
    """Creates an IdentifierRepository.

    Args:
        parameters: the credentials for the database connection
    Returns:
        the IdentifierRepository for the identifier database at the URL
    """
    port = 3306
    database = 'identifier'
    database_url = (f"mysql+mysqlconnector://{parameters['user']}:"
                    f"{parameters['password']}@{parameters['host']}:"
                    f"{port}/{database}")
    engine = create_engine(url=database_url)
    metadata.create_all(engine)
    return sessionmaker(bind=engine)()
