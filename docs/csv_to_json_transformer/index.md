# CSV to JSON Transformer

Gear reads a tabular (CSV) file of form data with one participant visit per row and creates a JSON file for each visit performing column transformations depending on the form type (or `module`).

The JSON file will be added to a subject/session/acquisition for the participant determined by the `module` value as follows,
- UDS
    - subject - [`naccid`]
    - session - FORMS-VIST-[`visitnum`]
    - acquisition - UDSv[`formver`]
- FTLD
    - subject - [`naccid`]
    - session - FORMS-VIST-[`visitnum`]
    - acquisition - FTLDv[`formver`]
- LBD
    - subject - [`naccid`]
    - session - FORMS-VIST-[`visitnum`]
    - acquisition - LBDv[`formver`]
- Milestone
    - subject - [`naccid`]
    - session - MILESTONE-[`visitdate`]
    - acquisition - MLSTv[`formver`]
- NP
    - subject - [`naccid`]
    - session - MILESTONE-[`visitdate`]
    - acquisition - NPv[`formver`]
    
JSON filename: [subject]-[session]-[acquisition].json
(e.g. NACC000123-FORMS-VISIT-05-UDSv4.json)

Transformations are determined by the `module` value and can include:
- removing a column
- renaming a column header
- modifying the values in a column (?TBD)