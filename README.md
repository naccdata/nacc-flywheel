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

### Adding new project

To add a new project

1. Create directory structure
    ```bash
    mkdir -p <new-project-name>/src/python
    touch <new-project-name>/src/python/main.py
    mkdir -p <new-project-name>/src/docker
    touch <new-project-name>/src/docker/Dockerfile
    touch <new-project-name>/src/docker/manifest.json
    ```
2. Add source roots to pants.toml
3. Add configuration for new code/directories
    ```bash
    ./pants tailor ::
    ```

### Adding new dependencies

If you add new python dependencies

1. Edit requirements.txt and add your new dependencies
2. Update dependencies (after editing requirements.txt)
    ```bash
    ./pants generate-lockfiles
    ```

### Working with code

1. Format everything
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
    ./pants run project_management/src/python/create_project.py --  project_management/data/test-project.yaml
    ```
    or
    ```bash
    ./pants run project_management/src/python:bin --  project_management/data/test-project.yaml
    ```

> Scripts will expect that `FW_API_KEY` is set.
> Do this by using `export FW_API_KEY=XXXXXX` using your FW key at the command line.
> Do not set the environment variable in the pants configuration, or otherwise commit your key into the repo.

### Working with docker images

1. Create docker image
    ```bash
    ./pants package project_management/src/docker::
    ```

2. Run docker image
    ```bash
    ./pants run project_management/src/docker::
    ```

Note: don't use `./pants publish` with Gears, need to use the `fw gear` commands to push to the FW instance instead.

### Working with a gear

For `fw gear` commands to work properly, the manifest.json file needs to be in the current working directory.
So, start by changing to ing docker directory where manifest.json is located.
For instance,

    ```bash
    cd project_management/src/docker
    ```

At which point you can use the [fw gear local](https://docs.flywheel.io/hc/en-us/articles/360037690613-Gear-Building-Tutorial-Part-2e-Gear-Testing-Debugging-Uploading) commands.

