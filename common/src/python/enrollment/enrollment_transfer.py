"""Models to represent information in the Participant enrollment/transfer
form."""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from identifiers.model import CenterIdentifiers
from pydantic import BaseModel, Field


class GenderIdentity(BaseModel):
    """Model for Gender Identity demographic data."""
    man: Optional[Literal[1]]
    woman: Optional[Literal[1]]
    transgender_man: Optional[Literal[1]]
    transgender_woman: Optional[Literal[1]]
    nonbinary: Optional[Literal[1]]
    two_spirit: Optional[Literal[1]]
    other: Optional[Literal[1]]
    other_term: Optional[Literal[1]]
    dont_know: Optional[Literal[1]]
    no_answer: Optional[Literal[1]]


class Demographics(BaseModel):
    """Model for demographic data."""
    years_education: int | Literal[99] = Field(ge=0, le=36)
    birth_date: datetime
    gender_identity: GenderIdentity

    @classmethod
    def create_from(cls, row: Dict[str, Any]) -> 'Demographics':
        """Constructs a Demographics object from row of enrollment/transfer
        form.

        Assumes form is PTENRLv1.

        Args:
          row: the dictionary for the row of form.
        Returns:
          Demographics object built from row
        """
        return Demographics(years_education=row['enrleduc'],
                            birth_date=datetime(int(row['enrlbirthmo']),
                                                int(row['enrlbirthyr']), 1),
                            gender_identity=GenderIdentity(
                                man=row['enrlgenman'],
                                woman=row['enrlgenwoman'],
                                transgender_man=row['enrlgentrman'],
                                transgender_woman=row['enrlgentrwoman'],
                                nonbinary=row['enrlgennonbi'],
                                two_spirit=row['enrlgentwospir'],
                                other=row['enrlgenoth'],
                                other_term=row['enrlgenothx'],
                                dont_know=row['enrlgendkn'],
                                no_answer=row['enrlgennoans']))


class TransferRecord(BaseModel):
    """Model representing transfer between centers."""
    date: datetime
    initials: str
    center_identifiers: CenterIdentifiers
    previous_identifiers: Optional[CenterIdentifiers]
    naccid: Optional[str] = Field(min_length=10, pattern=r"^NACC\d{6}$")


class EnrollmentRecord(BaseModel):
    """Model representing enrollment of participant."""
    center_identifier: CenterIdentifiers
    naccid: Optional[str] = Field(min_length=10, pattern=r"^NACC\d{6}$")
    guid: Optional[str] = Field(min_length=13)
    start_date: datetime
    end_date: Optional[datetime]
    transfer_from: Optional[TransferRecord]
    transfer_to: Optional[TransferRecord]
