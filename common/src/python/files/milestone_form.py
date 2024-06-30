"""Defines form class for milestone forms."""
from datetime import datetime
from typing import Optional

from dates.dates import datetime_from_form_date
from files.form import Form


class MilestoneForm(Form):
    """Milestone form class used for attribute curation."""

    def get_session_date(self) -> Optional[datetime]:
        """Get date of Milestones session.

        Returns:
            the date time value for the NP visit, None if not found
        """
        visit_datetime = None
        visit_date = self.get_metadata("vstdate_mlst")
        if visit_date:
            visit_datetime = datetime_from_form_date(visit_date)
        return visit_datetime
