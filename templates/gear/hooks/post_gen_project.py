"""Script to generate the CI for a new gear."""

"""Script to generate the CI a new library."""

MODULE_NAME: str = "{{ cookiecutter.module_name }}"
PACKAGE_NAME: str = "{{ cookiecutter.package_name }}"
CI_FILE_PATH: str = f"../../.github/workflows/ci_{MODULE_NAME}.yaml"

with open(CI_FILE_PATH, "w") as handle:
    handle.writelines(
        f"""---
name: CI gear/base

on:
  pull_request:
    paths:
      - 'requirements.txt'
      - 'python-default.lock'
      - '.github/workflows/python_reusable.yaml'
      - '.github/workflows/ci_{MODULE_NAME}.yaml'
      - 'gear/{MODULE_NAME}/**'
  workflow_dispatch:  # Allows to trigger the workflow manually in GitHub UI

jobs:
  ci-gear-{PACKAGE_NAME}:
    uses:
      ./.github/workflows/python_reusable.yml
    with:
      working-directory: gear/{MODULE_NAME}
    secrets: inherit"""
    )