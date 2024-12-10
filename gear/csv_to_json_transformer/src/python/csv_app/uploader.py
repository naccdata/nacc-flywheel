import json
import logging
from datetime import datetime
from typing import Any, Dict, List, TypedDict

import yaml
from flywheel.file_spec import FileSpec
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from flywheel_adaptor.subject_adaptor import (
    ParticipantVisits,
    SubjectAdaptor,
    SubjectError,
)
from keys.keys import DefaultValues, FieldNames
from utils.utils import update_file_info_metadata

log = logging.getLogger(__name__)


class VisitMapping(TypedDict):
    subject: SubjectAdaptor
    visits: ParticipantVisits


class JSONUploader():

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

    def upload_visits(self, participant_visits: Dict[str, List[Dict[str,
                                                                    Any]]]):
        """Converts a tranformed CSV record to a JSON file and uploads it to
        the respective acquisition in Flywheel.

        - If the record already exists in Flywheel (duplicate), it will not be uploaded.
        - If the record is new/modified, upload it to Flywheel and update file metadata.

        Args:
            participant_visits: set of visits to upload, by participant

        Returns:
            bool: True if uploads are successful
        """

        success = True
        for subject_lbl, visits in participant_visits.items():
            subject = self.__project.find_subject(subject_lbl)
            if not subject:
                log.info(
                    'NACCID %s does not exist in project %s/%s, creating a new subject',
                    subject_lbl, self.__project.group, self.__project.label)
                subject = self.__project.add_subject(subject_lbl)

            for visit in visits:
                session_label = DefaultValues.SESSION_LBL_PRFX + \
                    visit[FieldNames.VISITNUM]

                acq_label = visit[FieldNames.MODULE].upper()

                visit_file_name = f'{subject_lbl}-{session_label}-{acq_label}.json'
                try:
                    new_file = subject.upload_acquisition_file(
                        session_lbl=session_label,
                        acq_lbl=acq_label,
                        filename=visit_file_name,
                        contents=json.dumps(visit),
                        content_type='application/json')
                except (SubjectError, TypeError) as error:
                    log.error(error)
                    success = False
                    continue

                if not new_file:
                    continue

                if not update_file_info_metadata(new_file, visit):
                    success = False
                    continue

                self.__add_pending_visit(subject=subject,
                                         filename=visit_file_name,
                                         file_id=new_file.id,
                                         input_record=visit)

        success = success and self.__create_pending_visits_file()
        return success
