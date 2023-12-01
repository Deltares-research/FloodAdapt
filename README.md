# FloodAdapt
FloodAdapt is a decision-support tool that seeks to advance and accelerate flooding-related adaptation planning. It brings rapid, physics-based compound flood and detailed impact modelling into an easy-to-use system, allowing non-expert end-users to evaluate a wide variety of compound events, future conditions, and adaptation options in minutes.  FloodAdapt serves as a connector between scientific advances and practitioner needs, improving and increasing the uptake and impact of adaptation research and development.

To make decisions on flood adaptation, communities need to understand how climate and socio-economic changes will affect flood risk and the risk-reduction potential of various adaptation options. This type of information is usually costly to acquire, and models are often too slow and labor-intensive to evaluate all the scenarios required to understand the impacts and effectiveness of potential adaptation decisions. FloodAdapt addresses this by making rapid, physics-based compound flood modeling and detailed impact modeling accessible to non-expert end-users, allowing them to evaluate a wide variety of compound events, future conditions, and adaptation options in minutes.  

FloodAdapt was developed as a rapid planning tool with a straightforward graphical user interface for scenario generation, simulation, and visualization of spatial flooding and flooding impacts. Decision-making needs at the community level were central to the design of FloodAdapt. Users can answer planning questions like: “How will potential adaptation options reduce flood impacts?”, “How will those options perform for different types of events, like hurricanes, king tides, or heavy rainfall?”, “Which neighborhoods will benefit most?”, “How will those options hold up in the future?”

Users specify what-if scenarios composed of historic or synthetic weather events, climate or socio-economic future projections, and adaptation measures. 
The backend of FloodAdapt leverages the open-source, state-of-the-art process-based compound flood model SFINCS (https://github.com/Deltares/SFINCS) that can accurately predict compound flooding due to surge, rainfall, and river discharge, at a fraction of the computation time typically required by physics-based models. The damage model included in FloodAdapt is the Deltares-developed flood impact assessment tool Delft-FIAT (https://github.com/Deltares/Delft-FIAT). It calculates the flood damages to individual buildings and roads, and – when social vulnerability data is available – aggregates these damages over vulnerability classes.

FloodAdapt can greatly support adaptation planning by allowing users to explore many scenarios. It can be used to evaluate flooding and impacts due to compound weather events, like hurricanes, king tides, and rainfall events. Users can evaluate flooding, impacts, and risk considering user-specified projections of sea level rise, precipitation increase, storm frequency increase, population growth, and economic growth. Users can also test out adaptation options, like sea walls, levees, pumps, home elevations, buyouts and floodproofing. 

Recent developments of the decision-support system include (1) simplifying and partially automating the setup of the SFINCS and Delft-FIAT models, (2) improving the user experience, (3) better supporting adaptation planning with improvements like metrics tables, infographics, better visualizations in the user interface, adding in additional adaptation options to evaluate, and calculating benefits of adaptation options, and (4) incorporating social vulnerability and equity into the evaluation of adaptation options to support equitable adaptation planning.

FloodAdapt is currently in an intensive development stage. Independent usage of the repository will be challenging prior to end-of-year 2024. FloodAdapt documentation will be expanded on throughout 2024.  

# Contributing


## Setting up conda

In order to develop on `flood_adapt` locally, please follow the following steps:

- Download and install [mambaforge](https://mamba.readthedocs.io/en/latest/installation.html#fresh-install).

- Initialize `conda` by running the following in the `Miniconda prompt`:

```
conda init
```

- Depending on your company settings, you might also have to run the following in a Powershell terminal as administrator:

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

## Creating (or updating) the environment

- Create (or update) the environment by executing the following in your terminal:

```
mamba env create --file=environment.yml --force
```

## Installing FloodAdapt

- Activate the environment

```
conda activate flood_adapt
```

In order to develop on `flood_adapt` locally, execute the following line inside your virtual environment

```bash
pip install -e .
```

## Installing pre-commit (For developers)
Hook scripts are useful for identifying simple issues before submission to code review.
Precommit runs automatically on every commit point out issues in code such as missing semicolons, trailing whitespace, and debug statements. By pointing these issues out before code review, allows a code reviewer to focus on the architecture of a change while not wasting time with trivial style nitpicks. Install the git hook scripts with:

```bash
pre-commit install
```

Running this commands for the first time may take a minute or two, since the hook scripts need to be fetched and installed.
This scripts are cached, and now pre-commit will run automatically on every ```git commit```.
## Running the tests


If no already done, activate the environment

```
conda activate flood_adapt
```


To run the tests execute:

```bash
pytest tests
```

## Setup Visual Studio Code (optional)

1. Install the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python), [ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) and [autoDocstring](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring) extensions.

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
