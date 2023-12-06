# Identifier Lookup

The identifier-lookup gear reads participant IDs from a tabular (CSV) input file and checks whether each ID corresponds to a NACCID.
The input file is assumed to have one participant per row with columns ADCID (NACC assigned center ID), and PTID (center assigned participant ID).

The gear outputs a copy of the CSV file consisting of the rows for participants that have NACCIDs, with an added column for the NACCID.

If there are any rows where the participant ID has no corresponding NACCID, an error file is also output
- An error file with a row for each input row in which participant ID has no corresponding NACCID.
