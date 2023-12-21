"""Defines the table for the identifier database and maps the identifier class
to the table."""
from identifiers.model import Identifier
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.orm import registry

metadata = MetaData()

identifier_table = Table('identifier', metadata,
                         Column("nacc_id", Integer, primary_key=True),
                         Column("nacc_adc", Integer, nullable=False),
                         Column("adc_id", Integer, nullable=False),
                         Column("patient_id", String(10), nullable=False))

registry().map_imperatively(Identifier, identifier_table)
