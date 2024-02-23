# Study management

The project management app builds containers within Flywheel for a coordinating center supported study.

A *coordinating center supported study* is a research activity for which data is being collected at the coordinating center.
For NACC is this primarily the ADRC program for which data is captured at Alzheimer's Disease Research Centers (ADRCs), and then transferred to NACC for harmonization and release.

## Input 

This app takes a YAML file describing the study and creates containers within Flywheel to support the ingest and curation of the collected data.

The file format is

```yaml
---
study: <study-name>
study-id: <string-identifier>
primary: <whether is primary study>
centers: <list of center information>
datatypes: <list of datatype identifiers>
published: <whether the data is published>
```

A center is described using the following fields

```yaml
name: <center name>
center-id: <string identifier>
adcid: <int>
is-active: <whether the center is active>
tags: <list of strings for tagging study>
```

Notes:
1. Only one study should have `primary` set to `True`.

2. Like with any YAML file, you can include several study definitions separated by a line with `---`.
   However, it is more pragmatic to have one file per study for large studys.

2. The `tags` are strings that will be permissible as tags within the group for the center. 
   Each tag will also be added to ingest studys within the center's pipeline(s).

3. Choose `center-id` values to be mnemonic for the coordinating center staff.
   The choice will be visible to centers, but they will not need to type the value in regular interactions. 
   Staff, on the other hand, will need to use the strings in filters.

4. The `adcid` is an assigned code used to identify the center within submited data.
   Each center has a unique ADC ID.

5. Datatypes are strings used for creating ingest containers, and matching to sets of gear rules needed for handling ingest.


## Example

```yaml
---
study: "Project Tau"
study-id: tau
centers:
  - name: "Alpha Center"
    center-id: alpha
    adcid: 1
    is-active: True
    tags:
      - 'center-code-1006'
  - name: "Beta Center"
    center-id: beta-inactive
    adcid: 2
    is-active: False
    tags:
      - 'center-code-2006'
datatypes:
  - form
  - dicom
published: True
---
study: "Project Zeta"
study-id: zeta
centers:
  - name: "Alpha Center"
    center-id: alpha
    adcid: 1
    is-active: True
    tags:
      - 'center-code-1006'
  - name: "Gamma ADRC"
    center-id: gamma-adrc
    adcid: 3
    is-active: True
    tags:
      - 'center-code-5006'
datatypes:
  - form
published: False
```

## Running the App

To run from the command-line, first set the API key by running

```bash
export FW_API_KEY=XXXXXX
``` 
using your FW key instead of the `XXXXXX`. This key is available on your FW profile page.

```bash
pants run project_management/src/python/project_app:bin --  --no-gear project_management/data/project-definition.yaml
```

you can also specify the name of your admin group using `--admin_group` (default is `nacc`).
And, do a dry run using `--dry_run`

See the developers guide for information on deploying the app as a Docker container or Gear.