"""Module for converting a record in CSV to a JSON file."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, TypedDict

import yaml
from dates.form_dates import DEFAULT_DATE_FORMAT, convert_date
from flywheel import FileEntry
from flywheel.file_spec import FileSpec
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from flywheel_adaptor.subject_adaptor import (
    ParticipantVisits,
    SubjectAdaptor,
    SubjectError,
)
from keys.keys import DefaultValues, FieldNames
from outputs.errors import ListErrorWriter, unexpected_value_error

log = logging.getLogger(__name__)


class VisitMapping(TypedDict):
    subject: SubjectAdaptor
    visits: ParticipantVisits


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
        self.__pending_visits: Dict[str, VisitMapping] = {}
        self.system_errors = False

    def _update_file_metadata(self, file: FileEntry,
                              input_record: Dict[str, Any]) -> bool:
        """Set file modality and info.forms.json metadata.

        Args:
            file: Flywheel file object
            input_record: input visit data
        """

        # remove empty fields
        non_empty_fields = {
            k: v
            for k, v in input_record.items() if v is not None
        }
        info = {"forms": {"json": non_empty_fields}}
        try:
            file.update(modality='Form')
            file.update_info(info)
        except ApiException as error:
            log.error('Error in setting file %s metadata - %s', file.name,
                      error)
            return False

        return True

    def _is_duplicate_record(self, input_record: Dict[str, Any],
                             existing_file: FileEntry) -> bool:
        """Check whether the input data matches with an existing visit file.

        Args:
            input_record: input visit data
            existing_file: existing visit file

        Returns:
            True if a duplicate detected, else false
        """
        input_dict = sorted(input_record.items())
        try:
            currnt_dict = sorted(json.loads(existing_file.read()).items())
            return (input_dict == currnt_dict)
        except (json.JSONDecodeError, ApiException) as error:
            log.warning('Error in reading existing file - %s', error)
            return False

    def _add_pending_visit(self, *, subject: SubjectAdaptor, filename: str,
                           file_id: str, input_record: Dict[str, Any]):
        """Add the visit to the list of visits pending for QC for the
        participant.

        Args:
            subject: Flywheel subject adaptor for the participant
            filename: Flywheel aquisition file name
            file_id: Flywheel aquisition file ID
            input_record: input visit data
        """
        visit_mapping: VisitMapping
        subject_lbl = input_record[FieldNames.NACCID]
        if subject_lbl in self.__pending_visits:
            visit_mapping = self.__pending_visits[subject_lbl]
            visit_mapping['visits'].add_visit(
                filename=filename,
                file_id=file_id,
                visitdate=input_record[FieldNames.DATE_COLUMN])
        else:
            participant_visits = ParticipantVisits.create_from_visit_data(
                filename=filename, file_id=file_id, input_record=input_record)
            visit_mapping = {'subject': subject, 'visits': participant_visits}
            self.__pending_visits[subject_lbl] = visit_mapping

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
            acquisition = session.add_acquisition(label=acq_label)

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
        if existing_file and self._is_duplicate_record(input_record,
                                                       existing_file):
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
            log.error('Failed to upload file %s to %s/%s - %s',
                      visit_file_name, self.__project.group,
                      self.__project.label, error)
            self.system_errors = True
            return False

        acquisition = acquisition.reload()
        new_file = acquisition.get_file(visit_file_name)
        if not self._update_file_metadata(new_file, input_record):
            self.system_errors = True
            return False

        self._add_pending_visit(subject=subject,
                                filename=visit_file_name,
                                file_id=new_file.id,
                                input_record=input_record)
        return True

    def upload_pending_visits_file(self) -> bool:
        """Create and upload a pending visits file for each participant. These
        files will trigger the form-qc-coordinator gear for respective Flywheel
        subject.

        Returns:
            True if upload is successful, else False
        """

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        success = True
        for participant, visits_mapping in self.__pending_visits.items():
            subject = visits_mapping['subject']
            visits = visits_mapping['visits']
            yaml_content = yaml.safe_dump(
                data=visits.model_dump(serialize_as_any=True),
                allow_unicode=True,
                default_flow_style=False)
            filename = f'{participant}-visits-pending-qc-{timestamp}.yaml'
            file_spec = FileSpec(name=filename,
                                 contents=yaml_content,
                                 content_type='application/yaml')
            try:
                subject.upload_file(file_spec)
                log.info('Uploaded file %s to subject %s', filename,
                         participant)
            except SubjectError as error:
                success = False
                self.system_errors = True
                log.error('%s', error)

        return success
