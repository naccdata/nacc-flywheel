"""Module for converting a record in CSV to a JSON file."""
import json
import logging
from typing import Any, Dict

from dates.form_dates import DEFAULT_DATE_FORMAT, convert_date
from flywheel.file_spec import FileSpec
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from flywheel_adaptor.subject_adaptor import ParticipantVisits
from keys.keys import DefaultValues, FieldNames
from outputs.errors import ListErrorWriter, system_error, unexpected_value_error

log = logging.getLogger(__name__)


def is_duplicate_record(input_record: Dict[str, Any],
                        current_record: str) -> bool:
    """Check whether the input data matches with an existing visit file.

    Args:
        input_record: input visit data
        current_record: existing visit data

    Returns:
        True if a duplicate detected, else false
    """
    input_dict = sorted(input_record)
    currnt_dict = sorted(json.loads(current_record))
    return (input_dict == currnt_dict)


class JSONTransformer():
    """This class converts a CSV record to a JSON file and uploads it to the
    respective aquisition in Flywheel.

    - If the record already exists in Flywheel (duplicate), it will not be re-uploaded.
    - If the record is new/modified, upload it to Flywheel and update file metadata.
    """

    def __init__(self, project: ProjectAdaptor,
                 error_writer: ListErrorWriter) -> None:
        """Initialize the CSV Transformer.

        Args:
            proxy: Flywheel proxy object
            error_writer: the writer for error output
        """
        self.__project = project
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
        subject_lbl = input_record[FieldNames.NACCID]
        subject = self.__project.find_subject(subject_lbl)
        if not subject:
            log.info(
                'NACCID %s does not exist in project %s/%s, creating a new subject',
                subject_lbl, self.__project.group, self.__project.label)
            subject = self.__project.add_subject(subject_lbl)

        session_label = DefaultValues.SESSION_LBL_PRFX + \
            input_record[FieldNames.VISITNUM]
        session = subject.find_session(session_label)
        if not session:
            log.info(
                'Session %s does not exist in subject %s, creating a new session',
                session_label, subject_lbl)
            session = subject.add_session(session_label)

        acq_label = input_record[FieldNames.MODULE].upper()
        acquisition = session.acquisitions.find_first(f'label={acq_label}')
        if not acquisition:
            log.info(
                'Acquisition %s does not exist in session %s, '
                'creating a new acquisition', acq_label, session_label)
            acquisition = session.add_acquisition(f'label={acq_label}')

        normalized_date = convert_date(
            date_string=input_record[FieldNames.DATE_COLUMN],
            date_format=DEFAULT_DATE_FORMAT)  # type: ignore
        if not normalized_date:
            self.__error_writer.write(
                unexpected_value_error(
                    field=FieldNames.DATE_COLUMN,
                    value=input_record[FieldNames.DATE_COLUMN],
                    expected='',
                    message='Expected a valid date string',
                    line=line_num))
            return False

        input_record[FieldNames.DATE_COLUMN] = normalized_date

        visit_file_name = f'{subject_lbl}-{session_label}-{acq_label}.json'
        existing_file = acquisition.get_file(visit_file_name)
        if existing_file and is_duplicate_record(input_record,
                                                 existing_file.read()):
            log.warning(
                'Duplicate visit file %s already exists in project %s/%s',
                visit_file_name, self.__project.group, self.__project.label)
            return True  # returning true here since this is not a data error

        # if not duplicate, upload the visit
        visit_file_spec = FileSpec(name=visit_file_name,
                                   contents=json.dumps(input_record),
                                   content_type='application/json')

        try:
            acquisition.upload_file(visit_file_spec)
        except ApiException as error:
            message = 'Failed to upload file ' + \
                f'{visit_file_name} to {self.__project.group}/{self.__project.label}'
            self.__error_writer.write(system_error(message))
            log.error('%s - %s', message, error)
            return False

        return True

    def upload_pending_visits_file(self) -> bool:
        return True
