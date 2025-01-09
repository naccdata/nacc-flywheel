# Prescreening

Prescreens input files to queue for form-scheduler gear. Looks at the file's basename suffix, and passes it if matches any of the accepted modules (case-insensitive).

## Inputs

Along with an input file (typically expected to be a CSV but not required), the gear takes the following optional input parameters:

| Parameter | Required? | Default | Description |
| --------- | --------- | ------- | ----------- |
| `accepted_modules` | No | `"ENROLL,UDS,FTLD,LBD"` | Comma-deliminated list of accepted modules. Cannot be empty. |
| `tags_to_add` | No | `"queued"` | Comma-deliminated list of tags to add to the prescreened file. Cannot be empty. |
| `dry_run` | No | `false` | Whether or not to do a dry run - will verify file but will not add tags |
| `local_run` | No | `false` | Whether or not to do a local run on a local file - will verify the file but will not add tags |

The gear does not have any explicit outputs but will add the tags specified in `tags_to_add`.
