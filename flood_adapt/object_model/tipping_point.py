import os
import shutil
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import numpy as np
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from fiat_toolbox.metrics_writer.fiat_read_metrics_file import MetricsFileReader

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.interface.tipping_points import (
    TippingPointModel,
    ITipPoint,
    TippingPointStatus,
)
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.api.static import read_database

"""
This script implements a Tipping Point model to analyze the impact of sea level rise (SLR)
on metrics such as population exposure, economic losses, etc.
The model simulates scenarios based on varying SLR projections (for now) to identify tipping points 
where a metric exceeds a predefined threshold.

Core Functionalities:
- Creates projections for different SLR values.
- Iteratively runs simulations to determine tipping points for specified metrics.
- Saves results and tipping point data in a structured format for analysis.

Inputs:
- List of sea level rise values specifying different scenario projections.
- Dictionary detailing the tipping point conditions including metric name, value, unit, and type.

Outputs:
- Results for each scenario indicating if a tipping point is reached.
- Compiled results are saved as CSV files.
"""


class TippingPoint(ITipPoint):
    """Class holding all information related to tipping points analysis"""

    def __init__(self):
        """Initiation function when object is created through file or dict options"""
        self.database_input_path = Database().input_path
        self.site_toml_path = Path(Database().static_path) / "site" / "site.toml"
        self.results_path = Database().output_path / "scenarios"

    def create_tp_obj(self):
        # Save tipping point object to the tipping_points folder and a toml file
        if not (Database().input_path / "tipping_points" / self.attrs.name).exists():
            (Database().input_path / "tipping_points" / self.attrs.name).mkdir(
                parents=True
            )
        self.save(
            Database().input_path
            / "tipping_points"
            / self.attrs.name
            / f"{self.attrs.name}.toml"
        )
        return self

    def slr_projections(self, slr):
        """Create projections for sea level rise value"""
        new_projection_name = self.attrs.projection + "_slr" + str(slr).replace(".", "")
        proj = database.projections.get(self.attrs.projection)
        proj.attrs.physical_projection.sea_level_rise = UnitfulLength(
            value=slr, units=UnitTypesLength.meters
        )
        proj.save(
            Database().input_path
            / "projections"
            / new_projection_name
            / (new_projection_name + ".toml")
        )
        return self

    def create_tp_scenarios(self):
        """Create scenarios for each sea level rise value inside the tipping_point folder"""
        self.create_tp_obj()
        # self.check_scenarios()
        # self.has_run = self.has_run_check()
        # create projections based on SLR values
        for i, slr in enumerate(self.attrs.sealevelrise):
            self.slr_projections(slr)
            self.attrs.sealevelrise[i] = str(slr).replace(".", "")

        # crete scenarios for each SLR value
        scenarios = {
            f"slr_{slr}": {
                "name": f"slr_{slr}",
                "event": self.attrs.event_set,
                "projection": f"{self.attrs.projection}_slr{slr}",
                "strategy": self.attrs.strategy,
            }
            for slr in self.attrs.sealevelrise
        }
        self.scenarios_dict = scenarios

        # create subdirectories for each scenario and .toml files
        for scenario in scenarios.keys():
            if not (
                Database().input_path
                / "tipping_points"
                / self.attrs.name
                / "scenarios"
                / scenario
            ).exists():
                (
                    Database().input_path
                    / "tipping_points"
                    / self.attrs.name
                    / "scenarios"
                    / scenario
                ).mkdir(parents=True)

            scenario_obj = Scenario.load_dict(
                scenarios[scenario], Database().input_path
            )
            scenario_obj.save(
                Database().input_path
                / "tipping_points"
                / self.attrs.name
                / "scenarios"
                / scenario
                / f"{scenario}.toml"
            )

    def run_tp_scenarios(self):
        """Run all scenarios to determine tipping points, but first check if some scenarios are already run from the output folder"""
        for scenario in self.scenarios_dict.keys():
            scenario_obj = Scenario.load_dict(
                self.scenarios_dict[scenario], Database().input_path
            )
            # check if scenario already exists in the database, if yes skip the run and copy results
            if not self.check_scenarios(scenario_obj):
                # run scenario but there's also a check inside the function in case the scenario has already been run
                scenario_obj.run()

            # if the status is reached, save the SLR and the metric value
            if self.check_tipping_point(scenario_obj):
                self.attrs.status = TippingPointStatus.reached
                self.scenarios_dict[scenario]["tipping point reached"] = "Yes"
                break
            else:
                self.attrs.status = TippingPointStatus.not_reached
                self.scenarios_dict[scenario]["tipping point reached"] = "No"

        # Save results - make directory if it doesn't exist
        if not self.results_path.is_dir():
            self.results_path.mkdir(parents=True)

        tp_path = self.results_path.joinpath(
            f"tipping_point_results_{self.attrs.name}.csv"
        )
        tp_results = pd.DataFrame.from_dict(
            self.scenarios_dict, orient="index"
        ).reset_index(drop=True)
        tp_results.to_csv(tp_path)

    def check_tipping_point(self, scenario: Scenario):
        """Load results and check if the tipping point is reached"""
        # already optimised for multiple metrics
        info_df = pd.read_csv(
            scenario.direct_impacts.results_path.joinpath(
                f"Infometrics_{scenario.direct_impacts.name}.csv"
            ),
            index_col=0,
        )
        # if any tipping point is reached, return True
        return any(
            self.evaluate_tipping_point(
                info_df.loc[metric[0], "Value"],
                metric[1],
                metric[2],
            )
            for metric in self.attrs.tipping_point_metric
        )

    def evaluate_tipping_point(self, current_value, threshold, operator):
        """Compare current value with threshold for tipping point"""
        operations = {"greater": lambda x, y: x >= y, "less": lambda x, y: x <= y}
        return operations[operator](current_value, threshold)

    def check_scenarios(self, scenario_obj):
        # check if the current scenario in the tipping point object already exists in the database
        for db_scenario in Database().scenarios.list_objects()["name"]:
            if scenario_obj.__eq__(Database().scenarios.get(db_scenario)):
                # check if the scenario has been run
                if scenario_obj.init_object_model().direct_impacts.has_run:
                    # copy the output files from db_scenario to the output folder
                    shutil.copytree(
                        Database().scenarios.get(db_scenario).results_path,
                        scenario_obj.results_path,
                    )
                    return True
        return False

    # standard functions
    def load_file(
        filepath: Union[str, Path], database_input_path: Union[str, os.PathLike]
    ) -> "TippingPoint":
        """create risk event from toml file"""

        obj = TippingPoint(database_input_path)
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = TippingPointModel.model_validate(toml)
        return obj

    def load_dict(dct: Union[str, Path]) -> "TippingPoint":
        """create risk event from toml file"""

        obj = TippingPoint()
        obj.attrs = TippingPointModel.model_validate(dct)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Scenario to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    def __eq__(self, other):
        if not isinstance(other, TippingPoint):
            # don't attempt to compare against unrelated types
            raise NotImplementedError
        attrs_1, attrs_2 = self.attrs.model_copy(), other.attrs.model_copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2


# TODO: expand test into a separate file
# test function
from flood_adapt.config import set_system_folder

if __name__ == "__main__":
    database = read_database(
        rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database",
        "charleston_full",
    )
    set_system_folder(
        rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database\\system"
    )

    tp_dict = {
        "name": "tipping_point_test",
        "description": "",
        "event_set": "extreme12ft",
        "strategy": "no_measures",
        "projection": "current",
        "sealevelrise": [0.5, 1.0, 1.5],
        "tipping_point_metric": [
            ("FloodedAll", 34195.0, "greater"),
            ("FullyFloodedRoads", 2000, "greater"),
        ],
    }
    # load
    test_point = TippingPoint.load_dict(tp_dict)
    # create scenarios for tipping points
    test_point.create_tp_scenarios()
    # run all scenarios
    test_point.run_tp_scenarios()


# TODO: post processing stuff still to be done
# make html & plots
# write to file
