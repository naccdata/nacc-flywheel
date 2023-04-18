# Push Template

Script to push settings from template projects in an admin group, to projects in center groups.

## Environment

The script expects the `FW_API_KEY` environment variables to be set, which should be an API key for the FW instance.

## Flywheel configuration

The script also expects that there is an admin group containing template projects.

A template project has a name like `form-ingest-template` where the first word is the datatype and the second is a pipeline stage.
Concretely, the name should match the regex `^((\w+)-)?(\w+)-template$`.
Note that the first group is optional, so possible names are `form-ingest-template` or `accepted-template`.
The datatype names must match those used in the project description file used in the project management script.

The stage names are hard-coded in the project management script, and are `ingest`, `accepted` and `retrospective`.

Projects that are managed by the script should be in groups with a tag matching the regex `adcid-\d+`.
For example, `adcid-14`.
These tags can be set using the project management script.

## Running from command-line

The script can be run with 

```bash
./pants run push_template/src/python:bin
```

which will push all template projects to pipeline stage projects within tagged groups.

To give command line arguments, add `--` to the command line and give the arguments.
The arguments are `--dry_run` to run the script without making changes, and `--admin_group` to indicate the group in which templates occur. 
The default admin group is `nacc`.


If run with `--gear`, the script will read the other arguments from the Gear context.
