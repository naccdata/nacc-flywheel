"""Frquently accessed field names, labels, and default values."""


class FieldNames:
    """Class to store frquently accessed field names."""
    NACCID = 'naccid'
    MODULE = 'module'
    PACKET = 'packet'
    PTID = 'ptid'
    ADCID = 'adcid'
    MODE = 'mode'
    VISITNUM = 'visitnum'
    DATE_COLUMN = 'visitdate'
    FORMVER = 'formver'
    GUID = 'guid'
    OLDADCID = 'oldadcid'
    OLDPTID = 'oldptid'
    ENRLFRM_DATE = 'frmdate_enrl'
    ENRLFRM_INITL = 'initials_enrl'
    NACCIDKWN = 'naccidknwn'
    PREVENRL = 'prevenrl'


class RuleLabels:
    """Class to store rule definition labels."""
    CODE = 'code'
    INDEX = 'index'
    COMPAT = 'compatibility'
    TEMPORAL = 'temporalrules'
    NULLABLE = 'nullable'
    REQUIRED = 'required'
    GDS = 'compute_gds'


class DefaultValues:
    """Class to store default values."""
    NOTFILLED = '0'
    LEGACY_PRJ_LABEL = 'retrospective-form'
    ENROLLMENT_MODULE = 'ENROLLV1'
    GEARBOT_USER_ID = 'nacc-flywheel-gear@uw.edu'
    NACC_GROUP_ID = 'nacc'
    METADATA_PRJ_LBL = 'metadata'
    ADMIN_PROJECT = 'project-admin'


class MetadataKeys:
    """Class to store metadata keys."""
    LEGACY_KEY = 'legacy'
    LEGACY_LBL = 'legacy_label'
    LEGACY_ORDERBY = 'legacy_orderby'
    FAILED = 'failed'
