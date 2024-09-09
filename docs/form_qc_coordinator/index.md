# Form QC Coordinator

This gear coordinates the data quality checks for a given participant. It internally triggers the [Form QC Checker](https://github.com/naccdata/flywheel-gear-extensions/blob/main/docs/form-qc-checker/index.md) gear to validate each visit.
- Visits are evaluated in the order of the visit date. 
- If a visit fails validation, none of the subsequent visits will be evaluated until the failed visit is fixed.
- If a visit is modified, all the subsequents visits are re-evaluated for accuracy.

## Environment

This gear expects Flywheel to provide environment variables for AWS credentials for the gearbot user: AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID, AWS_DEFAULT_REGION.

You cannot replicate this environment for a local run without putting these values in the gear manifest.json and risk checking them into version control. So, please don't try -- instead use pytest to test non-gear aspects.

## Running

This gear can only be run at subject level.

### Inputs
- **visits_file**: YAML file with list of new/updated visits for the module/participant. [Example](../gear/form_qc_coordinator/data/test-input.yaml)
- **qc_configs_file**: JSON file with QC gear config information. [Example](../gear/form_qc_coordinator/data/qc-gear-configs.json)

### Configs
Gear configs are defined in [manifest.json](https://github.com/naccdata/flywheel-gear-extensions/blob/main/gear/form_qc_coordinator/src/docker/manifest.json)

