# Gear template

A cookiecutter template to create new Gear in the monorepo

## Preliminaries 

Within the VS Code devcontainer, run

```bash
pipx install cookiecutter
```

If you are not using the devcontainer, see the [cookiecutter docs](https://cookiecutter.readthedocs.io/en/2.5.0/README.html) for installation.

## Create Gear

Run cookiecutter from the root directory of the monorepo

```bash
cookiecutter templates/gear --output-dir gear/
```

You will then be prompted to instantiate the gear.
Type `enter` to accept the default value, or provide a new value.

```
  [1/6] gear_name (Gear Name): Junk Gear
  [2/6] gear_description (A NACC gear for Flywheel): A junk gear for trying this out
  [3/6] package_name (junk-gear): 
  [4/6] module_name (junk_gear): 
  [5/6] app_name (junk_gear_app): junk_app
  [6/6] image_tag (0.0.1): 
```
