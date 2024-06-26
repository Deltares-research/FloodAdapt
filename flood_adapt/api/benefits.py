from typing import Any, Union

import geopandas as gpd
import pandas as pd

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit


def get_benefits() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return Database().benefits.list_objects()


def get_benefit(name: str) -> IBenefit:
    return Database().benefits.get(name)


def create_benefit(attrs: dict[str, Any]) -> IBenefit:
    return Benefit.load_dict(attrs, Database().input_path)


def save_benefit(benefit: IBenefit) -> None:
    Database().benefits.save(benefit)


def edit_benefit(benefit: IBenefit) -> None:
    Database().benefits.edit(benefit)


def delete_benefit(name: str) -> None:
    Database().benefits.delete(name)


def check_benefit_scenarios(benefit: IBenefit) -> pd.DataFrame:
    return Database().check_benefit_scenarios(benefit)


def create_benefit_scenarios(benefit: IBenefit):
    Database().create_benefit_scenarios(benefit)


def run_benefit(name: Union[str, list[str]]) -> None:
    Database().run_benefit(name)


def get_aggregation_benefits(name: str) -> dict[gpd.GeoDataFrame]:
    return Database().get_aggregation_benefits(name)
