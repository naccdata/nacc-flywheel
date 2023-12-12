"""Defines the Identifier data class."""
from dataclasses import dataclass


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
        """The center assigned participant ID"""
        return self.patient_id
