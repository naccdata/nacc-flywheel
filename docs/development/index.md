# Development Guide 

This is the development guide for the NACC flywheel gear extensions repo.

## Directory structure

```bash
.
├── common              # shared code
│   ├── src
│   └── test
├── docs
│   ├── development
│   ├── directory_pull
│   ├── index.md
│   ├── project_management
│   ├── push_template
│   └── user_management
├── project_management  # script for managing NACC projects
│   ├── data
│   ├── src
│   └── test
├── push_template
│   ├── src
│   └── test
├── user_management     # script for managing project users
│   ├── directory
│   ├── src
│   └── test
├── dist                # Directory containing distributions built by Pants
├── mypy.ini
├── pants               # Pants script
├── pants.toml          # Pants configuration
├── python-default.lock # dependency lock file
├── requirements.txt    # Dependencies for full repo
├── BUILD               # Build declaration of python dependencies
├── LICENSE
└── README.md
```

[To update this structure, use `tree -L 2` and select missing chunks for inclusion.]

## Working with this repository

This respository is managed using [Pants](https://www.pantsbuild.org).

To get started, first run

```bash
bash get-pants.sh
```

It may also be opened in a VS Code devcontainer with a Python 3 environment and whatever is needed installed.
See the details [below](#working-within-vscode).

If you don't want to use the devcontainer you'll need to make sure you have a compatible environment setup along with the FW cli.
For details, see the files in `.devcontainer`, or just use the devcontainer.

If things are setup correctly, you will be able to run `pants version` and get a version number as a response, and `which fw` and find the FW cli executable.

## Care and feeding

### Adding new project

To add a new project

1. Create directory structure
    ```bash
    bash bin/new_gear.sh <new-project-name>
    ```

    This will create a directory with the name given and the structure

    ```bash
    .
    ├── src
    │   ├── docker
    │   │   ├── BUILD
    │   │   ├── Dockerfile
    │   │   └── manifest.json
    │   └── python
    │       ├── BUILD
    │       └── run.py
    └── test
        └── python
    ```
    
2. Add configuration for new code/directories

    ```bash
    pants tailor ::
    ```

    this will add a `BUILD` file in the `src/docker` and `src/python` subdirectories.

3. Edit the BUILD files

   The python BUILD file will look like

   ```python
   python_sources(name="project_app", )

   pex_binary(name="bin", entry_point="run.py")
   ```

   Replace `project_app` with the new app name.

   The docker BUILD file should look like 

   ```python
   file(name="manifest", source="manifest.json")

   docker_image(name="project-management",
                source="Dockerfile",
                dependencies=[":manifest", "project_management/src/python:bin"],
                image_tags=["0.0.1", "latest"])
   ```

   where you should replace the `project-management` image name, and `project_management` directory name.

4. Edit the docker file so that it has the content

   ```docker
   FROM python:3.10

   ENV BASE_DIR=/flywheel/v0
   RUN mkdir -p ${BASE_DIR}/input

   WORKDIR ${BASE_DIR}

   COPY project_management/src/docker/manifest.json ${BASE_DIR}
   COPY project_management.src.python/bin.pex /bin/run

   ENTRYPOINT [ "/bin/run" ]
   ```

   where `project_management` is replaced with the directory of your new project.

4. Edit the manifest.

   For the manifest, copy the file from an existing project. 
   At the top level, change the `name`, `label`, `description`, `version`, `author`.
   Under `custom.gear-builder` update `image` with the information from the `docker/BUILD` file.
   Then make any changes needed for the command line arguments to `inputs` and `config`.
   These details should match up with the information used by your `run.py` script to get parameters.

### Adding common code

If you need to add a file to the common library, either place it in the current subdirectory for the package that makes the most sense.

If you need to create a new package structure, add the subdirectory with the code, add an `__init__.py` file, and then run `pants tailor ::` like above.
Make sure the BUILD file contains the line `python_sources(name="lib")`


### Adding new dependencies

If you add new python dependencies

1. Edit requirements.txt and add your new dependencies
2. Update dependencies (after editing requirements.txt)
    ```bash
    pants generate-lockfiles
    ```

### Working with code

1. Format everything
    ```bash
    pants fmt ::
    ```

2. Format just the common subproject
    ```bash
    pants fmt common::
    ```

3. Lint
    ```bash
    pants lint ::
    ```

4. Run tests for common subproject
    ```bash
    pants test common::
    ```

5. Run type checker for common subproject
    ```bash
    pants check common::
    ```

5. Run the create project script (The `--` is required before the arguments)
    ```bash
    pants run project_management/src/python/run.py --  project_management/data/test-project.yaml
    ```
    or
    ```bash
    pants run project_management/src/python:bin --  project_management/data/test-project.yaml
    ```

> Scripts will expect that `FW_API_KEY` is set.
> Do this by using `export FW_API_KEY=XXXXXX` using your FW key at the command line.
> Do not set the environment variable in the pants configuration, or otherwise commit your key into the repo.

### Working with docker images

1. Create docker image
    ```bash
    pants package project_management/src/docker::
    ```

2. Run docker image
    ```bash
    pants run project_management/src/docker::
    ```

Note: don't use `pants publish` with Gears, you need to use the `fw gear` commands to push to the FW instance instead.

### Working with a gear

For `fw gear` commands to work properly, the manifest.json file needs to be in the current working directory.
So, start by changing to ing docker directory where manifest.json is located.
For instance,

    ```bash
    cd project_management/src/docker
    ```

At which point you can use the [fw gear local](https://docs.flywheel.io/hc/en-us/articles/360037690613-Gear-Building-Tutorial-Part-2e-Gear-Testing-Debugging-Uploading) commands.

## Working within VSCode

This repository is setup with a VSCode devcontainer. 
To use it you will need to install VSCode, Docker, and enable dev containers within VSCode.
When you open the repository within the devcontainer, the environment is a python3 container, with the flywheel cli installed.

To enable VSCode access to the python dependencies.

1. to create a `.env` file that sets the `PYTHONPATH` for source code in the project.
   ```bash
   bash bin/set-source-roots.sh
   ```
2. Update dependencies
   ```bash
   pants generate-lockfiles
   ```
3. Export virtual environment
   ```bash
   bash bin/set-venv.sh
   ``` 

If you run into any issues, consult , the [instructions for setting up an IDE](https://www.pantsbuild.org/docs/setting-up-an-ide)