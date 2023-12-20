"""Defines the NACCID lookup computation."""

import logging
from csv import DictReader, Sniffer
from typing import Dict, TextIO

from identifiers.model import Identifier
from outputs.errors import (ErrorWriter, empty_file_error, identifier_error,
                            missing_header_error)
from outputs.outputs import CSVWriter

log = logging.getLogger(__name__)

PTID = 'ptid'
NACCID = 'naccid'

def run(*, input_file: TextIO, identifiers: Dict[str, Identifier],
        output_file: TextIO, error_writer: ErrorWriter) -> bool:
    """Reads participant records from the input CSV file, finds the NACCID for
    each row from the ADCID and PTID, and outputs a CSV file with the NACCID
    inserted.

    If the NACCID isn't found for a row, an error is written to the error file.

    Note: this function assumes that the ADCID for each row is the same, and
    that the ADCID corresponds to the ID for the group where the file is
    located.
    The identifiers map should at least include Identifiers objects with this
    ADCID.

    Args:
      input_file: the data input stream
      identifiers: the map from PTID to Identifier object
      output_file: the data output stream
      error_writer: the error output writer
    Returns:
      True if there were IDs with no corresponding NACCID
    """

    sniffer = Sniffer()
    csv_sample = input_file.read(1024)
    if not csv_sample:
        error_writer.write(empty_file_error())
        return True

    if not sniffer.has_header(csv_sample):
        error_writer.write(missing_header_error())
        return True

    input_file.seek(0)
    detected_dialect = sniffer.sniff(csv_sample, delimiters=',')
    reader = DictReader(input_file, dialect=detected_dialect)
    assert reader.fieldnames, "File has header, reader should have fieldnames"

    header_fields = list(reader.fieldnames)
    if PTID not in header_fields:
        error_writer.write(missing_header_error())
        return True

    header_fields.append(NACCID)
    writer = CSVWriter(stream=output_file, fieldnames=header_fields)

    error_found = False
    for record in reader:
        assert record[PTID]
        identifier = identifiers.get(record[PTID])
        if not identifier:
            error_writer.write(
                identifier_error(line=reader.line_num, value=record[PTID]))
            error_found = True
            continue

        record[NACCID] = identifier.naccid
        writer.write(record)

    return error_found
