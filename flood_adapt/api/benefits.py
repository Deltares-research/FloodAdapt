from typing import Any, Union

import geopandas as gpd
import pandas as pd

import flood_adapt.dbs_classes.database as db
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit


def get_benefits() -> dict[str, Any]:
    # sorting and filtering either with PyQt table or in the API
    return db.Database().benefits.list_objects()


def get_benefit(name: str) -> IBenefit:
    return db.Database().benefits.get(name)


def create_benefit(attrs: dict[str, Any]) -> IBenefit:
    return Benefit.load_dict(attrs, db.Database().input_path)


def save_benefit(benefit: IBenefit) -> None:
    db.Database().benefits.save(benefit)


def edit_benefit(benefit: IBenefit) -> None:
    db.Database().benefits.edit(benefit)


def delete_benefit(name: str) -> None:
    db.Database().benefits.delete(name)


def check_benefit_scenarios(benefit: IBenefit) -> pd.DataFrame:
    return db.Database().check_benefit_scenarios(benefit)


def create_benefit_scenarios(benefit: IBenefit):
    db.Database().create_benefit_scenarios(benefit)


def run_benefit(name: Union[str, list[str]]) -> None:
    db.Database().run_benefit(name)


def get_aggregation_benefits(name: str) -> dict[gpd.GeoDataFrame]:
    return db.Database().get_aggregation_benefits(name)
