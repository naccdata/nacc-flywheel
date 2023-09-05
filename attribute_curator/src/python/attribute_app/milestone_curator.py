import logging
from typing import Any, Dict

from dates.dates import get_localized_timestamp
from files.milestone_form import MilestoneForm
from flywheel import Session
from flywheel_gear_toolkit.utils.curator import FileCurator

log = logging.getLogger(__name__)


class Curator(FileCurator):

    def curate_file(self, file_: Dict[str, Any]):
        """Curate Milestones form data."""

        acq = self.context.get_container_from_ref(file_.get("hierarchy"))
        filename = self.context.get_input_filename("file-input")
        file_o = acq.get_file(filename)
        ses = self.context.client.get_session(file_o.parents.get("session"))
        milestone_form = MilestoneForm(file_o)
        self.__curate_session(ses, milestone_form)

    def __curate_session(self, ses: Session, form: MilestoneForm):
        """Set attributes for Milestones session."""

        visit_datetime = form.get_session_date()
        if visit_datetime:
            timestamp = get_localized_timestamp(visit_datetime)
            ses.update({"timestamp": timestamp})
        else:
            log.warning("Timestamp undetermined for %s", ses.label)
