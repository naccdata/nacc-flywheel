# nacc-flywheel

Monorepo for NACC Flywheel adaptations.

Consists of python scripts for managing projects and project users.


```bash
.
├── common              # shared code
│   ├── src
│   └── test
├── project_management  # scripts for managing NACC projects
│   ├── data
│   ├── src
│   └── test
├── user_management     # scripts for managing project users
│   ├── directory
│   ├── src
│   └── test
├── dist
│   └── export
├── pants               # Pants script
├── pants.toml          # Pants configuration
├── python-default.lock # dependency lock file
├── requirements.txt    # Dependencies for full repo
├── BUILD               # Build declaration of python dependencies
├── LICENSE
└── README.md
```

The repository is setup to use Pants (https://www.pantsbuild.org) for the build.

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