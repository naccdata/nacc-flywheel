# Identifier Lookup

The identifier-lookup gear reads participant IDs from a tabular (CSV) input file, with one participant per row, and uses the Identifiers API to check whether each ID corresponds to a NACCID.

The gear outputs a CSV file consisting of the rows for participants that have NACCIDs, but with a column for the NACCID.

For each participant ID without a corresponding NACCID, the gear flags an error through a (YTD) Flywheel error logging mechanism.
