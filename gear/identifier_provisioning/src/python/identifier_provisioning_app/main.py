"""Defines Identifier Provisioning."""

import abc
import logging
from typing import Any, Dict, List, Optional, TextIO

from identifiers.identifiers_repository import IdentifierUnitOfWork
from identifiers.model import Identifier, IdentifierObject
from inputs.csv_reader import CSVVisitor, read_csv
from outputs.errors import (CSVLocation, ErrorWriter, FileError,
                            empty_field_error, missing_header_error,
                            unexpected_value_error)

log = logging.getLogger(__name__)


def is_new_enrollment(row: Dict[str, Any]) -> bool:
    return int(row['enrltype']) == 1


def is_transfer_out(row: Dict[str, Any]) -> bool:
    return int(row['ptxfer']) == 1


def previously_enrolled(row: Dict[str, Any]) -> bool:
    return int(row['prevenrl']) == 1


def has_known_naccid(row: Dict[str, Any]) -> bool:
    return int(row['naccidknwn']) == 1


class IdentifierBatch:
    """Collects new Identifier objects for commiting to repository."""

    def __init__(self) -> None:
        self.__identifiers: List[IdentifierObject] = []

    def add(self, identifier: IdentifierObject):
        self.__identifiers.append(identifier)

    def get(self,
            adcid: Optional[int] = None,
            ptid: Optional[int] = None,
            guid: Optional[str] = None) -> Optional[IdentifierObject]:
        if adcid and ptid:
            return None

        if guid:
            return None

        return None

    def commit(self, unit_of_work: IdentifierUnitOfWork) -> None:
        """Adds identifiers to the repository managed by the unit of work
        object.

        Args:
        unit_of_work: object managing transactions with identifier repository
        identifiers: the list of identifiers to add
        """
        with unit_of_work:
            identifiers_repo = unit_of_work.repository
            assert identifiers_repo, "repository is defined by context manager"
            identifiers_repo.add_list(self.__identifiers)
            unit_of_work.commit()


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


class AggregateRowValidator(RowValidator):

    def __init__(self, validators: List[RowValidator] = []) -> None:
        self.__validators = validators

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


class TransferOutVisitor(CSVVisitor):

    def __init__(self, error_writer: ErrorWriter) -> None:
        self.__error_writer = error_writer

    def visit_header(self, header: List[str]) -> bool:
        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        # check for matching incoming record at other center
        # if one exists, assign IDs
        # otherwise create outgoing transfer record, tag possible matches
        return False


class TransferInVisitor(CSVVisitor):

    def __init__(self, error_writer: ErrorWriter) -> None:
        self.__error_writer = error_writer

    def visit_header(self, header: List[str]) -> bool:
        """Checks that the header has expected column headings.

        Args:
          header: the list of column headings for file
        Returns:
          True if there are errors, False otherwise.
        """
        expected_columns = {'oldadcid', 'oldptid', 'naccidknwn', 'naccid'}
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Visits enrollment/transfer data for single form."""
        previous_adcid = row['oldadcid']
        if not previous_adcid:
            self.__error_writer.write(
                empty_field_error(field='oldadcid',
                                  line=line_num,
                                  message='No ADCID given for transfer'))
            return True
        previous_ptid = row['oldptid']
        if not previous_ptid:
            # TODO: record pending incoming transfer needing identification
            self.__error_writer.write(
                empty_field_error(field='oldptid',
                                  line=line_num,
                                  message='No PTID given for transfer'))
            return True
        # TODO: get naccid for previous adcid-ptid
        # TODO: if none, error
        if has_known_naccid(row):
            known_naccid = row['naccid']
            if known_naccid:
                pass

        return False


def existing_participant_error(field: str,
                               value: str,
                               line: int,
                               message: Optional[str] = None) -> FileError:
    """Creates a FileError for unexpected existing participant."""
    error_message = message if message else f'Participant exists for PTID {value}'
    return FileError(error_type='error',
                     error_code='participant-exists',
                     location=CSVLocation(column_name=field, line=line),
                     message=error_message)


class NewPTIDRowValidator(RowValidator):

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

        self.__error_writer.write(
            existing_participant_error(field='ptid',
                                       line=line_number,
                                       value=ptid))
        return False


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
        guid = row['guid']
        identifier = self.__identifiers.get(guid=guid)
        if not identifier:
            return True

        self.__error_writer.write(
            existing_participant_error(
                field='guid',
                line=line_number,
                value=guid,
                message=f'Participant exists for GUID {guid}'))
        return False


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
        self.__validator = AggregateRowValidator([
            NewPTIDRowValidator(batch, error_writer),
            NewGUIDRowValidator(batch, error_writer),
            NoDemographicMatchRowValidator(batch, error_writer)
        ])
        self.__error_writer = error_writer

    def visit_header(self, header: List[str]) -> bool:
        expected_columns = {'adcid', 'ptid', 'guid', 'naccid'}
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return False

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        if not self.__validator.check(row, line_num):
            return True

        # provision naccid
        #identifier = Identifier(nacc_id=newnaccid, patient_id=)
        # add ids to list (?) for creation

        return False


class ProvisioningVisitor(CSVVisitor):
    """A CSV Visitor class for processing participant enrollment and transfer
    forms."""

    def __init__(self, error_writer: ErrorWriter,
                 batch: IdentifierBatch) -> None:
        self.__error_writer = error_writer
        self.__enrollment_visitor = NewEnrollmentVisitor(error_writer,
                                                         batch=batch)
        self.__transfer_in_visitor = TransferInVisitor(error_writer)
        self.__transfer_out_visitor = TransferOutVisitor(error_writer)

    def visit_header(self, header: List[str]) -> bool:
        """Prepares visitor to work with CSV file with given header.

        Args:
          header: the list of header names
        Returns:
          True if all of the visitors return True. False otherwise
        """
        expected_columns = {'module', 'enrltype', 'prevenrl', 'ptxfer'}
        if not expected_columns.issubset(set(header)):
            self.__error_writer.write(missing_header_error())
            return True

        return (self.__enrollment_visitor.visit_header(header)
                and self.__transfer_in_visitor.visit_header(header)
                and self.__transfer_out_visitor.visit_header(header))

    def visit_row(self, row: Dict[str, Any], line_num: int) -> bool:
        """Provisions a NACCID for the NACCID and PTID.

        If not a transfer, checks that the center already has a participant
        with PTID.
        And, checks whether demographics match any existing participant.
        In both case is an error.

        If is a transfer, BLAH

        Args:
          row: the dictionary for the CSV row (DictReader)
          line_num: the line number of the row
        Returns:
          True if a NACCID is provisioned without error, False otherwise
        """
        field = 'module'
        value = 'ptenrlv1'
        if row[field] != value:
            self.__error_writer.write(
                unexpected_value_error(field=field, value=value,
                                       line=line_num))
            return False

        if is_new_enrollment(row):
            return self.__enrollment_visitor.visit_row(row=row,
                                                       line_num=line_num)

        if is_transfer_out(row):
            return self.__transfer_out_visitor.visit_row(row=row,
                                                         line_num=line_num)
        if previously_enrolled(row):
            return self.__transfer_in_visitor.visit_row(row=row,
                                                        line_num=line_num)

        # Note: this should have already been caught in QC checks
        self.__error_writer.write(
            unexpected_value_error(
                field='prevenrl',
                value='1',
                line=line_num,
                message='Incoming transfer must have previous enrollment'))
        return False


def run(*, input_file: TextIO, unit_of_work: IdentifierUnitOfWork,
        error_writer: ErrorWriter):
    """Runs identifier provisioning process.

    Args:
      input_file: the data input stream
      error_writer: the error output writer
    """
    identifier_batch = IdentifierBatch()
    has_error = read_csv(
        input_file=input_file,
        error_writer=error_writer,
        visitor=ProvisioningVisitor(batch=identifier_batch,
                                    error_writer=error_writer))
    identifier_batch.commit(unit_of_work=unit_of_work)
    return has_error
