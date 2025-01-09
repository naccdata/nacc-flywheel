# Prescreening

Prescreens input files to queue for form-scheduler gear. Looks at the file's basename suffix, and passes it if matches any of the accepted modules (case-insensitive). It then checks if the scheduler gear is running and triggers it if there are none in the `running` or `pending` state.

## Inputs

This gear takes two input files:

1. The input file (typically expected to be a CSV but not required) to verify
2. The scheduler gear config file - an example can be found in [gear/prescreening/data/form-scheduler-configs.json](../../gear/prescreening/data/form-scheduler-configs.json)

The gear also takes the following optional input parameters:

| Parameter | Required? | Default | Description |
| --------- | --------- | ------- | ----------- |
| `accepted_modules` | No | `"ENROLL,UDS,FTLD,LBD"` | Comma-deliminated list of accepted modules. Cannot be empty. |
| `tags_to_add` | No | `"queued"` | Comma-deliminated list of tags to add to the prescreened file. Cannot be empty. |
| `dry_run` | No | `false` | Whether or not to do a dry run - will verify file but will not add tags |

The gear does not have any explicit outputs but will add the tags specified in `tags_to_add` to the input file and trigger the schedule gear if not currently pending/running.
