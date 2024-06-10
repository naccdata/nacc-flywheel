"""Defines Identifier Provisioning."""

import logging
from typing import Any, Dict, Iterator, List, Optional, TextIO

from enrollment.enrollment_transfer import (
    EnrollmentRecord, NewGUIDRowValidator, NewPTIDRowValidator, TransferRecord,
    guid_available, has_known_naccid, is_new_enrollment, previously_enrolled)
from flywheel.file_spec import FileSpec
from flywheel_adaptor.flywheel_proxy import ProjectAdaptor
from identifiers.identifiers_repository import IdentifierRepository
from identifiers.model import CenterIdentifiers
from inputs.csv_reader import AggregateRowValidator, CSVVisitor, read_csv
from outputs.errors import (CSVLocation, ErrorWriter, FileError,
                            identifier_error, missing_header_error,
                            unexpected_value_error)
from outputs.outputs import JSONWriter

log = logging.getLogger(__name__)


class EnrollmentBatch:
    """Collects new Identifier objects for commiting to repository."""

    def __init__(self, repo: IdentifierRepository) -> None:
        self.__records: Dict[str, EnrollmentRecord] = {}
        self.__repo = repo

    def __iter__(self) -> Iterator[EnrollmentRecord]:
        """Returns an iterator to the the enrollment records in this batch."""
        return iter(self.__records.values())
    
    def __len__(self) -> int:
        """Returns the number of enrollment records in this batch."""
        return len(self.__records.values())

    def add(self, enrollment_record: EnrollmentRecord) -> None:
        """Adds the Identifier request object to this bacth.

        Args:
          identifier: the identifier request object
        """
        identifier = enrollment_record.center_identifier
        self.__records[identifier.ptid] = enrollment_record

    def commit(self) -> None:
        """Adds identifiers to the repository.

        Args:
        identifier_repo: the repository for identifiers
        identifiers: the list of identifiers to add
        """
        query = [
            record.center_identifier for record in self.__records.values()
        ]
        identifiers = self.__repo.create_list(query)
        log.info(f"created {len(identifiers)} new NACCIDs")
        if len(query) != len(identifiers):
            log.warning(
                f"expected {len(query)} new IDs, got {len(identifiers)}")

        for identifier in identifiers:
            record = self.__records.get(identifier.ptid)
            if record:
                record.naccid = identifier.naccid


def transfer_not_implemented_error(line: int,
                                   field: str = 'ptxfer',
                                   message: Optional[str] = None) -> FileError:
    """Creates a FileError for transfers."""
    error_message = message if message else 'Transfer not performed'
    return FileError(error_type='error',
                     error_code='transfer',
                     location=CSVLocation(column_name=field, line=line),
                     message=error_message)


class TransferVisitor(CSVVisitor):
    """Visitor for processing transfers into a center."""

    def __init__(self, error_writer: ErrorWriter, transfer_writer: JSONWriter,
                 repo: IdentifierRepository) -> None:
        self.__error_writer = error_writer
        self.__transfer_writer = transfer_writer
        self.__repo = repo
        self.__validator = NewPTIDRowValidator(repo, error_writer)

    def visit_header(self, header: List[str]) -> bool:
        """Checks that the header has expected column headings.

        Args:
          header: the list of column headings for file
        Returns:
          True if there are errors, False otherwise.
        """
        expected_columns = {
            'oldadcid', 'oldptid', 'naccidknwn', 'naccid', 'prevenrl'
        }
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visits enrollment/transfer data for single form."""
        if not self.__validator.check(row, line_num):
            return True

        new_identifiers = CenterIdentifiers(adcid=row['adcid'],
                                            ptid=row['ptid'])
        previous_identifiers = None
        naccid_identifier = None
        ptid_identifier = None
        guid_identifier = None

        if has_known_naccid(row):
            known_naccid = row['naccid']
            if known_naccid:
                naccid_identifier = self.__repo.get(naccid=known_naccid)
                if not naccid_identifier:
                    self.__error_writer.write(
                        identifier_error(field='naccid',
                                         value=known_naccid,
                                         line=line_num))
                    return True

        if guid_available(row):
            guid_identifier = self.__repo.get(guid=row['guid'])

            if not guid_identifier:
                self.__error_writer.write(
                    identifier_error(
                        field='guid',
                        value=row['guid'],
                        line=line_num,
                        message=f"No NACCID found for GUID {row['guid']}"))

            if naccid_identifier and guid_identifier != naccid_identifier:
                self.__error_writer.write(
                    FileError(error_type='error',
                              error_code='mismatched-id',
                              location=CSVLocation(line=line_num,
                                                   column_name='naccid'),
                              message=("mismatched NACCID for "
                                       f"Guid {row['guid']} "
                                       f"and provided NACCID {known_naccid}")))
                return True
            naccid_identifier = guid_identifier

        if previously_enrolled(row):
            previous_adcid = row['oldadcid']
            previous_ptid = row['oldptid']
            if previous_adcid and previous_ptid:
                ptid_identifier = self.__repo.get(adcid=previous_adcid,
                                                  ptid=previous_ptid)
                if not ptid_identifier:
                    self.__error_writer.write(
                        identifier_error(
                            value=previous_ptid,
                            line=line_num,
                            message=(
                                f"No NACCID found for ADCID {previous_adcid}, "
                                f"PTID {previous_ptid}")))
                    return True

                if naccid_identifier and ptid_identifier != naccid_identifier:
                    self.__error_writer.write(
                        FileError(error_type='error',
                                  error_code='mismatched-id',
                                  location=CSVLocation(line=line_num,
                                                       column_name='naccid'),
                                  message=("mismatched NACCID for "
                                           f"{previous_adcid}-{previous_ptid} "
                                           f"and {known_naccid}")))
                    return True
                naccid_identifier = ptid_identifier

                previous_identifiers = CenterIdentifiers(adcid=previous_adcid,
                                                         ptid=previous_ptid)

        naccid = None
        if naccid_identifier:
            naccid = naccid_identifier.naccid
        transfer_record = TransferRecord(
            date=row['frmdate_enrl'],
            initials=row['initials_enrl'],
            center_identifiers=new_identifiers,
            previous_identifiers=previous_identifiers,
            naccid=naccid)
        self.__transfer_writer.write(transfer_record.model_dump())

        self.__error_writer.write(
            transfer_not_implemented_error(field='enrltype',
                                           line=line_num,
                                           message="Transfer not performed"))
        return True


class NewEnrollmentVisitor(CSVVisitor):
    """A CSV Visitor class for processing new enrollment forms."""

    def __init__(self, error_writer: ErrorWriter, repo: IdentifierRepository,
                 batch: EnrollmentBatch) -> None:
        self.__batch = batch
        self.__validator = AggregateRowValidator([
            NewPTIDRowValidator(repo, error_writer),
            NewGUIDRowValidator(repo, error_writer)
        ])
        self.__error_writer = error_writer

    def visit_header(self, header: List[str]) -> bool:
        """Checks for ID columns in the header.

        Args:
          header: the list of header column names
        Returns:
          True if there is an error in the header. False, otherwise.
        """
        expected_columns = {'adcid', 'ptid', 'guid'}
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Adds an identifier object to the batch for creating new identifiers.

        Args:
          row: the dictionary for the row
          line_num: the line number for the row
        Returns:
          True if any of the validators fail. False, otherwise.
        """
        if not self.__validator.check(row, line_num):
            return True

        log.info('Adding new enrollment for (%s,%s)', row['adcid'],
                 row['ptid'])
        self.__batch.add(EnrollmentRecord.create_from(row))

        return False


class ProvisioningVisitor(CSVVisitor):
    """A CSV Visitor class for processing participant enrollment and transfer
    forms."""

    def __init__(self, error_writer: ErrorWriter,
                 transfer_writer: JSONWriter, batch: EnrollmentBatch,
                 repo: IdentifierRepository) -> None:
        self.__error_writer = error_writer
        self.__enrollment_visitor = NewEnrollmentVisitor(error_writer,
                                                         repo=repo,
                                                         batch=batch)
        self.__transfer_in_visitor = TransferVisitor(
            error_writer, repo=repo, transfer_writer=transfer_writer)

    def visit_header(self, header: List[str]) -> bool:
        """Prepares visitor to work with CSV file with given header.

        Args:
          header: the list of header names
        Returns:
          True if all of the visitors return True. False otherwise
        """
        expected_columns = {'module', 'enrltype'}
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return (self.__enrollment_visitor.visit_header(header)
                and self.__transfer_in_visitor.visit_header(header))

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Provisions a NACCID for the NACCID and PTID.

        First checks that the row has the form name as the module.
        Then checks form to determine processing.
        If form is
        - a new enrollment, then applies the NewEnrollmentVisitor.
        - a transfer out of the center, then applies the TransferOutVisitor.
        - a transfer into the center, then applies the TransferInVisitor

        Args:
          row: the dictionary for the CSV row (DictReader)
          line_num: the line number of the row
        Returns:
          True if a NACCID is provisioned without error, False otherwise
        """
        module_field = 'module'
        if row[module_field] != 'ptenrlv1':
            self.__error_writer.write(
                unexpected_value_error(field=module_field,
                                       value=row[module_field],
                                       line=line_num))
            return False

        if is_new_enrollment(row):
            return self.__enrollment_visitor.visit_row(row=row,
                                                       line_num=line_num)

        return self.__transfer_in_visitor.visit_row(row=row, line_num=line_num)


def run(*, input_file: TextIO, repo: IdentifierRepository, enrollment_project: ProjectAdaptor,
        error_writer: ErrorWriter, transfer_writer: JSONWriter):
    """Runs identifier provisioning process.

    Args:
      input_file: the data input stream
      form_name: the module designator for the form
      error_writer: the error output writer
    """
    enrollment_batch = EnrollmentBatch(repo=repo)
    has_error = read_csv(input_file=input_file,
                         error_writer=error_writer,
                         visitor=ProvisioningVisitor(
                             batch=enrollment_batch,
                             repo=repo,
                             error_writer=error_writer,
                             transfer_writer=transfer_writer))
    enrollment_batch.commit()
    
    for record in enrollment_batch:
        if not record.naccid:
            log.error('NACCID should exist for enrollment record %s/%s', record.center_identifier.adcid, record.center_identifier.ptid)
            continue

        if enrollment_project.find_subject(label=record.naccid):
            log.error('Subject with NACCID %s exists', record.naccid)
            continue

        subject = enrollment_project.add_subject(record.naccid)

        session = subject.sessions.find_first('label=enrollment_transfer')
        if not session:
            session = subject.add_session("enrollment_transfer")
        
        acquisition = session.acquisitions.find_first("label=enrollment")
        if not acquisition:
            acquisition = session.add_acquisition("enrollment")

        record_file_spec = FileSpec('enrollment.json', record.model_dump_json(exclude_none=True), 'application/json')
        acquisition.upload_file(record_file_spec)

    

    return has_error
