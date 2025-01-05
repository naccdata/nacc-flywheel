import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from string import Template
from typing import Any, Dict, List, Literal, Optional, TypedDict

import yaml
from flywheel.file_spec import FileSpec
from flywheel.rest import ApiException
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from flywheel_adaptor.subject_adaptor import (
    ParticipantVisits,
    SubjectAdaptor,
    SubjectError,
)
from keys.keys import DefaultValues, FieldNames
from pydantic import BaseModel, Field
from utils.utils import update_file_info_metadata

log = logging.getLogger(__name__)


class VisitMapping(TypedDict):
    subject: SubjectAdaptor
    visits: ParticipantVisits


class LabelTemplate(BaseModel):
    """Defines a string template object for generating labels using input data
    from file records."""
    template: str
    transform: Optional[Literal['upper', 'lower']] = Field(default=None)

    def instantiate(self,
                    record: Dict[str, Any],
                    *,
                    environment: Optional[Dict[str, Any]] = None) -> str:
        """Instantiates the template using the data from the record matching
        the variables in the template. Converts the generated label to upper or
        lower case if indicated for the template.

        Args:
          record: data record
          env: environment variable settings
        Returns:
          the result of substituting values from the record.
        Raises:
          ValueError if a variable in the template does not occur in the record
        """
        result = self.template
        try:
            result = Template(self.template).substitute(record)
        except KeyError as error:
            if not environment:
                raise ValueError(
                    f"Error creating label, missing column {error}") from error

        if environment:
            try:
                result = Template(result).substitute(environment)
            except KeyError as error:
                raise ValueError(
                    f"Error creating label, missing column {error}") from error

        if self.transform == 'lower':
            return result.lower()

        if self.transform == 'upper':
            return result.upper()

        return result


class UploadTemplateInfo(BaseModel):
    """Defines model for label template input."""
    session: LabelTemplate
    acquisition: LabelTemplate
    filename: LabelTemplate


class RecordUploader(ABC):

    @abstractmethod
    def upload(self, records: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Uploads the records to acquisitions under the subject.

        Args:
          records: map from subject to list of records
        Returns:
          True if the file for each record is saved. False, otherwise.
        """


class JSONUploader(RecordUploader):
    """Generalizes upload of a record to an acquisition as JSON."""

    def __init__(self,
                 *,
                 project: ProjectAdaptor,
                 environment: Optional[Dict[str, Any]] = None,
                 template_map: UploadTemplateInfo) -> None:
        self.__project = project
        self.__session_template = template_map.session
        self.__acquisition_template = template_map.acquisition
        self.__filename_template = template_map.filename
        self.__environment = environment if environment else {}

    def upload(self, records: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Uploads the records to acquisitions under the subject.

        Args:
          records: map from subject to list of records
        Returns:
          True if the file for each record is successfully saved
        """
        success = True
        for subject_label, record_list in records.items():
            subject = self.__project.add_subject(subject_label)

            for record in record_list:
                try:
                    subject.upload_acquisition_file(
                        session_label=self.__session_template.instantiate(
                            record),
                        acquisition_label=self.__acquisition_template.
                        instantiate(record),
                        filename=self.__filename_template.instantiate(
                            record, environment=self.__environment),
                        contents=json.dumps(record),
                        content_type='application/json')
                except SubjectError as error:
                    raise UploaderError(error) from error
                except ValueError as error:
                    raise UploaderError(error) from error

        return success


class FormJSONUploader(RecordUploader):

    def __init__(self, project: ProjectAdaptor, module: str) -> None:
        self.__project = project
        self.__module = module
        self.__pending_visits: Dict[str, VisitMapping] = {}

    def __add_pending_visit(self, *, subject: SubjectAdaptor, filename: str,
                            file_id: str, input_record: Dict[str, Any]):
        """Add the visit to the list of visits pending for QC for the
        participant.

        Args:
            subject: Flywheel subject adaptor for the participant
            filename: Flywheel acquisition file name
            file_id: Flywheel acquisition file ID
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

    def __create_pending_visits_file(self) -> bool:
        """Create and upload a pending visits file for each participant module.
        These files will trigger the form-qc-coordinator gear for respective
        Flywheel subject.

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
            filename = f'{participant}-{self.__module}-visits-pending-qc-{timestamp}.yaml'  # NOQA E501
            file_spec = FileSpec(name=filename,
                                 contents=yaml_content,
                                 content_type='application/yaml')
            try:
                subject.upload_file(file_spec)
                log.info('Uploaded file %s to subject %s', filename,
                         participant)
            except SubjectError as error:
                success = False
                log.error(error)

        return success

    def __copy_qc_gear_metadata(self, *, error_log_name: str,
                                visit_file_name: str, subject: SubjectAdaptor,
                                session: str, acquisition: str) -> bool:
        """Copy existing QC gear metadata from visit file to error log file.

        Args:
            error_log_name: error log name for the visit
            visit_file_name: visit acquisition file file name
            subject: Flywheel subject adaptor
            session: Flywheel session label
            acquisition: Flywheel acquisition label

        Returns:
            bool: True if copying metadata successful
        """

        visit_file = subject.find_acquisition_file(
            session_label=session,
            acquisition_label=acquisition,
            filename=visit_file_name)
        if not visit_file:
            return False

        visit_file = visit_file.reload()
        error_log_file = self.__project.get_file(error_log_name)
        if not error_log_file or not visit_file.info:
            return False

        error_log_file = error_log_file.reload()
        qc_gear_metadata = visit_file.info.get('qc',
                                               {}).get(DefaultValues.QC_GEAR,
                                                       {})

        if not qc_gear_metadata:
            return False

        info = error_log_file.info if (error_log_file.info
                                       and 'qc' in error_log_file.info) else {
                                           'qc': {}
                                       }
        info['qc'][DefaultValues.QC_GEAR] = qc_gear_metadata

        try:
            error_log_file.update_info(info)
        except ApiException:
            return False

        return True

    def upload(
            self,
            participant_records: Dict[str, Dict[str, Dict[str, Any]]]) -> bool:
        """Converts a transformed CSV record to a JSON file and uploads it to
        the respective acquisition in Flywheel.

        - If the record already exists in Flywheel (duplicate), it will not be uploaded.
        - If the record is new/modified, upload it to Flywheel and update file metadata.

        Args:
            participant_visits: set of visits to upload, by participant

        Returns:
            bool: True if uploads are successful
        """

        success = True
        for subject_lbl, visits_info in participant_records.items():
            subject = self.__project.find_subject(subject_lbl)
            if not subject:
                log.info(
                    'NACCID %s does not exist in project %s/%s, creating a new subject',
                    subject_lbl, self.__project.group, self.__project.label)
                subject = self.__project.add_subject(subject_lbl)

            for log_file, record in visits_info.items():
                session_label = DefaultValues.SESSION_LBL_PRFX + \
                    record[FieldNames.VISITNUM]

                acq_label = record[FieldNames.MODULE].upper()

                visit_file_name = subject.get_acquisition_file_name(
                    session=session_label, acquisition=acq_label)
                try:
                    new_file = subject.upload_acquisition_file(
                        session_label=session_label,
                        acquisition_label=acq_label,
                        filename=visit_file_name,
                        contents=json.dumps(record),
                        content_type='application/json')
                except (SubjectError, TypeError) as error:
                    log.error(error)
                    success = False
                    continue

                # No error and no new file (i.e. duplicate file exists)
                if not new_file:
                    if not self.__copy_qc_gear_metadata(
                            error_log_name=log_file,
                            visit_file_name=visit_file_name,
                            subject=subject,
                            session=session_label,
                            acquisition=acq_label):
                        log.warning(
                            'Failed to copy QC gear metadata to error log file '
                            ' %s from existing visit file %s', log_file,
                            visit_file_name)
                    continue

                if not update_file_info_metadata(new_file, record):
                    success = False
                    continue

                self.__add_pending_visit(subject=subject,
                                         filename=visit_file_name,
                                         file_id=new_file.id,
                                         input_record=record)

        success = success and self.__create_pending_visits_file()
        return success


class UploaderError(Exception):
    pass
