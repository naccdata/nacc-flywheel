"""Models to represent information in the Participant enrollment/transfer form.
"""

from typing import List, Literal, Optional, TextIO
from pydantic import BaseModel, Field

from identifiers.model import CenterIdentifiers
from outputs.outputs import CSVWriter


class GenderIdentity(BaseModel):
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
    years_education: int | Literal[99] = Field(ge=0, le=36)
    birth_month: int = Field(ge=1, le=12)
    birth_year: int = Field(ge=1950, le=2030)
    gender_identity: GenderIdentity

class EnrollmentTransferRow(BaseModel):
    adcid: int = Field(ge=0)
    ptid: str = Field(max_length=10)
    frmdate_enrl: str # date
    initials_enrl: str
    enrltype: Literal[1,2]
    enrlbirthmo: int = Field(ge=1, le=12)
    enrlbirthyr: int = Field(ge=1950, le=2030)
    enrleduc: int | Literal[99] = Field(ge=0, le=36)
    enrlgenman: Optional[Literal[1]]
    enrlgenwoman: Optional[Literal[1]]
    enrlgentrman: Optional[Literal[1]]
    enrlgentrwoman: Optional[Literal[1]] 
    enrlgennonbi: Optional[Literal[1]]
    enrlgentwospir: Optional[Literal[1]] 
    enrlgenoth: Optional[Literal[1]] 
    enrlgenothx: Optional[Literal[1]] 
    enrlgendkn: Optional[Literal[1]] 
    enrlgennoans: Optional[Literal[1]] 
    guidavail: Literal[0,1]
    guid: str
    prevenrl: Literal[1,2]
    oldadcid: int = Field(ge=0)
    oldptid: str = Field(max_length=10)
    naccidknwn: Literal[1,2]
    naccid: str = Field(min_length=10, pattern=r"^NACC\d{6}$")
    ptidconf: str = Field(max_length=10)
    module: str


    @property
    def new_enrollment(self) -> bool:
        return self.enrltype == 1
    
    @property
    def previously_enrolled(self) -> bool:
        return self.prevenrl == 1
    
    @property
    def naccid_known(self) -> bool:
        return self.naccidknwn == 1
    
    @property
    def current_identifiers(self) -> CenterIdentifiers:
        return CenterIdentifiers(adcid=self.adcid, ptid=self.ptid)
    
    @property
    def previous_identifiers(self) -> CenterIdentifiers:
        return CenterIdentifiers(adcid=self.oldadcid, ptid=self.oldptid)
    
    def demographics(self) -> Demographics:
        return Demographics(years_education=self.enrleduc,
                            birth_month=self.enrlbirthmo,
                            birth_year=self.enrlbirthyr,
                            gender_identity=GenderIdentity(
                                man=self.enrlgenman,
                                woman=self.enrlgenwoman,
                                transgender_man=self.enrlgentrman,
                                transgender_woman=self.enrlgentrwoman,
                                nonbinary=self.enrlgennonbi,
                                two_spirit=self.enrlgentwospir,
                                other=self.enrlgenoth,
                                other_term=self.enrlgenothx,
                                dont_know=self.enrlgendkn,
                                no_answer=self.enrlgennoans
                            ))


class TransferRecord(BaseModel):
    date: datetime
    initials: str
    center_identifiers: CenterIdentifiers
    previous_identifiers: Optional[CenterIdentifiers]
    naccid: Optional[str] = Field(min_length=10, pattern=r"^NACC\d{6}$")

class TransferWriter(CSVWriter):
    """CSVWRiter for writing transfer records."""

    def __init__(self, stream: TextIO) -> None:
        fieldnames = TransferRecord
        super().__init__(stream, fieldnames)

class EnrollmentRecord(BaseModel):
    center_identifier: CenterIdentifiers
    start_date: datetime
    end_date: datetime
    transfer_from: TransferRecord
    transfer_to: TransferRecord