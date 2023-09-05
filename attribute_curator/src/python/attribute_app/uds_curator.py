import logging
from typing import Any, Dict, Optional

from dates.dates import datetime_from_form_date, get_localized_timestamp
from files.uds_form import UDSV3Form
from flywheel import Session, Subject
from flywheel_gear_toolkit.utils.curator import FileCurator

log = logging.getLogger(__name__)


class Curator(FileCurator):

    def curate_file(self, file_: Dict[str, Any]):
        """Look in UDSv3 file for demographic information and set subject
        attributes."""

        acq = self.context.get_container_from_ref(file_.get("hierarchy"))
        filename = self.context.get_input_filename("file-input")
        file_o = acq.get_file(filename)
        form = UDSV3Form(file_o)

        subject = self.context.client.get_subject(
            file_o.parents.get("subject"))
        packet = form.get_metadata("packet")
        if packet and packet.startswith("I"):
            self.__curate_subject_initial(sub=subject, form=form)

        session = self.context.client.get_session(
            file_o.parents.get("session"))
        self.__curate_session(subject, session, file_o)

    def __curate_session(self, subject: Subject, session: Session,
                         form: UDSV3Form):
        """Set session attributes.

        Args:
            sub (Subject): the subject object
            ses (Session): the session object
            file_o (FileEntry): the file entry for UDSv3 file
        """

        # Set session weight
        weight_kg = form.get_weight_at_session()
        if weight_kg:
            session.update({"weight": weight_kg})
        else:
            log.warning("Weight unknown for %s", session.label)

        visit_datetime = form.get_session_date()
        if not visit_datetime:
            log.warning("No visit date given for %s", session.label)
            return

        # Set session timestamp
        timestamp = get_localized_timestamp(visit_datetime)
        if timestamp:
            session.update({"timestamp": timestamp})
        else:
            log.warning("Timestamp undetermined for %s", session.label)

        # Set age at session
        age = form.get_age_at_session(visit_datetime)
        if age:
            session.update({"age": age})
        else:
            log.warning("Age unknown for %s", session.label)

        # Set/update latest CDR info for the subject
        self.__set_subject_cdr_info(subject, form)

    def __curate_subject_initial(self, *, sub: Subject, form: UDSV3Form):
        """Sets subject fields based on data from a UDSv3 data file for an
        initial visit.

        Args:
        sub: the subject object
        file_o: the file entry for the file
        """
        sub.update(type="human")
        sex = form.get_subject_sex()
        race = form.get_subject_race()
        ethnicity = form.get_subject_ethnicity()
        dob_timestamp = None
        date_of_birth = form.get_subject_dob()
        if date_of_birth:
            dob_timestamp = get_localized_timestamp(date_of_birth)
        else:
            log.warning("DOB undetermined for %s", sub.label)
        info = form.get_subject_initial_info_fields()

        sub.update(
            firstname="not-collected",
            lastname="not-collected",
            sex=sex,
            cohort="Study",
            race=race,
            ethnicity=ethnicity,
            date_of_birth=dob_timestamp,
            info=info,
        )

    def __set_subject_cdr_info(self, subject: Subject, form: UDSV3Form):
        """Sets the latest CDR info for the subject.

        Args:
        sub: the subject object
        file_o: the file entry for the file
        """
        cdrinfo = form.get_cdr_info()
        current_date = dotty_get(cdrinfo, "cognitive.cdr-latest.date")
        assert current_date
        last_date = dotty_get(subject.info, "cognitive.cdr-latest.date")
        assert last_date

        if last_date:
            current_date = datetime_from_form_date(current_date)
            last_date = datetime_from_form_date(last_date)

        if current_date > last_date:
            log.debug(f"Updating subject CDR info with new values")
            subject.update(info=cdrinfo)
        else:
            log.debug(f"Setting subject CDR info")
            subject.update(info=cdrinfo)


def dotty_get(full_dict: Dict[str, Any], dotty_key: str) -> Optional[Any]:
    """Gets value by hierarchical key from dictionary.

    A hierarchical key is of the form "top.middle.bottom".

    Args:
      full_dict: a hierarchical dictionary
      dotty_key: a hierarchical key
    Returns:
      value from lowest dictionary corresponding to key,
      None if key doesn't match
    """
    keys = dotty_key.split(".")
    val = full_dict
    while keys:
        key = keys.pop(0)
        val = val.get(key, {})
    if not val:
        return None

    return val
