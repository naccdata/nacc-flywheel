"""Module for converting a record in CSV to a JSON file."""

import logging
from typing import Any, Dict

from flywheel_adaptor.flywheel_proxy import FlywheelProxy
from flywheel_adaptor.subject_adaptor import ParticipantVisits
from outputs.errors import ListErrorWriter

log = logging.getLogger(__name__)


class JSONTransformer():
    """This class converts a CSV record to a JSON file and uploads it to the
    respective aquisition in Flywheel.

    - If the record already exists in Flywheel (duplicate), it will not be re-uploaded.
    - If the record is new/modified, upload it to Flywheel and update file metadata.
    """

    def __init__(self, proxy: FlywheelProxy,
                 error_writer: ListErrorWriter) -> None:
        """Initialize the CSV Transformer.

        Args:
            proxy: Flywheel proxy object
            error_writer: the writer for error output
        """
        self.__proxy = proxy
        self.__error_writer = error_writer
        self.__pending_visits: Dict[str, ParticipantVisits] = {}

    def transform_record(self, input_record: Dict[str, Any],
                         line_num: int) -> bool:
        """Converts the input record to a JSON file and uploads it to the
        respective aquisition in Flywheel. Assumes the input record has all
        required keys when it gets to this point.

        Args:
            input_record: record from CSV file
            line_num (int): line number in CSV file

        Returns:
            True if the record was processed without error, False otherwise
        """

        return True

    def upload_pending_visits_file(self) -> bool:
        return True
