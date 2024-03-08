"""Defines components related to user authorizations."""
from typing import Dict, List, Literal, Sequence, Set

from pydantic import BaseModel


class Authorizations(BaseModel):
    """Type class for authorizations."""
    study_id: str
    submit: List[Literal['form', 'dicom']]
    audit_data: bool
    approve_data: bool
    view_reports: bool

    @classmethod
    def create_from_record(cls, activities: Sequence[str]) -> "Authorizations":
        """Creates an Authorizations object directory access activities.

        Activities from the NACC directory are represented as a string
        consisting of a comma-separated list of letters.

        The letters represent the following activities:
        - a: submit form data
        - b: submit image data
        - c: audit data
        - d: approve data
        - e: view reports

        Args:
          activities: a string containing activities
        Returns:
          The Authorizations object
        """
        modalities: List[Literal['form', 'dicom']] = []
        if 'a' in activities:
            modalities.append('form')
        if 'b' in activities:
            modalities.append('dicom')

        return Authorizations(study_id='adrc',
                              submit=modalities,
                              audit_data=bool('c' in activities),
                              approve_data=('d' in activities),
                              view_reports=('e' in activities))


class AuthMap(BaseModel):
    """Type class for mapping authorizations to roles."""
    project_authorizations: Dict[str, Dict[str, str]]

    def get(self, *, project_id: str,
            authorizations: 'Authorizations') -> Set[str]:
        """Gets the roles for a project and authorizations.

        Args:
            project_id: the project ID
            authorizations: the authorizations
        Returns:
            The list of roles
        """
        roles = set()

        if project_id not in self.project_authorizations:
            return roles

        activity_map = self.project_authorizations[project_id]
        if authorizations.approve_data:
            value = activity_map.get('approve-data')
            if value:
                roles.add(value)
        if authorizations.audit_data:
            value = activity_map.get('audit-data')
            if value:
                roles.add(value)
        if authorizations.view_reports:
            value = activity_map.get('view-reports')
            if value:
                roles.add(value)
        if authorizations.submit:
            for datatype in authorizations.submit:
                value = activity_map.get(f'submit-{datatype}')
                if value:
                    roles.add(value)

        return roles
