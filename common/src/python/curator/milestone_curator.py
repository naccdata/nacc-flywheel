"""Defines utilities for Milestone forms."""
import logging
from typing import Any, Dict

from curator.form_curator import FormCurator, curate_session_timestamp
from files.milestone_form import MilestoneForm

log = logging.getLogger(__name__)


class MilestoneCurator(FormCurator):
    """File curation class for milestone forms."""

    def curate_file(self, file_: Dict[str, Any]):
        """Curate Milestones form data.

        Args:
          file_object: JSON data for file
        """
        file_entry = self.get_file(file_)
        milestone_form = MilestoneForm(file_entry)
        session = self.get_session(file_entry)
        curate_session_timestamp(session, milestone_form)
