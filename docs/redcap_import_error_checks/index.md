# REDCap Import Error Checks

Bulk imports all error checks to REDCap.

The error check CSVs are created and uploaded to [uniform-data-set](https://github.com/naccdata/uniform-data-set), which are then stored in S3 at [s3://nacc-qc-rules/CSV/](https://us-west-2.console.aws.amazon.com/s3/buckets/nacc-qc-rules?region=us-west-2&bucketType=general&tab=objects). The gear uses this S3 path to pull the CSVs from to perform the import to REDCap.

Additionally, any error codes that were converted to 3.1 (LBD-only) and/or FVP will also have their error codes automatically generated for the import.
