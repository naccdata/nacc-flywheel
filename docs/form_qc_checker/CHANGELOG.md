# Changelog

All notable changes to this gear are documented in this file.

## 1.0.0
* Update to use nacc-form-validator [v0.3.0](https://github.com/naccdata/nacc-form-validator/releases/tag/v0.3.0)
* Rename/refactor `FlywheelDatastore` class to `DatastoreHelper` to allow more general operations
* Add `compute_gds` as a composite rule to match new GDS score validation

## 0.0.32

* [#102](https://github.com/naccdata/flywheel-gear-extensions/pull/102) Form QC Checker updates
	* Add functionality to update/reset failed visit info in subject metadata
	* Updates how to access rule definitions in S3 - use `nacc-flywheel-gear` user credentials
	* Update optional form validation for non-strict mode
	* Update `FlywheelDatastore` class functionality - retrieve legacy module info from Flywheel admin group metadata project
	* Check whether there's a failed previous visit before evaluating the current visit
	* Move dataview creation/reading to FW proxy class

## 0.0.31

* [#100](https://github.com/naccdata/flywheel-gear-extensions/pull/100) Update to use `nacc-form-validator` v0.2.0

## 0.0.30

* [#89](https://github.com/naccdata/flywheel-gear-extensions/pull/89) Adds support for optional forms validation
	* Uses `optional_forms.json` to define optional forms, and load correct definition file dependin on the value of the **mode** variable for the respective form

## 0.0.29 and earlier

* Undocumented
