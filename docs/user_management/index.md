# User management

The user management utility reads a user file from the admin project and updates the listed users.

## Environment

The script expects the `FW_API_KEY` environment variables to be set, which should be an API key for the FW instance.

## Flywheel configuration

The script expects two YAML files as input: the list of users, and the map from user authorizations to Flywheel role names.

The user file should contain a list of user information

```yaml
---
- authorizations:
    approve_data: <Boolean> # whether user can approve data
    audit_data: <Boolean>   # whether user audits data quality
    submit:
    - <datatype name>       # datatypes which user can submit
    view_reports: <Boolean> # whether user can view reports
  center_id: <integer ID>   # the ADCID for the center
  credentials:
    id: <id-value>          # user ID (email or ePPN)
    type: <type-name>       # type of credential
  email: <email-address>    # user email
  name:
    first_name: <user first name> 
    last_name: <user last name>
  org_name: <center name>
  submit_time: <datetime of submission>
  ```

The authorization map defines a mapping $project\to (authorization\to role)$

```yaml
---
<project-id>:
  approve-data: <rolename>
  audit-data: <rolename>
  view-reports: <rolename>
  submit-form: <rolename>
  submit-image: <rolename>
```

Valid project IDs are determined by the project management script.
These are:

- `accepted` or `accepted-<study-id>`
- `metadata`
- `ingest-<datatype>` or `ingest-<datatype>-<study-id>`
- `sandbox-<datatype>` or `sandbox-<datatype>-<study-id>`

The datatypes and study IDs are determined by the study definition used by project management.

The role names are set in the Flywheel instance.
Roles used by NACC for center users include `read-only`, `curate` and `upload`.

If an authorization has no access to a project, it should be left off the list.
For instance, `submit-form` would have no corresponding role for `ingest-dicom`

  
## Running from command-line

  The script can be run with

  ```bash
  pants run user_management/src/python/user_app:bin -- <filename>
  ```

  which will update users listed in the named file.

  Additional command line arguments are `--dry_run` to run the script without making changes, and `--admin_group` to indicate the group in which the file is found.
  The default admin group is `nacc`.
  
## User Enrollment Process

### Center member authorization

A center member is authorized as a user of the NACC Directory by the Center Administrator.
In this process, the administrator adds a center member to the NACC Directory in REDCap and authorizes their access to the NACC Data Platform.
Authorization initiates a Data Platform Access survey that prompts the user to provide the email to be used for authentication.

```mermaid
sequenceDiagram
    actor admin as Center<br/>Admin
    actor member as Center<br/>Member

    participant directory as NACC<br/>Directory
    admin ->> directory: authorize
    directory -) member: access survey email
    member ->> directory: auth email
```

### Pulling NACC Directory

The directory is pulled nightly to Flywheel using the [Directory Pull](../pull_directory/) gear.
This gear writes a file with user information in an admin project on Flywheel.

```mermaid
sequenceDiagram
    scheduler ->> puller: initiate
    note right of scheduler: nightly

    participant puller as Directory Pull
    participant directory as NACC<br/>Directory
    puller ->> directory: get user information
    puller ->> Flywhel: write directory user file
```

### User management

Updates to the NACC directory user file trigger a gear rule that runs the user management gear.

```mermaid
sequenceDiagram
    Rule ->> usermgmt: initiate
    note right of Rule: update to directory user file

    participant usermgmt as User<br/>Management
    usermgmt ->> Flywheel: pull directory users
    loop each authorized user
        usermgmt ->> CoManage: get by email
        actor member as Center<br/>Member   
        alt user not in registry
            usermgmt ->> CoManage: create
            usermgmt -) member: claim email
        else user is claimed in registry
            usermgmt ->> Flywheel: find by registry ID
            alt if user not in Flywheel
              usermgmt ->> Flywheel: create
              usermgmt -) member: notification email
            end
            usermgmt ->> Flywheel: set user roles
        else is unclaimed for more than a week
            usermgmt -) member: claim reminder email
        end
    end
```