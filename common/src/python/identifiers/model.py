"""Defines the Identifier data class."""
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(unsafe_hash=True)
class Identifier:
    """Record for identifier correspondence."""
    nacc_id: int
    nacc_adc: int
    adc_id: int
    patient_id: str

    @property
    def naccid(self) -> str:
        """The string NACCID for this identifier."""
        return f"NACC{str(self.nacc_id).zfill(6)}"

    @property
    def ptid(self) -> str:
        """The center assigned participant ID."""
        return self.patient_id


class IdentifierObject(BaseModel):
    """Response model for identifiers.

    Hides unconventional naming of fields and has NACCID as string.
    """
    adcid: int
    naccadc: int
    ptid: str
    naccid: str

    def as_model(self) -> Identifier:
        """Returns the IdentifierModel for this Identifier.

        Returns:
          the corresponding IdentifierModel for this object
        """
        return Identifier(adc_id=self.adcid,
                          nacc_adc=self.naccadc,
                          patient_id=self.ptid,
                          nacc_id=int(self.naccid[4:]))

    @classmethod
    def create_from(cls, identifier: Identifier) -> 'IdentifierObject':
        """Create Identifier object from model object.

        Args:
          identifier: the IdentifierModel object to copy
        Returns:
          the Identifier copy of the model object
        """
        return IdentifierObject(adcid=identifier.adc_id,
                                naccadc=identifier.nacc_adc,
                                ptid=identifier.ptid,
                                naccid=identifier.naccid)
