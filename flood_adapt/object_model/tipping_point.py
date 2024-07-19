import os
from pathlib import Path
from typing import Union

import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from scipy.interpolate import interp1d

from flood_adapt.api.static import read_database
from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.interface.tipping_points import (
    ITipPoint,
    TippingPointModel,
    TippingPointStatus,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.scenario import Scenario

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
    """Class holding all information related to tipping points analysis."""

    def __init__(self):
        """Initiate function when object is created through file or dict options."""
        self.site_toml_path = Path(Database().static_path) / "site" / "site.toml"
        self.results_path = Database().output_path / "tipping_points"
        self.scenarios = {}

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
        """Create projections for sea level rise value."""
        new_projection_name = self.attrs.projection + "_slr" + str(slr).replace(".", "")
        proj = Database().projections.get(self.attrs.projection)
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

    def check_scenarios_exist(self, scenario_obj):
        db_list = []
        # check if the current scenario in the tipping point object already exists in the database
        for db_scenario in Database().scenarios.list_objects()["objects"]:
            if scenario_obj == db_scenario:
                db_list.append(db_scenario.attrs.name)
        return db_list

    def create_tp_scenarios(self):
        """Create scenarios for each sea level rise value inside the tipping_point folder."""
        self.create_tp_obj()
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

        # create subdirectories for each scenario and .toml files
        for scenario in scenarios.keys():

            scenario_obj = Scenario.load_dict(
                scenarios[scenario], Database().input_path
            )
            scen_exists = self.check_scenarios_exist(scenario_obj)

            if scen_exists:
                # make a dict with name and object
                self.scenarios[scen_exists[0]] = {
                    "name": scen_exists[0],
                    "object": scenario_obj,
                }
            else:
                Database().scenarios.save(scenario_obj)
                self.scenarios[scenario_obj.attrs.name] = {
                    "name": scenario_obj.attrs.name,
                    "object": scenario_obj,
                }

        self.attrs.scenarios = list(self.scenarios.keys())
        self.save(
            filepath=Database().input_path
            / "tipping_points"
            / self.attrs.name
            / f"{self.attrs.name}.toml"
        )  # for later when we have a database_tp: TODO: Database().tipping_points.save(self)

    def run_tp_scenarios(self):
        """Run all scenarios to determine tipping points."""
        for name, scenario in self.scenarios.items():
            scenario_obj = scenario["object"]
            # commented out to run every scenario - TODO: uncomment if you want to skip scenarios once
            # if self.attrs.status == TippingPointStatus.reached:
            #     self.scenarios[name]["tipping point reached"] = True
            #     continue

            if not self.scenario_has_run(scenario_obj):
                scenario_obj.run()

            # Check the tipping point status
            if self.check_tipping_point(scenario_obj):
                self.attrs.status = TippingPointStatus.reached
                self.scenarios[name]["tipping point reached"] = True
            else:
                self.scenarios[name]["tipping point reached"] = False

        # prepare the csv file for the pathway generator
        self.prepare_tp_results()

    def scenario_has_run(self, scenario_obj):
        # TODO: once has_run is refactored (external) we change below to make it more direct
        for db_scenario, finished in zip(
            Database().scenarios.list_objects()["objects"],
            Database().scenarios.list_objects()["finished"],
        ):
            if scenario_obj == db_scenario and finished:
                return True
        return False

    def check_tipping_point(self, scenario: Scenario):
        """Load results and check if the tipping point is reached."""
        info_df = pd.read_csv(
            scenario.init_object_model().direct_impacts.results_path.joinpath(
                f"Infometrics_{scenario.direct_impacts.name}.csv"
            ),
            index_col=0,
        )
        # add to self.scenarios the results of the value metric for the given tipping point metric
        for metric in self.attrs.tipping_point_metric:
            self.scenarios[scenario.attrs.name][f"{metric[0]}_value"] = info_df.loc[
                metric[0], "Value"
            ]

        # if any tipping point is reached, return True
        # TODO: maybe change to different approach if more than one tipping
        # point is being assessed (instead of any, maybe you want to check
        # which TPs are reached and return a dict with the results)
        return any(
            self.evaluate_tipping_point(
                info_df.loc[metric[0], "Value"],
                metric[1],
                metric[2],
            )
            for metric in self.attrs.tipping_point_metric
        )

    def evaluate_tipping_point(self, current_value, threshold, operator):
        """Compare current value with threshold for tipping point."""
        operations = {"greater": lambda x, y: x >= y, "less": lambda x, y: x <= y}
        return operations[operator](current_value, threshold)

    def calculate_sea_level_at_threshold(self, tp_results):
        tp_results["ATP"] = "False"
        for metric in self.attrs.tipping_point_metric:
            metric_name, threshold, operator = metric
            valid_data = tp_results[tp_results["Metric"] == f"{metric_name}"].dropna()

            x = valid_data["sea level"]
            y = valid_data["Value"]

            # Create a linear interpolation function
            interpolation_function = interp1d(y, x, fill_value="extrapolate")

            new_rows = pd.DataFrame(
                {
                    "sea level": interpolation_function(threshold),
                    "strategy": valid_data.iloc[0]["strategy"],
                    "Metric": metric_name.value,
                    "Value": threshold,
                    "ATP": "True",
                },
                index=[0],
            )
            tp_results = pd.concat([tp_results, new_rows], ignore_index=True)
        tp_results = tp_results.sort_values(by=["Metric", "sea level"])
        return tp_results

    def prepare_tp_results(self):

        tp_path = self.results_path.joinpath(self.attrs.name)
        # Save results - make directory if it doesn't exist
        if not tp_path.is_dir():
            tp_path.mkdir(parents=True)

        # Convert the scenarios dictionary to a DataFrame
        tp_results = pd.DataFrame.from_dict(self.scenarios, orient="index").reset_index(
            drop=True
        )

        # Add 'sea level' column with hardcoded conversion
        tp_results["sea level"] = [
            float(i) / 10 for i in self.attrs.sealevelrise
        ]  # TODO: fix later if needed

        # Add 'strategy' column
        tp_results["strategy"] = self.attrs.strategy

        # Melt the DataFrame to long format
        tp_results_long = pd.melt(
            tp_results,
            id_vars=["sea level", "strategy"],
            value_vars=[col for col in tp_results.columns if col.endswith("_value")],
            var_name="Metric",
            value_name="Value",
        )

        # Clean up the 'Metric' column
        tp_results_long["Metric"] = tp_results_long["Metric"].str.replace("_value", "")

        # Calculate the sea level at the tipping point threshold
        tp_results_long = self.calculate_sea_level_at_threshold(tp_results_long)

        tp_results_long.to_csv(tp_path / "tipping_point_results.csv")

    # create a function that plots the results from tp_path / "tipping_point_results.csv" against the SLR values
    def plot_results(self):
        tp_path = self.results_path.joinpath(self.attrs.name)
        tp_results = pd.read_csv(tp_path / "tipping_point_results.csv")

        for metric in self.attrs.tipping_point_metric:
            metric_data = tp_results[tp_results["Metric"] == metric[0]]
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=metric_data["sea level"],
                    y=metric_data["Value"],
                    mode="lines+markers",
                    name=f"{metric[0]}",
                )
            )

            fig.add_shape(
                type="line",
                x0=0,
                x1=1,
                y0=metric[1],
                y1=metric[1],
                xref="paper",
                yref="y",
                line=dict(
                    color="Red",
                    width=2,
                    dash="dash",
                ),
                name=f"{metric[0]} threshold",
            )
            fig.update_layout(
                title=f"Tipping Point Analysis for {self.attrs.name}",
                xaxis_title="Sea Level Rise (m)",
                yaxis_title="Value",
            )

            fig.show()

    ### standard functions ###
    def load_file(filepath: Union[str, Path]) -> "TippingPoint":
        """Create risk event from toml file."""
        obj = TippingPoint()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = TippingPointModel.model_validate(toml)
        return obj

    def load_dict(dct: Union[str, Path]) -> "TippingPoint":
        """Create risk event from toml file."""
        obj = TippingPoint()
        obj.attrs = TippingPointModel.model_validate(dct)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save tipping point to a toml file."""
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


# TODO: post processing stuff still to be done for frontend
# make html & plots
# write to file

if __name__ == "__main__":
    from flood_adapt.config import set_system_folder

    database = read_database(
        r"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\Database",
        "charleston_test",
    )
    set_system_folder(
        r"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\Database\\system"
    )

    tp_dict = {
        "name": "tipping_point_test",
        "description": "",
        "event_set": "extreme12ft",
        "strategy": "no_measures",
        "projection": "current",
        "sealevelrise": [0.5, 1.0, 1.5, 2],
        "tipping_point_metric": [
            ("TotalDamageEvent", 130074525.0, "greater"),
            ("DisplacedHighVulnerability", 1000, "greater"),
        ],
    }
    # load
    test_point = TippingPoint.load_dict(tp_dict)
    # create scenarios for tipping points
    test_point.create_tp_scenarios()
    # run all scenarios
    test_point.run_tp_scenarios()

    test_point.plot_results()
