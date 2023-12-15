"""Defines ADD DETAIL computation."""

import json
import logging
from csv import DictReader, DictWriter, Sniffer
from typing import Dict, TextIO

from identifiers.model import Identifier
from outputs.errors import (ErrorWriter, empty_file_error, identifier_error,
                            missing_header_error)

log = logging.getLogger(__name__)


def run(*, input_file: TextIO, identifiers: Dict[str, Identifier],
        output_file: TextIO, error_writer: ErrorWriter) -> bool:
    """Runs ADD DETAIL process.

    Args:
      proxy: the proxy for the Flywheel instance
      input_file: the data input stream
      output_file: the data output stream
      error_file: the error output stream
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
    if 'ptid' not in header_fields:
        # TODO record missing ID column error
        return True

    header_fields.append('naccid')
    writer = DictWriter(output_file, fieldnames=header_fields, dialect='unix')
    writer.writeheader()

    found_error = False
    for record in reader:
        assert record['ptid']
        identifier = identifiers.get(record['ptid'])
        if not identifier:
            error = identifier_error(line=reader.line_num,
                                     value=record['ptid'])
            found_error = True
            continue

        record['naccid'] = identifier.naccid
        writer.writerow(record)

    return found_error
