# Installation

## Setting up Pixi
To build the environment, manage dependencies and run tasks, FloodAdapt uses [Pixi](https://pixi.sh/latest/), please download and install it by following the instructions on the pixi website.

Before continuing the installation process, make sure you have access to all required private repositories by ensuring you are in the Teams `FloodAdaptUsers` in the [Deltares](https://github.com/orgs/Deltares/teams/floodadaptusers) and [Deltares-research](https://github.com/orgs/Deltares-research/teams/floodadaptusers) organizations.

## Windows
Then run these commands to install FloodAdapt:
```bash
git clone https://github.com/Deltares-research/FloodAdapt.git
cd FloodAdapt
pixi install
```
## Linux
Linux is not supported at the moment, but will be supported in the near future.

## Configure database

Before you can do anything with FloodAdapt, a database is required. Information on how to set it up can be found in the [examples](docs/4_system_setup/index.qmd).
Creating a database is quite complex and is meant for domain experts.
If you would like to use FloodAdapt, but cannot setup a database, please contact `FloodAdapt@deltares.nl`

FloodAdapt uses a database to store, handle and organize input files, output files and static data. This database needs to be configured the first time you want to use FloodAdapt. Which is done via [`flood_adapt/config.py`](flood_adapt/config.py) which contains the `Settings` class to set and validate environment variables, specific to your system.

To initialize FloodAdapt and configure the database, add the following lines to the top of your script / initialize function to validate and set the environment variables:
```python
from pathlib import Path
from flood_adapt import Settings

# Usually ends in `Database` and can contain multiple sites
root = Path("path/to/your/database/root")

# Specifies which site to use
name = "database_name"

# Define the paths to the model kernel binaries
sfincs_bin = Path("path/to/your/sfincs/bin.exe")
fiat_bin = Path("path/to/your/fiat/bin.exe")

# Validate and set environment variables
Settings(
    DATABASE_ROOT=root,
    DATABASE_NAME=name,
    SFINCS_BIN_PATH=sfincs_bin,
    FIAT_BIN_PATH=fiat_path,
    VALIDATE_BINARIES=True,
)
```

## Developing FloodAdapt

To contribute to FloodAdapt, you will need to install additional dependencies. To do so, clone the repository and install the development environment:

```bash
# Install dev environment
git clone https://github.com/Deltares/FloodAdapt
cd FloodAdapt

# This will install the required environment and run the tests to verify
pixi run tests
```

Alternatively, you can open an interactive shell and have pixi take care of activating and updating your environment.
```bash
# `activate` the dev environment
pixi shell -e dev

# Develop
pytest tests/test_x/test_y/test_z.py
python scripts/my_script.py
...
```

### Adding editable installations to your environment

To make developing easier and not have to reinstall packages after every change, editable installs exist.
Pixi supports editable installs, but not in the most intuitive way, as they need to be defined as editable in the project specification.

Example command to add the package `example_package` as an editable install to the default environment:
- go to the non-pixi sections in `pyproject.toml` and comment out the `example_package`. (`[dependencies]` or `[optional-dependencies]`)
- in the pixi section `[tool.pixi.pypi-dependencies]`: add the following line `example_package = {path = "./path/to/example_package", editable = true }`. Note that this path is relative to the root of this project.
- run `pixi update`

## Useful pixi commands
```bash
# Display all pixi commands and options
pixi -h

# Install a non default pixi environment defined in pyproject.toml
pixi install -e [ENV_NAME]

# Update environment(s) to the latest allowed by dependency specifications in pyproject.toml
pixi update

# List all available tasks
pixi task list

# Run a task in the default environment for that task
pixi run [TASK]

# Start a shell in the pixi environment
pixi shell -e [ENV_NAME]

# Add a package to the dependencies
pixi add [PACKAGE]

# Run a task in a specific environment
pixi run -e [ENV_NAME] [TASK]
```

### Generating the documentation

We use `quartodoc` to generate our API documentation automatically. If you have the `docs` optional dependency group installed.
you can do this by running `quartodoc build` from the `docs` directory, and it will create the documentation for you.
After this is done, if you wish, you can build and view the documentation locally by running `quarto preview` from the `docs` directory

The full documentation can be rendered with: `pixi run render-docs`
For more information on all (sub-)tasks of the render pipeline, refer to the section `[tool.pixi.feature.docs.tasks]` defined in [`pyproject.toml`](pyproject.toml).

> Note: To run and render the examples, some data is required that we cannot host on GitHub. To get access to this data, .... TODO
