# nacc-flywheel

Monorepo for NACC Flywheel adaptations.

Consists of python scripts for managing projects and project users.

1. Project management - creates and manages NACC projects as
   Flywheel groups and projects.
2. User management - attaches users to centers in roles identified in NACC directory.

The repository is setup to use Pants (https://www.pantsbuild.org) for the build.

## Directory structure

```bash
.
├── common              # shared code
│   ├── src
│   └── test
├── project_management  # script for managing NACC projects
│   ├── data
│   ├── src
│   └── test
├── user_management     # script for managing project users
│   ├── directory
│   ├── src
│   └── test
├── dist                # Directory containing distributions built by Pants
├── pants               # Pants script
├── pants.toml          # Pants configuration
├── python-default.lock # dependency lock file
├── requirements.txt    # Dependencies for full repo
├── BUILD               # Build declaration of python dependencies
├── LICENSE
└── README.md
```

## Care and feeding



Commands are
1. Format every thing
    ```bash
    ./pants fmt ::
    ```
2. Format just the common subproject
    ```bash
    ./pants fmt common::
    ```
3. Lint
    ```bash
    ./pants lint ::
    ```
4. Run tests for common subproject
    ```bash
    ./pants test common::
    ```
5. Run the create project script (The `--` is required before the arguments)
    ```bash
    ./pants run project_management/src/create_project.py --  project_management/data/test-project.yaml
    ```

6. Update dependencies (after editing requirements.txt)
    ```bash
    ./pants generate-lockfiles
    ```
    
7. Add configuration for new code/directories
    ```bash
    ./pants tailor ::
    ```