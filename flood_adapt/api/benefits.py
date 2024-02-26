from typing import Any, Union

import geopandas as gpd
import pandas as pd

from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.database import IDatabase


def get_benefits(database: IDatabase) -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return database.get_benefits()


def get_benefit(name: str, database: IDatabase) -> IBenefit:
    return database.get_benefit(name)


def create_benefit(attrs: dict[str, Any], database: IDatabase) -> IBenefit:
    return Benefit.load_dict(attrs, database.input_path)


def save_benefit(benefit: IBenefit, database: IDatabase) -> None:
    database.save_benefit(benefit)


def edit_benefit(benefit: IBenefit, database: IDatabase) -> None:
    database.edit_benefit(benefit)


def delete_benefit(name: str, database: IDatabase) -> None:
    database.delete_benefit(name)


def check_benefit_scenarios(benefit: IBenefit, database: IDatabase) -> pd.DataFrame:
    return database.check_benefit_scenarios(benefit)


def create_benefit_scenarios(benefit: IBenefit, database: IDatabase):
    database.create_benefit_scenarios(benefit)


def run_benefit(name: Union[str, list[str]], database: IDatabase) -> None:
    database.run_benefit(name)


def get_aggregation_benefits(name: str, database: IDatabase) -> dict[gpd.GeoDataFrame]:
    return database.get_aggregation_benefits(name)
