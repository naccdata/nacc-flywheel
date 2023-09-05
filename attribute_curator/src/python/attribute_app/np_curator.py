"""Curation utilities for NP forms."""
import logging
from typing import Any, Dict

from files.form_curator import FormCurator, curate_session_timestamp
from files.np_form import NPv11Form

log = logging.getLogger(__name__)


class NPv11Curator(FormCurator):
    """File curator for NPv11 forms."""

    def curate_file(self, file_: Dict[str, Any]):
        """Curate Neuropathology (NP) form data."""
        file_entry = self.get_file(file_)
        form = NPv11Form(file_entry)
        session = self.get_session(file_entry)
        curate_session_timestamp(session, form)
