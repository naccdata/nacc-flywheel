# REDCap Project Info Management

This gear adds REDCap project information needed to integrate a form project with a center form ingest pipeline in Flywheel.

Reads a YAML file that contains a list of objects such as

```yaml
---
- center-id: sample-program
  study-id: test
  project-label: ingest-form
  projects:
  - redcap-pid: 1
    label: ptenrlv1
```

Adds the information to the ingest project metadata for the study within the center group.

Gear must be run with admin privileges.
