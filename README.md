# FloodAdapt
FloodAdapt is a decision-support tool that seeks to advance and accelerate flooding-related adaptation planning. It brings rapid, physics-based compound flood and detailed impact modelling into an easy-to-use system, allowing non-expert end-users to evaluate a wide variety of compound events, future conditions, and adaptation options in minutes.  FloodAdapt serves as a connector between scientific advances and practitioner needs, improving and increasing the uptake and impact of adaptation research and development.

To make decisions on flood adaptation, communities need to understand how climate and socio-economic changes will affect flood risk and the risk-reduction potential of various adaptation options. This type of information is usually costly to acquire, and models are often too slow and labor-intensive to evaluate all the scenarios required to understand the impacts and effectiveness of potential adaptation decisions. FloodAdapt addresses this by making rapid, physics-based compound flood modeling and detailed impact modeling accessible to non-expert end-users, allowing them to evaluate a wide variety of compound events, future conditions, and adaptation options in minutes.

FloodAdapt was developed as a rapid planning tool with a straightforward graphical user interface for scenario generation, simulation, and visualization of spatial flooding and flooding impacts. Decision-making needs at the community level were central to the design of FloodAdapt. Users can answer planning questions like: “How will potential adaptation options reduce flood impacts?”, “How will those options perform for different types of events, like hurricanes, king tides, or heavy rainfall?”, “Which neighborhoods will benefit most?”, “How will those options hold up in the future?”

Users specify what-if scenarios composed of historic or synthetic weather events, climate or socio-economic future projections, and adaptation measures.
The backend of FloodAdapt leverages the open-source, state-of-the-art process-based compound flood model SFINCS (https://github.com/Deltares/SFINCS) that can accurately predict compound flooding due to surge, rainfall, and river discharge, at a fraction of the computation time typically required by physics-based models. The damage model included in FloodAdapt is the Deltares-developed flood impact assessment tool Delft-FIAT (https://github.com/Deltares/Delft-FIAT). It calculates the flood damages to individual buildings and roads, and – when social vulnerability data is available – aggregates these damages over vulnerability classes.

FloodAdapt can greatly support adaptation planning by allowing users to explore many scenarios. It can be used to evaluate flooding and impacts due to compound weather events, like hurricanes, king tides, and rainfall events. Users can evaluate flooding, impacts, and risk considering user-specified projections of sea level rise, precipitation increase, storm frequency increase, population growth, and economic growth. Users can also test out adaptation options, like sea walls, levees, pumps, home elevations, buyouts and floodproofing.

Recent developments of the decision-support system include (1) simplifying and partially automating the setup of the SFINCS and Delft-FIAT models, (2) improving the user experience, (3) better supporting adaptation planning with improvements like metrics tables, infographics, better visualizations in the user interface, adding in additional adaptation options to evaluate, and calculating benefits of adaptation options, and (4) incorporating social vulnerability and equity into the evaluation of adaptation options to support equitable adaptation planning.

FloodAdapt is currently in an intensive development stage. Independent usage of the repository will be challenging prior to end-of-year 2024. FloodAdapt documentation will be expanded on throughout 2024.

## Setting up conda

In order to develop the FloodAdapt-GUI locally, please follow the following steps:

- Download and install [mambaforge](https://mamba.readthedocs.io/en/latest/installation.html#fresh-install).

- Depending on your company settings, you might also have to run the following in a Powershell terminal as administrator:

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

## Installation

Before starting the installation process, make sure you have access to all required private repositories by ensuring you are in the Teams `FloodAdaptUsers` in the [Deltares](https://github.com/orgs/Deltares/teams/floodadaptusers) and [Deltares-research](https://github.com/orgs/Deltares-research/teams/floodadaptusers) organizations.

To run FloodAdapt, GeoPandas needs to be installed. GeoPandas depends for its spatial functionality on a large geospatial, open source stack of libraries (GEOS, GDAL, PROJ). These base C libraries can sometimes be a challenge to install.

Pre built binaries are provided in `environment/geospatial-wheels`, and are installed using `environment/make_environment.py`. They can be manually installed into your environment using: `pip install <wheel_path>`. All other dependencies can be either found on pip (https://pypi.org/) or have pyproj.toml files to use during installation.

## Creating the environment

The environment for running and developing FloodAdapt can be made with the script: `make_environment.py`.

Create a virtual environment named `ENV_NAME` with the core dependencies of FloodAdapt by running the following in a terminal:

```bash
python make_environment.py -n ENV_NAME
```

Additional installation options that can be added to the end of the command:

`-n ENV_NAME` or `--name ENV_NAME`
- The name for the environment to be created. If it already exists, it will be removed and recreated from scratch.

`-p PREFIX` or `--prefix PREFIX`
- Creates the environment at `prefix/name` instead of the default conda location.

`-d GROUP` or `--dev GROUP`
- Install optional dependencies of FloodAdapt-GUI and FloodAdapt in addition the core ones. GROUP: dev | build | all

`-e` or `--editable`
- Do an editable install of the FloodAdapt-GUI and FloodAdapt packages.

## Updating the environment
To update your current environment, run the following commands:
```bash
conda activate ENV_NAME

cd FloodAdapt

python -m pip install -e . --upgrade
```
Note:  Update all packages and their dependencies to the latest available versions allowed by requirements defined in pyproject.toml files. This also performs the update for the backend dependencies, but deactivates the editable installation and installs everything as a package.

## Configure database

FloodAdapt uses a database to store, handle and organize input files, output files and static data. This database needs to be configured the first time you want to use FloodAdapt. Which is done via `flood_adapt/config.py` which contains the Settings class to set and validate environment variables, specific to your system.

To initialize floodadapt and configure the database, add the following lines to the top of your script / initialize function to validate and set the environment variables:
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
    database_root=root,
    database_name=name,
    system_folder=system_folder,
)
```

## Developing FloodAdapt

Clone the repository

```bash
git clone https://github.com/Deltares/FloodAdapt
```

Create a developer environment `example_name`, with an editable installation FloodAdapt core and the `dev` optional dependency group .

```bash
python make_environment.py -n example_name --editable --dev dev
```

For more guidelines on contributing to FloodAdapt please see `CONTRIBUTING.md`

### Optional Dependencies
Different groups of packages are required for various tasks that are not required to run the application. The optional dependency groups for FloodAdapt are:
- `dev` - linting, pre-commit hooks & testing
- `build` - distribution related packages & publishing to pip
- `docs` - generating documentation & example notebooks
- `all` - all of the above

An optional dependency group can be installed in addition to installing the core using `pip install .[group_name]`, where '.' can be replaced by a directory path that contains a pyproject.toml file.

### Generating the documentation

We use `quartodoc` to generate our API documentation automatically. If you have the `docs` optional dependency group installed.
you can do this by running `quartodoc build` from the `docs` directory, and it will create the documentation for you.
After this is done, if you wish, you can build and view the documentation locally by running `quarto preview` from the `docs` directory
### Setup Visual Studio Code (optional)

1. Initialize pre-commit to run locally before you commit by running the following command:
```
pre-commit install
```

2. Add the following to your `.vscode/settings.json` file in your workspace

```json
{
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": true
        }
    },
    "python.formatting.provider": "black",
    "autoDocstring.docstringFormat": "numpy"
}
```
