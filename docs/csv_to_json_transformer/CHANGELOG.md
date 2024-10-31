# Changelog

All notable changes to this gear are documented in this file.

## 0.0.6
- Creates a JSON file for each record in input CSV file
- Normalizes the visit date to `YYYY-MM-DD` format
- Creates Flywheel hierarchy (subject/session/acquisition) if it does not exist
- Check whether the record is a duplicate
- If not duplicate, upload/update visit file
- Update file info metadata and modality
- For each participant, creates a visits pending for QC file and upload it to Flywheel subject (QC Coordinator gear is triggered on this file)
