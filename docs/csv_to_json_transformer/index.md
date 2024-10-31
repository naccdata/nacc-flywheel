# CSV to JSON Transformer

Gear reads a tabular (CSV) file of form data with one participant visit per row and creates a JSON file for each visit performing column transformations depending on the form type (or `module`).

The JSON file will be added to a subject/session/acquisition for the participant determined by the `module` value as follows,
- UDS
    - subject - [`naccid`]
    - session - FORMS-VIST-[`visitnum`]
    - acquisition - [`module`]
- FTLD
    - subject - [`naccid`]
    - session - FORMS-VIST-[`visitnum`]
    - acquisition - [`module`]
- LBD
    - subject - [`naccid`]
    - session - FORMS-VIST-[`visitnum`]
    - acquisition - [`module`]
- Milestone
    - subject - [`naccid`]
    - session - MILESTONE-[`visitdate`]
    - acquisition - [`module`]
- NP
    - subject - [`naccid`]
    - session - NP-RECORD-[`visitdate`]
    - acquisition - [`module`]
    
JSON filename: [subject]-[session]-[acquisition].json
(e.g. NACC000123-FORMS-VISIT-05-UDSV4.json)

Transformations are determined by the `module` value and can include:
- removing a column
- renaming a column header
- normalizing visit date to `YYYY-MM-DD` format
- modifying the values in a column (?TBD)