# FloodAdapt
(previously known as CFRSS)

A software package Support System which can be used to assess the benefits and costs of Flood Resilience measures in a Community. 
It uses SFINCS (Super-Fast INundation of CoastS) and FIAT-Objects in the background.



# Contributing


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

- Create the environment by executing the following in your terminal:

```
conda create -n flood_adapt python=3.10
```

- Activate the environment

```
conda activate flood_adapt
```

In order to develop on `flood_adapt` locally, execute the following line inside your virtual environment

```bash
pip install -e ".[tests,lint]"
```

To run the tests execute:

```bash
pytest tests
```
