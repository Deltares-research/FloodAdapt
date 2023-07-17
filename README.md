# FloodAdapt
(previously known as CFRSS)

A software package Support System which can be used to assess the benefits and costs of Flood Resilience measures in a Community.
It uses SFINCS (Super-Fast INundation of CoastS) and FIAT-Objects in the background.



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
Precommit runs automatically on every commit point out issues in code such as missing semicolons, trailing whitespace, and debug statements. By pointing these issues out before code review, allows a code reviewer to focus on the architecture of a change while not wasting time with trivial style nitpicks.

```pre-commit install
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
