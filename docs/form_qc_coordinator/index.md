# Form QC Coordinator

This gear coordinates the data quality checks for a given participant. It internally triggers the [Form QC Checker](../form_qc_checker/index.md) gear to validate each visit.
- Visits are evaluated in the order of the visit date. 
- If a visit fails validation, none of the subsequent visits will be evaluated until the failed visit is fixed.
- If a visit is modified, all the subsequents visits are re-evaluated for accuracy.

### Environment
This gear uses the AWS SSM parameter store, and expects that AWS credentials are available in environment variables (`AWS_SECRET_ACCESS_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_DEFAULT_REGION`) within the Flywheel runtime.


### Running
This gear can only be run at subject level.

### Inputs
- **visits_file**: YAML file with list of new/updated visits for the module/participant. [Example](../../gear/form_qc_coordinator/data/example-input.yaml)
- **qc_configs_file**: JSON file with QC gear config information. [Example](../../gear/form_qc_coordinator/data/qc-gear-configs.json)

### Configs
Gear configs are defined in [manifest.json](../../gear/form_qc_coordinator/src/docker/manifest.json).

