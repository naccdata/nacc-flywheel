from datetime import datetime
from typing import Any, Dict, List, Optional

from flywheel import Session
from flywheel.file_spec import FileSpec
from flywheel.finder import Finder


class Subject:

    @property
    def id(self) -> str:
        ...

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

    def add_session(self, label: str) -> Session:
        ...

    @property
    def sessions(self) -> Finder[Session]:
        ...

    def reload(self) -> Subject:
        ...

    def update_info(self, *args, **kwargs):
        """Update the info with the passed in arguments."""
        ...

    def upload_file(self, file: FileSpec) -> List[Dict]:
        ...
