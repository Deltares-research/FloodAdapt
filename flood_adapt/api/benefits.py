import inspect
import types
from typing import Any, Union

import geopandas as gpd
import pandas as pd

from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.database import IDatabase


def get_benefits(database: IDatabase) -> dict[str, Any]:
    """Returns a dictionary with info on the benefits that currently
    exist in the database.

    Parameters
    ----------
    database : IDatabase
        Database object

    Returns
    -------
    dict[str, Any]
        Dictionary with info on the benefits
    """
    return database.benefits.list_objects()


def get_benefit(name: str, database: IDatabase) -> IBenefit:
    """Returns the benefit object with the specified name from the database

    Parameters
    ----------
    name : str
        name of the object to be returned
    database : IDatabase
        database object

    Returns
    -------
    IBenefit
        The benefit object with the specified name
    """
    return database.benefits.get(name)


def create_benefit(attrs: dict[str, Any], database: IDatabase) -> IBenefit:
    return Benefit.load_dict(attrs, database.input_path)


def save_benefit(benefit: IBenefit, database: IDatabase) -> None:
    """Save the benefit to the database.

    Parameters
    ----------
    benefit : IBenefit
        The benefit to save.
    database : IDatabase
        The database to save the benefit to.

    Raises
    ------
    ValueError
        Raise error if name is already in use.
    """
    database.benefits.save(benefit)


def edit_benefit(benefit: IBenefit, database: IDatabase) -> None:
    database.benefits.edit(benefit)


def delete_benefit(name: str, database: IDatabase) -> None:
    database.benefits.delete(name)


def check_benefit_scenarios(benefit: IBenefit, database: IDatabase) -> pd.DataFrame:
    return database.check_benefit_scenarios(benefit)


def create_benefit_scenarios(benefit: IBenefit, database: IDatabase):
    database.create_benefit_scenarios(benefit)


def run_benefit(name: Union[str, list[str]], database: IDatabase) -> None:
    database.run_benefit(name)


def get_aggregation_benefits(name: str, database: IDatabase) -> dict[gpd.GeoDataFrame]:
    return database.get_aggregation_benefits(name)


# Get a list of all public functions defined in this module
__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or isinstance(obj, types.FunctionType))
    and not name.startswith("_")
]

# Append 'IMeasure' to the list
__all__.append("IBenefit")
