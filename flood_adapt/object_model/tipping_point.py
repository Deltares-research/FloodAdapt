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

from flood_adapt.object_model.interface.tipping_points import (
    TipPointModel,
    ITipPoint,
    TippingPointStatus,
)
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.api.startup import read_database

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

    attrs: TipPointModel
    database_input_path: Union[str, os.PathLike]

    def __init__(self, database_input_path: Union[str, os.PathLike]):
        """Initiation function when object is created through file or dict options"""
        self.database_input_path = Path(database_input_path)
        self.site_toml_path = (
            Path(database_input_path).parent / "static" / "site" / "site.toml"
        )

    def init_object_model(self):
        """Create input and output folders for the tipping point"""

        self.results_path = Path(self.database_input_path).parent.joinpath(
            "output", "Scenarios", self.attrs.name
        )

        # create an input baseline folder for the scenarios
        if not (self.database_input_path / "scenarios" / self.attrs.name).exists():
            (self.database_input_path / "scenarios" / self.attrs.name).mkdir()
        self.save(
            self.database_input_path
            / "scenarios"
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
            self.database_input_path
            / "projections"
            / new_projection_name
            / (new_projection_name + ".toml")
        )
        return self

    def create_tp_scenarios(self):
        """Create scenarios for each sea level rise value"""
        self.init_object_model()
        # TODO: commenting out because now we are creating all scenarios, check it later to see how we deal with redundant scenarios
        # self.check_scenarios()
        # self.has_run = self.has_run_check()
        # create projections based on SLR values
        for slr in self.attrs.sealevelrise:
            self.slr_projections(slr)

        # crete scenarios for each SLR value
        scenarios = {
            f"slr_"
            + str(slr).replace(".", ""): {
                "name": f"slr_" + str(slr).replace(".", ""),
                "event": self.attrs.event_set,
                # get a string from slr removing the dot
                "projection": self.attrs.projection
                + "_slr"
                + str(slr).replace(".", ""),
                "strategy": self.attrs.strategy,
            }
            for slr in self.attrs.sealevelrise
        }
        self.scenarios_dict = scenarios

        # create subdirectories for each scenario and .toml files
        for scenario in scenarios.keys():
            if not (
                self.database_input_path / "scenarios" / self.attrs.name / scenario
            ).exists():
                (
                    self.database_input_path / "scenarios" / self.attrs.name / scenario
                ).mkdir()

            scenario_obj = Scenario.load_dict(
                scenarios[scenario], self.database_input_path
            )
            scenario_obj.save(
                self.database_input_path
                / "scenarios"
                / self.attrs.name
                / scenario
                / f"{scenario}.toml"
            )

    def run_tp_scenarios(self):
        """Run all scenarios to determine tipping points"""
        for scenario in self.scenarios_dict.keys():
            scenario_obj = Scenario.load_dict(
                self.scenarios_dict[scenario], self.database_input_path
            )
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
        impact_metrics = {
            key: info_df.loc[key, "Value"]
            for key in self.attrs.tipping_point_metric.keys()
        }
        return self.evaluate_tipping_point(impact_metrics)

    def evaluate_tipping_point(self, impact_metrics):
        """Compare tipping points and stops when one tipping point is reached"""
        # already optimised for multiple metrics
        if self.attrs.operator == "greater":
            return any(
                [
                    impact_metrics[key] > value
                    for key, value in self.attrs.tipping_point_metric.items()
                ]
            )
        elif self.attrs.operator == "less":
            return any(
                [
                    impact_metrics[key] < value
                    for key, value in self.attrs.tipping_point_metric.items()
                ]
            )

    # FUNCTIONS THAT ARE STILL NOT IMPLEMENTED - from benefits
    def has_run_check(self):
        """Check if the tipping point analysis has already been run"""
        results_toml = self.results_path.joinpath("results.toml")
        results_csv = self.results_path.joinpath("results.csv")
        results_html = self.results_path.joinpath("results.html")
        # TODO: check this

        check = all(results_toml.exists() for result in [results_toml, results_csv])
        if check:
            with open(results_toml, "rb") as fp:
                self.results = tomli.load(fp)

    def check_scenarios(self):
        """Check which scenarios are needed for this tipping point calculation
        and if they have already been created"""
        # calculating scenarios per slr level
        scenarios_calc = {
            f"slr_{slr}": {
                "name": f"slr_{slr}",
                "event": self.attrs.event_set,
                "projection": self.attrs.projection,
                "strategy": self.attrs.strategy,
                "sealevelrise": slr,
                "tipping_point_metric": self.attrs.tipping_point_metric,
            }
            for slr in self.attrs.sealevelrise
        }

        scenarios_avail = []
        for scenario_path in list(
            self.database_input_path.joinpath("scenarios").glob("*")
        ):
            scenarios_avail.append(
                Scenario.load_file(scenario_path.joinpath(f"{scenario_path.name}.toml"))
            )

        # Check if any of the needed scenarios are already there
        for scenario in scenarios_calc.keys():
            scn_dict = scenarios_calc[scenario].copy()
            scn_dict["name"] = scenario
            scenario_obj = Scenario.load_dict(scn_dict, self.database_input_path)
            created = [
                scn_avl for scn_avl in scenarios_avail if scenario_obj == scn_avl
            ]
            if len(created) > 0:
                scenarios_calc[scenario]["scenario created"] = created[0].attrs.name
                if created[0].init_object_model().direct_impacts.has_run:
                    scenarios_calc[scenario]["scenario run"] = True
                else:
                    scenarios_calc[scenario]["scenario run"] = False
            else:
                scenarios_calc[scenario]["scenario created"] = "No"
                scenarios_calc[scenario]["scenario run"] = False

        df = pd.DataFrame(scenarios_calc).T
        self.scenarios = df.astype(
            dtype={
                "event": "str",
                "projection": "str",
                "strategy": "str",
                "scenario created": "str",
                "scenario run": bool,
            }
        )
        return self.scenarios

    # standard functions
    def load_file(
        filepath: Union[str, Path], database_input_path: Union[str, os.PathLike]
    ) -> "TippingPoint":
        """create risk event from toml file"""

        obj = TippingPoint(database_input_path)
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = TipPointModel.model_validate(toml)
        return obj

    def load_dict(
        dct: Union[str, Path], database_input_path: Union[str, os.PathLike]
    ) -> "TippingPoint":
        """create risk event from toml file"""

        obj = TippingPoint(database_input_path)
        obj.attrs = TipPointModel.model_validate(dct)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Scenario to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

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
        "tipping_point_metric": {"FloodedAll": 34195.0, "FullyFloodedRoads": 200},
        "operator": "greater",
    }
    # load
    test_point = TippingPoint.load_dict(tp_dict, database.input_path)
    # create scenarios for tipping points
    test_point.create_tp_scenarios()
    # run all scenarios
    test_point.run_tp_scenarios()


# TODO: post processing stuff still to be done
# make html & plots
# write to file
