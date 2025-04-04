from typing import Any, Union

import geopandas as gpd
import pandas as pd

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.benefit_runner import Benefit


def get_benefits() -> dict[str, Any]:
    """Get all benefits from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all benefits.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
        Each value is a list of the corresponding attribute for each benefit.
    """
    # sorting and filtering either with PyQt table or in the API
    return Database().benefits.list_objects()


def get_benefit(name: str) -> Benefit:
    """Get a benefit from the database by name.

    Parameters
    ----------
    name : str
        The name of the benefit to retrieve.

    Returns
    -------
    Benefit
        The benefit object with the given name. See [Benefit](/api_ref/) for details.

    Raises
    ------
    ValueError
        If the benefit with the given name does not exist.
    """
    return Database().benefits.get(name)


def create_benefit(attrs: dict[str, Any]) -> Benefit:
    """Create a new benefit object.

    Parameters
    ----------
    attrs : dict[str, Any]
        The attributes of the benefit object to create. Should adhere to the Benefit schema.
    """
    return Benefit(**attrs)


def save_benefit(benefit: Benefit) -> None:
    """Save a benefit object to the database.

    Parameters
    ----------
    benefit : Benefit
        The benefit object to save.

    Raises
    ------
    ValueError
        If the benefit object is not valid.
    """
    Database().benefits.save(benefit)


def edit_benefit(benefit: Benefit) -> None:
    """Edit a benefit object in the database.

    Parameters
    ----------
    benefit : Benefit
        The benefit object to edit.

    Raises
    ------
    ValueError
        If the benefit object does not exist.
    """
    Database().benefits.edit(benefit)


def delete_benefit(name: str) -> None:
    """Delete a benefit object from the database.

    Parameters
    ----------
    name : str
        The name of the benefit object to delete.

    Raises
    ------
    ValueError
        If the benefit object does not exist.
    """
    Database().benefits.delete(name)


def check_benefit_scenarios(benefit: Benefit) -> pd.DataFrame:
    """Return a dataframe with the scenarios needed for this benefit assessment run.

    Parameters
    ----------
    benefit : Benefit
        The benefit object to check.

    Returns
    -------
    pd.DataFrame
        A dataframe with the scenarios needed for this benefit assessment run.
    """
    return Database().check_benefit_scenarios(benefit)


def create_benefit_scenarios(benefit: Benefit):
    """Create the benefit scenarios.

    Parameters
    ----------
    benefit : Benefit
        The benefit object to create scenarios for.
    """
    Database().create_benefit_scenarios(benefit)


def run_benefit(name: Union[str, list[str]]) -> None:
    """Run the benefit assessment.

    Parameters
    ----------
    name : Union[str, list[str]]
        The name of the benefit object to run.
    """
    Database().run_benefit(name)


def get_aggregation_benefits(name: str) -> dict[str, gpd.GeoDataFrame]:
    """Get the aggregation benefits for a benefit assessment.

    Parameters
    ----------
    name : str
        The name of the benefit assessment.

    Returns
    -------
    gpd.GeoDataFrame
        The aggregation benefits for the benefit assessment.
    """
    return Database().get_aggregation_benefits(name)
