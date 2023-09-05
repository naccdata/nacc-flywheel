from datetime import datetime
from typing import Any, Dict, Optional


class Subject:

    @property
    def label(self) -> str:
        ...

    # info is "defined" as object
    @property
    def info(self) -> Dict[str, Any]:
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
