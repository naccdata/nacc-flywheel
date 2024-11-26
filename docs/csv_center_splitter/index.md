# CSV Center Splitter

Splits a CSV of participant data by the center ID, and writes the results into projects for the corresponding centers.

## Input Format

Along with the input CSV, the gear takes in a config YAML with the following fields:

```yaml
center_key: <column name from the input CSV with the ADCID>
target_project: <name of the target Flywheel project to write results to per center>
```

The ADCIDs are mapped to the Flywheel group ID using the custom info found in the `metadata` project.

### Input CSV and Example

The input CSV is expected to at minimum have the following expected fields:

Example:

```csv

```

### Config Example

```yaml
center_key: ADCID
target_project: distribution-ncrad-biomarker
```
