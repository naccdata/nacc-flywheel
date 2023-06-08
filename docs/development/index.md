# Development Guide 

This is the development guide for the NACC flywheel gear extensions repo.

## Directory structure

```bash
.
├── bin                 # utility scripts
├── common              # shared code
│   ├── src
│   └── test
├── directory_pull      # gear script to pull users from directory
│   ├── src
│   └── test
├── docs                # documentation
│   ├── development
│   ├── directory_pull
│   ├── index.md
│   ├── project_management
│   ├── push_template
│   └── user_management

├── mypy-stubs          # type stubs for flywheel SDK
│   └── src
├── project_management  # gear script for managing NACC projects
│   ├── data
│   ├── src
│   └── test
├── push_template       # gear script to push template projects
│   ├── src
│   └── test
├── user_management     # gear script for managing project users
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

This repository can be used within a VS Code devcontainer.
To use it, open the repository in VS Code configured to run a devcontainer, and start the container.

If you don't use the devcontainer you'll need to install the FW cli and be sure it is on your path.
Information on installing the `fw-beta` CLI can be found [here](https://flywheel-io.gitlab.io/tools/app/cli/fw-beta/).

The build is managed using [Pants](https://www.pantsbuild.org), which comes with it's own Python interpreter.
So, you only need to install Pants.

To install Pants, run the command 

```bash
bash bin/get-pants.sh
```

At this point, you should be able to run the commands

- `pants version`, and
- `fw-beta --version`

without error.

If you are working in VS Code, see the details [below](#working-within-vscode) to get the code environment setup.

## How each gear project is setup

### Directory structure

Each gear project will have a directory structure like this

    ```bash
    .
    ├── src
    │   ├── docker              # gear configuration
    │   │   ├── BUILD           # - build file for gear
    │   │   ├── Dockerfile      # - Docker configuration for gear
    │   │   └── manifest.json   # - gear manifest
    │   └── python              # script configuration
    │       └── app_package     # app specific directory name
    │           ├── BUILD       # - build file for script
    │           ├── main.py     # - main function for script
    │           └── run.py      # - entry point script 
    └── test
        └── python              # script tests
    ```

A project might include other subdirectories, and the directory `src/python/app_package` should have a name specific to the app.
For instance, the `project_management` directory looks like

```bash
project_management/
├── data
│   └── test-project.yaml
├── src
│   ├── docker
│   │   ├── BUILD
│   │   ├── Dockerfile
│   │   └── manifest.json
│   └── python
│       └── project_app
│           ├── BUILD
│           ├── __init__.py
│           ├── main.py
│           └── run.py
└── test
    └── python
```

where the `app_package` directory is named `project_app`.

Each [build file](https://www.pantsbuild.org/docs/targets) contains metadata about the code and indicates build sources and targets.

For instance, the `project_management/src/python/project_app/BUILD` file contains

   ```python
   python_sources(name="project_app", )

   pex_binary(name="bin", entry_point="run.py")
   ```

which indicates the python directory contains the sources for the `project_app`, and has a build target named `bin` with the `run.py` script as the entrypoint.
(There is no requirement that the sources name and the subdirectory name match.)

And `project_management/src/docker/BUILD` contains

   ```python
   file(name="manifest", source="manifest.json")

   docker_image(name="project-management",
               source="Dockerfile",
               dependencies=[":manifest", "project_management/src/python:bin"],
               image_tags=["0.0.1", "latest"])

   experimental_run_shell_command(
       name="gear",
       command="/home/vscode/bin/fw-beta gear",
       description="run fw gear command for project_management",
       workdir="project_management/src/docker")
   ```

which describes a Docker image target that depends on the manifest file, and the pex target in the python directory.
It also enables a target `gear` that allows running `fw gear` in the context of the `project_management/src/docker` directory.

### Gear scripts

The scripts are inspired by Flwheel's [template project](https://gitlab.com/flywheel-io/scientific-solutions/gears/templates/skeleton).
(Flywheel's template assumes one Gear per repository, which doesn't work for a monorepo.)
In that template, the Gear has two scripts `run.py` and `main.py` (or, rather, a file with a name specific to the app).
The `run.py` script manages the environment, and the `main.py` does the computation.

Each `run.py` script will have this structure, where the first check is whether `--gear` was given as a command line argument.
That determines whether to get the remainder of the arguments from the gear context or from the command line arguments.

```python
def main():
    parser = <call_appropriate_command_line_parser>
    args = parser.parse_args()

    if args.gear: # script is being run as a gear
        ... # get arguments from gear context (refs manifest file)
    else:
        ... # get arguments from command line parser
    
    ... # get api key and connect to FW
    ... # gather any information based on arguments
    run(...) # call run method from main.py
```

The file `common/src/python/inputs/arguments.py` defines three variants of command line parsers, which can be used in different scenarios:

 - `build_base_parser` -- command line parser with arguments to indicate whether running a gear, whether doing a dry run, whether to only work on centers (e.g., groups) tagged as new, and what the admin group is for the system
 - `build_parser_with_output` -- builds a base parser with a file argument for output
 - `build_parser_with_input` -- builds a base parser with a file argument for input


The `main.py` script defines a `run` method that performs the computation.
Most of the work is done by calling code from the `common` subdirectory. 

### Dockerfile

The Dockerfile sets up the Gear's working environment

   ```docker
   FROM python:3.10

   ENV BASE_DIR=/flywheel/v0
   RUN mkdir -p ${BASE_DIR}/input

   WORKDIR ${BASE_DIR}

   COPY project_management/src/docker/manifest.json ${BASE_DIR}
   COPY project_management.src.python/bin.pex /bin/run

   ENTRYPOINT [ "/bin/run" ]
   ```

The key details are setting up the `/flywheel/v0` directory with the manifest file, and copying the binary pex file into the image with it set as the entrypoint for the container.

### Gear manifest

The manifest is a JSON file that defines the metadata for the gear.
Look at the FW gear documentation for more detail, but there are three key details and how they relate to other files in the directories for each gear project.

1. The `docker/BUILD` file defines the Docker image target, which should correspond to `custome.gear-builder.image` in the manifest file.
   For instance, the manifest file for `project_management` has

   ```json
   {
    ...
       "custom": {
           "gear-builder": {
               "category": "utility",
               "image": "naccdata/project-management"
           },
           ...
       },
    ...
   }
   ```
   where the image corresponds to the name of the image in the build script.
   (The category indicates this is a utility gear within FW.)

2. If the gear takes an input file, this should be named in the `inputs` within the manifest.
   The name has to be used within the `run.py` script to find the file.

   For instance, the project_management gear manifest has 

   ```json
   {
    ...
       "inputs": {
           "project_file": {
               "description": "The project YAML file",
               "base": "file",
               "type": {
                   "enum": [
                       "source code"
                   ]
               }
           }
       },
    ...
   }
   ```

3. Any other arguments to the  script collected in `run.py` should be given in the `config` of the manifest

   For instance, the project_management manifest file has

   ```json
   {
    ...
       "config": {
           "dry_run": {
               "description": "Whether to do a dry run",
               "type": "boolean",
               "default": false
           },
           "admin_group": {
               "description": "Name of the admin group",
               "type": "string",
               "default": "nacc"
           },
           "new_only": {
               "description": "Only create projects for centers tagged as new",
               "type": "boolean",
               "default": false
           }
       },
    ...
   }
   ```

4. The manifest indicates how to run the script.
   For this we need to know that the Dockerfile places the pex file in `/bin/run`, and the `run.py` script assumes it is given the `--gear` command line argument when run as a gear.
   So, the gear is executed as `/bin/run --gear`, which is indicated in the manifest as

   ```json
   {
    ...
       "command": "/bin/run --gear"
   }
   ```

### Gear documentation

In addition to the project directory, each gear has a directory in `docs` that contains an `index.md` file.


## Adding a new gear

The `bin/new_gear.sh` script will set up the directories for a new gear.
The script takes the project name (and assumes snakecase)

```bash
bash bin/new_gear.sh zebra_management
```

This will create a directory with the name given and the structure

```bash
zebra_management
├── src
│   ├── docker
│   │   ├── BUILD
│   │   ├── Dockerfile
│   │   └── manifest.json
│   └── python
│       └── zebra_app
│           ├── BUILD
│           ├── main.py
    │       └── run.py
└── test
    └── python
```

Make the following changes:

1. Check the `BUILD` files and make sure the target and dependency names match what you expect.

   You may want to edit the `python_sources` name argument in `zebra_management/src/python/zebra_app/BUILD` to set a new app name.
   By default it will pick the prefix before the underscore, so the default app name for a gear named `zebra_management` will be `zebra_app`.
   Similarly, the Docker image will be named `zebra-management`, replacing the underscore with a hyphen.
   If you want to change this, you'll need to change the image name in both the `docker/BUILD` and `docker/manifest.json` files.

2. Edit the `manifest.json` file

   At the top level, change the `name`, `label`, `description`, `version`, `author`.
   Under `custom.gear-builder` update `image` with the information from the `docker/BUILD` file.
   Then make any changes needed for the command line arguments to `inputs` and `config`.
   By default the script will use the prefix before the underscore to name the file key for `inputs`, and for a project named `zebra_management` will use `zebra_file` as the key in the manifest and the `run.py` script.
   Make sure these details should match up with the information used by your `run.py` script to get parameters.

To complete the gear, you will likely need to make changes to `run.py` and the `main` scripts.
In `run.py`, add anything that needs to be done gathering information from the environment, and the main script will do the actual computation mostly using code from the `common` directory.
There may be exceptions to this scheme.
For instance, the `directory_pull` script uses `run.py` without a main script because it behaves differently depending on whether it is run as a gear.


## Adding common code

If you need to add a file to the common library, either place it in an existing subdirectory for the package that makes the most sense, or create a directory for a new package.

If you need to create a new package structure, add the subdirectory with the code, add an `__init__.py` file, and then run `pants tailor ::`.
Then change the new `BUILD` file so that it contains the line `python_sources(name="lib")`

## Adding new dependencies

If you add new python dependencies

1. Edit `requirements.txt` in the top directory and add your new dependencies.
2. Regenerate the lock file
    ```bash
    pants generate-lockfiles
    ```

## Working with code

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

4. Run tests for the common subproject
    ```bash
    pants test common::
    ```

5. Run type checker for the common subproject
    ```bash
    pants check common::
    ```

5. Run the project management script (The `--` is required before the arguments)
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

## Working with docker images

1. Create docker image
    ```bash
    pants package project_management/src/docker::
    ```

2. Run docker image
    ```bash
    pants run project_management/src/docker::
    ```

Note: don't use `pants publish` with Gears, you need to use the gear commands below to push to the FW instance instead.

## Working with a gear

The repo is setup to use the [`fw-beta` CLI tool](https://flywheel-io.gitlab.io/tools/app/cli/fw-beta/).
(If you are working within the VSCode devcontainer, `fw` is an alias for `fw-beta`.)

To get started, first login to the FW instance using `fw login`.

After that you can use the `gear` target defined in the `docker/BUILD` file of the gear project.
For instance, the command 

```bash
pants run project_management/src/docker:gear
```

runs `fw gear` within the `project_management/src/docker` directory.
See the [`fw gear` documentation](https://flywheel-io.gitlab.io/tools/app/cli/fw-beta/gear/) for details on the options to this command.

Remember that in pants to provide arguments you need to use `--` between the command and the options.
For instance,

```bash
pants run project_management/src/docker:gear -- ls
```

lists the gears installed on the instance.

This should enable doing things such as [local debugging](https://docs.flywheel.io/hc/en-us/articles/360037690613-Gear-Building-Tutorial-Part-2e-Gear-Testing-Debugging-Uploading).

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

If you run into any issues, consult the [instructions for setting up an IDE](https://www.pantsbuild.org/docs/setting-up-an-ide)