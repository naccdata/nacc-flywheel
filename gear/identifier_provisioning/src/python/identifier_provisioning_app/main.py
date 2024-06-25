"""Defines Identifier Provisioning."""

import logging
from typing import Any, Dict, Iterator, List, TextIO

from enrollment.enrollment_project import EnrollmentProject, TransferInfo
from enrollment.enrollment_transfer import (
    CenterValidator, EnrollmentRecord, NewGUIDRowValidator,
    NewPTIDRowValidator, TransferRecord, guid_available, has_known_naccid,
    is_new_enrollment, previously_enrolled)
from gear_execution.gear_execution import GearExecutionError
from identifiers.identifiers_repository import (IdentifierRepository,
                                                IdentifierRepositoryError)
from identifiers.model import CenterIdentifiers
from inputs.csv_reader import AggregateRowValidator, CSVVisitor, read_csv
from outputs.errors import (CSVLocation, ErrorWriter, FileError,
                            identifier_error, missing_header_error)

log = logging.getLogger(__name__)


class EnrollmentBatch:
    """Collects new Identifier objects for commiting to repository."""

    def __init__(self) -> None:
        self.__records: Dict[str, EnrollmentRecord] = {}

    def __iter__(self) -> Iterator[EnrollmentRecord]:
        """Returns an iterator to the the enrollment records in this batch."""
        return iter(self.__records.values())

    def __len__(self) -> int:
        """Returns the number of enrollment records in this batch."""
        return len(self.__records.values())

    def add(self, enrollment_record: EnrollmentRecord) -> None:
        """Adds the enrollment object to this bacth.

        Args:
          enrollment_record: the enrollment object
        """
        identifier = enrollment_record.center_identifier
        self.__records[identifier.ptid] = enrollment_record

    def commit(self, repo: IdentifierRepository) -> None:
        """Adds participants to the repository.

        NACCIDs are added to records after identifiers are created.

        Args:
          repo: the repository for identifiers
        """
        if not self.__records:
            log.warning('No enrollment records found to create')
            return

        query = [
            record.center_identifier for record in self.__records.values()
        ]
        identifiers = repo.create_list(query)
        log.info("created %s new NACCIDs", len(identifiers))
        if len(query) != len(identifiers):
            log.warning("expected %s new IDs, got %s", len(query),
                        len(identifiers))

        for identifier in identifiers:
            record = self.__records.get(identifier.ptid)
            if record:
                record.naccid = identifier.naccid


class TransferVisitor(CSVVisitor):
    """Visitor for processing transfers into a center."""

    def __init__(self, error_writer: ErrorWriter, transfer_info: TransferInfo,
                 repo: IdentifierRepository) -> None:
        self.__error_writer = error_writer
        self.__transfer_info = transfer_info
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
        """Visits enrollment/transfer data for single form.

        Args:
          row: the dictionary for the row in the file
          line_num: the line number of the row
        Returns:
          True if there are any errors in the row. False, otherwise.
        """
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
                return True
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
            if previous_adcid is not None and previous_ptid:
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
        self.__transfer_info.add(
            TransferRecord(date=row['frmdate_enrl'],
                           initials=row['initials_enrl'],
                           center_identifiers=new_identifiers,
                           previous_identifiers=previous_identifiers,
                           naccid=naccid))

        log.info('Transfer found on line %s', line_num)

        return False


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
        """Adds an enrollment record to the batch for creating new identifiers.

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

    def __init__(self, *, center_id: int, error_writer: ErrorWriter,
                 transfer_info: TransferInfo, batch: EnrollmentBatch,
                 repo: IdentifierRepository) -> None:
        self.__error_writer = error_writer
        self.__enrollment_visitor = NewEnrollmentVisitor(error_writer,
                                                         repo=repo,
                                                         batch=batch)
        self.__transfer_in_visitor = TransferVisitor(
            error_writer, repo=repo, transfer_info=transfer_info)
        self.__validator = CenterValidator(center_id=center_id, error_writer=error_writer)

    def visit_header(self, header: List[str]) -> bool:
        """Prepares visitor to work with CSV file with given header.

        Args:
          header: the list of header names
        Returns:
          True if all of the visitors return True. False otherwise
        """
        expected_columns = {'enrltype'}
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return (self.__enrollment_visitor.visit_header(header)
                and self.__transfer_in_visitor.visit_header(header))

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Provisions a NACCID for the ADCID and PTID.

        First checks that the row has the form name as the module.
        Then checks form to determine processing.
        If form is
        - a new enrollment, then applies the NewEnrollmentVisitor.
        - a transfer TransferVisitor.

        Args:
          row: the dictionary for the CSV row (DictReader)
          line_num: the line number of the row
        Returns:
          True if an error occurs. False, otherwise.
        """
        if not self.__validator.check(row=row, line_number=line_num):
            return True

        if is_new_enrollment(row):
            return self.__enrollment_visitor.visit_row(row=row,
                                                       line_num=line_num)

        return self.__transfer_in_visitor.visit_row(row=row, line_num=line_num)


def run(*, input_file: TextIO, center_id: int, repo: IdentifierRepository,
        enrollment_project: EnrollmentProject, error_writer: ErrorWriter):
    """Runs identifier provisioning process.

    Args:
      input_file: the data input stream
      center_id: the ADCID for the center
      repo: the identifier repository
      enrollment_project: the project tracking enrollment
      error_writer: the error output writer
    """
    transfer_info = TransferInfo(transfers=[])
    enrollment_batch = EnrollmentBatch()
    has_error = read_csv(input_file=input_file,
                         error_writer=error_writer,
                         visitor=ProvisioningVisitor(
                             center_id=center_id,
                             batch=enrollment_batch,
                             repo=repo,
                             error_writer=error_writer,
                             transfer_info=transfer_info))
    if has_error:
        log.error("no changes made due to errors in input file")
        return True

    log.info("requesting %s new NACCIDs", len(enrollment_batch))
    try:
        enrollment_batch.commit(repo)
    except IdentifierRepositoryError as error:
        raise GearExecutionError(error) from error

    for record in enrollment_batch:
        if not record.naccid:
            log.error('Failed to generate NACCID for enrollment record %s/%s',
                      record.center_identifier.adcid,
                      record.center_identifier.ptid)
            continue

        if enrollment_project.find_subject(label=record.naccid):
            log.error('Subject with NACCID %s exists', record.naccid)
            continue

        subject = enrollment_project.add_subject(record.naccid)
        subject.add_enrollment(record)
        # subject.update_demographics_info(demographics)

    enrollment_project.add_transfers(transfer_info)

    return False
