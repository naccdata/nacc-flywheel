# Pull Metadata

Script to pull metadata files from S3 Bucket and distribute to the same project in group of each center with data in the data files.

## Environment

This gear assumes it is running within the NACC admin group in Flywheel which is configured to provide AWS credentials for the gear bot user.

Also, assumes the data has been placed in an S3 bucket.

## Flywheel configuration

## Running

Flywheel utility gears are either triggered by a gear rule, or run from a batch script.

Both require a configuration with the following:

- the parameter path to the root for the credentials for the S3 bucket. The credentials should include parameters `accesskey`, `secretkey`, `region`
- the bucket prefix for the input table files
- the label of the destination projects to be used within each center

A batch script would be
```python
from flywheel import Client

client = Client(os.environment.get("FW_API_KEY"))
pull_gear = client.lookup("gears/pull-metadata")

config = {
    dry_run: False,
    s3_param_path: '/prod/path/to/s3/credentials',
    bucket_name: 'input/bucket/prefix',
    destination_label: 'destination-project-label',
    table_list: [ 'table-name1.csv', 'table-name2.csv', 'table-name3.csv' ]
}

pull_gear.run(config=config, destination=admin_project)
```

This gear doesn't use the destination, but it needs to be set.
For this to work, set `admin_project` to a project in the admin group.
For NACC, use the group `nacc/project-admin`.
