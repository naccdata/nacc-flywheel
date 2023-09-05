from datetime import datetime
from typing import Optional


class Subject:

    @property
    def label(self) -> str:
        ...

    @property
    def info(self) -> object:
        ...

    @property
    def type(self) -> str:
        ...

    def update(
            self,
            *,
            firstname: Optional[str] = None,
            lastname: Optional[str] = None,
            sex: Optional[str] = None,
            cohort: Optional[
                str] = None,  # Cohort is an enum with string value
            race: Optional[str] = None,
            ethnicity: Optional[str] = None,
            date_of_birth: Optional[datetime] = None,
            info: Optional[object] = None,
            type: Optional[str] = None):
        ...
