# FloodAdapt
FloodAdapt is a decision-support tool that seeks to advance and accelerate flooding-related adaptation planning. It brings rapid, physics-based compound flood and detailed impact modelling into an easy-to-use system, allowing non-expert end-users to evaluate a wide variety of compound events, future conditions, and adaptation options in minutes.  FloodAdapt serves as a connector between scientific advances and practitioner needs, improving and increasing the uptake and impact of adaptation research and development.

To make decisions on flood adaptation, communities need to understand how climate and socio-economic changes will affect flood risk and the risk-reduction potential of various adaptation options. This type of information is usually costly to acquire, and models are often too slow and labor-intensive to evaluate all the scenarios required to understand the impacts and effectiveness of potential adaptation decisions. FloodAdapt addresses this by making rapid, physics-based compound flood modeling and detailed impact modeling accessible to non-expert end-users, allowing them to evaluate a wide variety of compound events, future conditions, and adaptation options in minutes.

FloodAdapt was developed as a rapid planning tool with a straightforward graphical user interface for scenario generation, simulation, and visualization of spatial flooding and flooding impacts. Decision-making needs at the community level were central to the design of FloodAdapt. Users can answer planning questions like: “How will potential adaptation options reduce flood impacts?”, “How will those options perform for different types of events, like hurricanes, king tides, or heavy rainfall?”, “Which neighborhoods will benefit most?”, “How will those options hold up in the future?”

Users specify what-if scenarios composed of historic or synthetic weather events, climate or socio-economic future projections, and adaptation measures.
The backend of FloodAdapt leverages the open-source, state-of-the-art process-based compound flood model SFINCS (https://github.com/Deltares/SFINCS) that can accurately predict compound flooding due to surge, rainfall, and river discharge, at a fraction of the computation time typically required by physics-based models. The damage model included in FloodAdapt is the Deltares-developed flood impact assessment tool Delft-FIAT (https://github.com/Deltares/Delft-FIAT). It calculates the flood damages to individual buildings and roads, and – when social vulnerability data is available – aggregates these damages over vulnerability classes.

FloodAdapt can greatly support adaptation planning by allowing users to explore many scenarios. It can be used to evaluate flooding and impacts due to compound weather events, like hurricanes, king tides, and rainfall events. Users can evaluate flooding, impacts, and risk considering user-specified projections of sea level rise, precipitation increase, storm frequency increase, population growth, and economic growth. Users can also test out adaptation options, like sea walls, levees, pumps, home elevations, buyouts and floodproofing.

Recent developments of the decision-support system include (1) simplifying and partially automating the setup of the SFINCS and Delft-FIAT models, (2) improving the user experience, (3) better supporting adaptation planning with improvements like metrics tables, infographics, better visualizations in the user interface, adding in additional adaptation options to evaluate, and calculating benefits of adaptation options, and (4) incorporating social vulnerability and equity into the evaluation of adaptation options to support equitable adaptation planning.

FloodAdapt is currently in an intensive development stage. Independent usage of the repository will be challenging prior to end-of-year 2024. FloodAdapt documentation will be expanded on throughout 2024.

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

#### TODO add section for the DatabaseBuilder.

FloodAdapt uses a database to store, handle and organize input files, output files and static data. This database needs to be configured the first time you want to use FloodAdapt. Which is done via `flood_adapt/misc/config.py` which contains the `Settings` class to set and validate environment variables, specific to your system.

To initialize FloodAdapt and configure the database, add the following lines to the top of your script / initialize function to validate and set the environment variables:
```python
from pathlib import Path
from flood_adapt.misc.config import Settings

# Usually ends in `Database` and can contain multiple sites
root = Path("path/to/your/database/root")

# Specifies which site to use
name = "database_name"

# Contains the model kernels to run that perform the calculations
system_folder = Path("path/to/your/system/folder")

# Validate and set environment variables
Settings(
    DATABASE_ROOT=root,
    DATABASE_NAME=name,
    SYSTEM_FOLDER=system_folder,
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
