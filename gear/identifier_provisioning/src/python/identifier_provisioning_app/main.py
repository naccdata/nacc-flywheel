"""Defines Identifier Provisioning."""

import abc
import logging
from typing import Any, Dict, List, Optional, TextIO

from enrollment.enrollment_transfer import TransferRecord
from identifiers.identifiers_lambda_repository import IdentifierRequestObject
from identifiers.identifiers_repository import (IdentifierRepository,
                                                NoMatchingIdentifier)
from identifiers.model import CenterIdentifiers, IdentifierObject
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import (CSVLocation, ErrorWriter, FileError,
                            empty_field_error, identifier_error,
                            missing_header_error, unexpected_value_error)
from outputs.outputs import CSVWriter

log = logging.getLogger(__name__)


def is_new_enrollment(row: Dict[str, Any]) -> bool:
    """Checks if row is a new enrollment.

    Args:
      row: the dictionary for the row.
    Returns:
      True if the row represents a new enrollment. False, otherwise.
    """
    return int(row['enrltype']) == 1


def previously_enrolled(row: Dict[str, Any]) -> bool:
    """Checks if row is has previous enrollment set.

    Args:
      row: the dictionary for the row.
    Returns:
      True if the row represents a previous enrollment. False, otherwise.
    """
    return int(row['prevenrl']) == 1


def guid_available(row: Dict[str, Any]) -> bool:
    """Checks if row has available GUID.

    Args:
      row: the dictionary for the row
    Returns:
      True if the row indicates the GUID is available
    """
    return int(row['guidavail']) == 1


def has_known_naccid(row: Dict[str, Any]) -> bool:
    """Checks if row has a known NACCID.

    Args:
      row: the dictionary for the row.
    Returns:
      True if the row represents a known NACCID. False, otherwise.
    """
    return int(row['naccidknwn']) == 1


class IdentifierBatch:
    """Collects new Identifier objects for commiting to repository."""

    def __init__(self, repo: IdentifierRepository) -> None:
        self.__identifiers: List[IdentifierRequestObject] = []
        self.__repo = repo

    def add(self, identifier: IdentifierRequestObject) -> None:
        """Adds the Identifier request object to this bacth.

        Args:
          identifier: the identifier request object
        """
        self.__identifiers.append(identifier)

    def get(self,
            adcid: Optional[int] = None,
            ptid: Optional[str] = None,
            guid: Optional[str] = None,
            naccid: Optional[str] = None) -> Optional[IdentifierObject]:
        """Gets the identifier object for the parameters.

        Args:
          adcid: the ADCID (expect ptid)
          ptid: the PTID (expect adcid)
          guid: the NIA GUID
          naccid: the NACCID
        Returns:
          the identifier object for the ID, None b/c I'm lazy
        Raises:
          NoMatchingIdentifier if there is no Identifier for the search
        """
        if adcid and ptid:
            try:
                return self.__repo.get(adcid=adcid, ptid=ptid)
            except NoMatchingIdentifier:
                return None

        if naccid:
            try:
                return self.__repo.get(naccid=naccid)
            except NoMatchingIdentifier:
                return None

        if guid:
            return None

        return None

    def commit(self) -> None:
        """Adds identifiers to the repository.

        Args:
        identifier_repo: the repository for identifiers
        identifiers: the list of identifiers to add
        """
        self.__repo.create_list(self.__identifiers)


# pylint: disable=(too-few-public-methods)
class RowValidator(abc.ABC):
    """Abstract class for a RowValidator."""

    @abc.abstractmethod
    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks the row passes the validation criteria of the implementing
        class.

        Args:
            row: the dictionary for the input row
        Returns:
            True if the validator check is true, False otherwise.
        """


# pylint: disable=(too-few-public-methods)
class AggregateRowValidator(RowValidator):
    """Row validator for running more than one validator."""

    def __init__(self,
                 validators: Optional[List[RowValidator]] = None) -> None:
        if validators:
            self.__validators = validators
        else:
            self.__validators = []

    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks the row against each of the validators.

        Args:
            row: the dictionary for the input row
        Returns:
            True if all the validator checks are true, False otherwise
        """
        for validator in self.__validators:
            if not validator.check(row, line_number):
                return False

        return True


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

    def __init__(self, error_writer: ErrorWriter, transfer_writer: CSVWriter,
                 batch: IdentifierBatch) -> None:
        self.__error_writer = error_writer
        self.__transfer_writer = transfer_writer
        self.__batch = batch
        self.__validator = NewPTIDRowValidator(batch, error_writer)

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
                naccid_identifier = self.__batch.get(naccid=known_naccid)
                if not naccid_identifier:
                    self.__error_writer.write(
                        identifier_error(field='naccid',
                                         value=known_naccid,
                                         line=line_num))
                    return True

        if guid_available(row):
            guid_identifier = self.__batch.get(guid=row['guid'])

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
                ptid_identifier = self.__batch.get(adcid=previous_adcid,
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
        self.__transfer_writer.write(transfer_record)

        self.__error_writer.write(
            transfer_not_implemented_error(field='enrltype',
                                           line=line_num,
                                           message="Transfer not performed"))
        return True


def existing_participant_error(field: str,
                               value: str,
                               line: int,
                               message: Optional[str] = None) -> FileError:
    """Creates a FileError for unexpected existing participant."""
    error_message = message if message else ('Participant exists for PTID '
                                             f'{value}')
    return FileError(error_type='error',
                     error_code='participant-exists',
                     location=CSVLocation(column_name=field, line=line),
                     message=error_message)


# pylint: disable=(too-few-public-methods)
class NewPTIDRowValidator(RowValidator):
    """Row validator to check that the PTID in the rows does not have a
    NACCID."""

    def __init__(self, batch: IdentifierBatch,
                 error_writer: ErrorWriter) -> None:
        self.__identifiers = batch
        self.__error_writer = error_writer

    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks that PTID does not already correspond to a NACCID.

        Args:
          row: the dictionary for the row
        Returns:
          True if no existing NACCID is found for the PTID, False otherwise
        """
        ptid = row['ptid']
        identifier = self.__identifiers.get(adcid=row['adcid'], ptid=ptid)
        if not identifier:
            return True

        log.info('Found participant for (%s,%s)', row['adcid'], row['ptid'])
        self.__error_writer.write(
            existing_participant_error(field='ptid',
                                       line=line_number,
                                       value=ptid))
        return False


# pylint: disable=(too-few-public-methods)
class NewGUIDRowValidator(RowValidator):
    """Row Validator to check whether a GUID corresponds to an existing
    NACCID."""

    def __init__(self, batch: IdentifierBatch,
                 error_writer: ErrorWriter) -> None:
        self.__identifiers = batch
        self.__error_writer = error_writer

    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks that the GUID does not already correspond to a NACCID.

        Args:
          row: the dictionary for the row
        Returns:
          True if no existing NACCID is found for the GUID, False otherwise
        """
        if not guid_available(row):
            return True

        guid = row['guid']
        identifier = self.__identifiers.get(guid=guid)
        if not identifier:
            return True

        log.info('Found participant for GUID %s', row['guid'])
        self.__error_writer.write(
            existing_participant_error(
                field='guid',
                line=line_number,
                value=guid,
                message=f'Participant exists for GUID {guid}'))
        return False


# pylint: disable=(too-few-public-methods)
class NoDemographicMatchRowValidator(RowValidator):
    """Row Validator to check whether the demographics match any existing
    participants."""

    def __init__(self, batch: IdentifierBatch,
                 error_writer: ErrorWriter) -> None:
        self.__identifiers = batch
        self.__error_writer = error_writer

    def check(self, row: Dict[str, Any], line_number: int) -> bool:
        """Checks that row demographics do not match an existing participant.

        Args:
          row: the dictionary for the row
        Returns:
          True if no existing participant matches demographics, False otherwise
        """
        return True


class NewEnrollmentVisitor(CSVVisitor):
    """A CSV Visitor class for processing new enrollment forms."""

    def __init__(self, error_writer: ErrorWriter,
                 batch: IdentifierBatch) -> None:
        self.__batch = batch
        self.__validator = AggregateRowValidator([
            NewPTIDRowValidator(batch, error_writer),
            NewGUIDRowValidator(batch, error_writer),
            NoDemographicMatchRowValidator(batch, error_writer)
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
        self.__batch.add(
            IdentifierRequestObject(adcid=row['adcid'], ptid=row['ptid']))

        return False


class ProvisioningVisitor(CSVVisitor):
    """A CSV Visitor class for processing participant enrollment and transfer
    forms."""

    def __init__(self, form_name: str, error_writer: ErrorWriter,
                 batch: IdentifierBatch) -> None:
        self.__form_name = form_name
        self.__error_writer = error_writer
        self.__enrollment_visitor = NewEnrollmentVisitor(error_writer,
                                                         batch=batch)
        self.__transfer_in_visitor = TransferVisitor(error_writer, batch=batch)

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
        if row[module_field] != self.__form_name:
            self.__error_writer.write(
                unexpected_value_error(field=module_field,
                                       value=self.__form_name,
                                       line=line_num))
            return False

        if is_new_enrollment(row):
            return self.__enrollment_visitor.visit_row(row=row,
                                                       line_num=line_num)

        return self.__transfer_in_visitor.visit_row(row=row, line_num=line_num)


def run(*, input_file: TextIO, form_name: str, repo: IdentifierRepository,
        error_writer: ErrorWriter):
    """Runs identifier provisioning process.

    Args:
      input_file: the data input stream
      form_name: the module designator for the form
      error_writer: the error output writer
    """
    identifier_batch = IdentifierBatch(repo=repo)
    has_error = read_csv(input_file=input_file,
                         error_writer=error_writer,
                         visitor=ProvisioningVisitor(
                             form_name=form_name,
                             batch=identifier_batch,
                             error_writer=error_writer))
    identifier_batch.commit()
    return has_error
