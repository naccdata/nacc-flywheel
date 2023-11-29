# CSV to JSON Transformer

Gear reads a tabular (CSV) file of form data with one participant per row and creates a JSON file for each participant performing column transformations depending on the form type.

The JSON file will be added to a subject/session/acquisition for the participant determined by columns `NACCID`, `visitnum`, `visitdate` 

[**CLARIFY WHAT COLUMNS NEEDED TO ATTACH TO SUBJECT/SESSIONS. MAY DEPEND ON `module` VALUE**]

Transformations are determined by the value of the `module` column and can include:

- removing a column
- renaming a column header
- modifying the values in a column (?TBD)