# FloodAdapt
(previously known as CFRSS)

A software package Support System which can be used to assess the benefits and costs of Flood Resilience measures in a Community. 
It uses SFINCS (Super-Fast INundation of CoastS) and FIAT-Objects in the background.



# Contributing


## Setting up conda

In order to develop on `flood_adapt` locally, please follow the following steps:

- Download and install [miniconda](https://docs.conda.io/en/latest/miniconda.html).

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
conda env create --file=environment.yml --force
```

- Installing hydromt

```
pip install git+https://github.com/Deltares/hydromt.git@85e7795a9f1972fe4e2a8bf7dd2d941193008574
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
