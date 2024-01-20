# Form QC Checker

This gear reads a JSON form data file and uses a form- and study-specific set of QC rules to check the values. QC rule definitions are downloaded from a S3 bucket. Gear uses the [NACC Form Validator](https://github.com/naccdata/nacc-form-validator) library for rule evaluation.

## Environment

This gear expects Flywheel to provide environment variables for AWS credentials for the gearbot user: AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION.

You cannot replicate this environment for a local run without putting these values in the gear manifest.json and risk checking them into version control. So, please don't try -- instead use pytest to test non-gear aspects.

## Running

Flywheel utility gears are either triggered by a gear rule, or run from a batch script.

### Inputs
- form_data_file: The form data JSON file to validate, this is required.

### Configs
- The parameter path to the root for the credentials for the S3 bucket containing rule definitions. The credentials should include parameters `accesskey`, `secretkey`, `region`
- The validation mode (strict_mode): If set to False, input data variables that are not in the rule definitions are skipped from validation
- The primary key field of the project/study data (e.g. naccid)

Example config:
```python
config = {
    dry_run: False,
    s3_param_path: '/prod/path/to/s3/credentials',
    primary_key: 'naccid',
    strict_mode: True,
    tag: 'form-qc-checker'
}
```

### Outputs

TODO - describe error report