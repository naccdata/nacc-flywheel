"""Methods to define user permissions in REDCap projects."""

from typing import Any, Dict, List, Optional

NACC_TECH_ROLE = 'NACC-TECH-ROLE'
NACC_STAFF_ROLE = 'NACC-STAFF-ROLE'
CENTER_USER_ROLE = 'CENTER-USER-ROLE'


def get_nacc_developer_permissions(
        *,
        username: str,
        expiration: Optional[str] = None,
        forms_list: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Permissions for a NACC user who has developer privilleges for a project.

    Args:
        username: REDCap username
        expiration (optional): permission expiration date
        forms_list (optional): list of forms in the project

    Returns:
        Dict[str, Any]: user permissions directory
    """

    forms = {}  # Form rights
    forms_export = {}  # Data export rights

    # Need to set permissions for each form in the project
    if forms_list:
        for form in forms_list:
            form_name = form['instrument_name']
            forms[form_name] = 1  # View and Edit
            forms_export[form_name] = 1  # Full Data Set

    permissions = {
        "username": username,
        "expiration": expiration,
        "design": 1,
        "alerts": 1,
        "user_rights": 1,
        "data_access_groups": 1,
        "data_export": 1,
        "reports": 1,
        "stats_and_charts": 1,
        "manage_survey_participants": 1,
        "calendar": 1,
        "data_import_tool": 1,
        "data_comparison_tool": 1,
        "logging": 1,
        "file_repository": 1,
        "data_quality_create": 1,
        "data_quality_execute": 1,
        "api_export": 1,
        "api_import": 1,
        "record_create": 1,
        "record_rename": 1,
        "record_delete": 1,
        "forms": forms,
        "forms_export": forms_export
    }

    return permissions
