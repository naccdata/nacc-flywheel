import logging
from typing import Any, Dict

from dates.dates import get_localized_timestamp
from files.np_form import NPv11Form
from flywheel import Session
from flywheel_gear_toolkit.utils.curator import FileCurator

log = logging.getLogger(__name__)


class NPCurator(FileCurator):

    def curate_file(self, file_: Dict[str, Any]):
        """Curate Nuropathelogy (NP) form data."""

        acq = self.context.get_container_from_ref(file_.get("hierarchy"))
        filename = self.context.get_input_filename("file-input")
        file_o = acq.get_file(filename)
        ses = self.context.client.get_session(file_o.parents.get("session"))
        form = NPv11Form(file_o)
        self.curate_session(ses, form)

    def curate_session(self, ses: Session, form: NPv11Form):
        """Set attributes for NP session."""

        visit_datetime = form.get_session_date()
        if visit_datetime:
            timestamp = get_localized_timestamp(visit_datetime)
            ses.update({"timestamp": timestamp})
        else:
            log.warning("Timestamp undetermined for %s", ses.label)
