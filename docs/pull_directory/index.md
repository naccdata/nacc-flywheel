# NACC Directory Pull

This utility pulls user information from a Flywheel-access report in the NACC REDCap instance,
and then creates a file with the user information in a form that can be loaded by the [user management utility](../user_management/index.md).

The NACC directory in REDCap ensures that emails are unique, but not user credentials (user IDs).
Since the user IDs are used to create FW accounts, we don't want to create user accounts with a "disputed" user ID.
So, any entries with the same user ID are saved in the file `conflicts-nacc-directory-users.yaml`, and the incorrect entries will have to be invalidated in the directory in REDCap.

## Configuration

The gear uses the following from the AWS parameter store:

- API key for Flywheel
- API token, URL and report ID for the Flywheel Access report of the NACC directory on REDCap

Remaining configuration are listed in the manifest. 
Defaults are set so that the gear is ready to run in the NACC instance.
Using these defaults, files will be written in the project `nacc/project-admin` and are named `nacc-directory-users.yaml` and `conflicts-nacc-directory-users.yaml`

## REDCap configuration

The script expects that there is a user access report that is defined in the directory project.

The following are assumed to be columns in the report

- `flywheel_access_information_complete` - integer indicating whether all information has been provided.
- `flywheel_access_activities` - list of activities indicated by letters `a` through `e`
- `fw_credential_type` - string indicating type of credential
- `fw_credential_id` - string ID for user credentials
- `firstname` - user first name
- `lastname` - user last name
- `contact_company_name` - the name of the center
- `adresearchctr` - string with numeric ID for center
- `email` - user email
- `fw_cred_sub_time` - submission time for credentials


