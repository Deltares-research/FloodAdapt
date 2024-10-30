import os
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from scipy.interpolate import interp1d

from flood_adapt.object_model.interface.tipping_points import (
    ITipPoint,
    TippingPointModel,
    TippingPointStatus,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.scenario import Scenario


def ensure_database_loaded():
    """Ensure that the Database class is available without circular issues."""
    try:
        Database()
    except NameError:
        from flood_adapt.dbs_controller import Database
    return Database()


class TippingPoint(ITipPoint):
    """Class holding all information related to tipping points analysis."""

    def __init__(self):
        self.database = ensure_database_loaded()
        self.site_toml_path = Path(self.database.static_path) / "site" / "site.toml"
        self.results_path = self.database.output_path / "tipping_points"
        self.scenarios = {}

    def slr_projections(self, slr):
        """Create projections for sea level rise value."""
        new_projection_name = (
            self.attrs.projection + "_tp_slr" + str(slr).replace(".", "")
        )
        proj = self.database.projections.get(self.attrs.projection)
        proj.attrs.physical_projection.sea_level_rise = UnitfulLength(
            value=slr, units=UnitTypesLength.meters
        )
        proj.attrs.name = new_projection_name
        if proj.attrs.name not in self.database.projections.list_objects()["name"]:
            self.database.projections.save(proj)
        return self

    def check_scenarios_exist(self, scenario_obj, existing_scenarios):
        # check if the current scenario in the tipping point object already exists in the database, if not save it
        for db_scenario in existing_scenarios:
            if scenario_obj == db_scenario:
                return db_scenario
        self.database.scenarios.save(scenario_obj)
        return scenario_obj

    def create_tp_scenarios(self):
        """Create scenarios for each sea level rise value inside the tipping_point folder."""
        for i, slr in enumerate(self.attrs.sealevelrise):
            self.slr_projections(slr)
            self.attrs.sealevelrise[i] = str(slr).replace(".", "")

        scenarios = {
            f"slr_{slr}": {
                "name": f'{self.attrs.projection}_tp_slr{str(slr).replace(".", "")}_{self.attrs.event_set}_{self.attrs.strategy}',
                "event": self.attrs.event_set,
                "projection": f'{self.attrs.projection}_tp_slr{str(slr).replace(".", "")}',
                "strategy": self.attrs.strategy,
            }
            for slr in self.attrs.sealevelrise
        }

        existing_scenarios = self.database.scenarios.list_objects()["objects"]

        for scenario in scenarios.keys():
            scenario_obj = Scenario.load_dict(
                scenarios[scenario], self.database.input_path
            )
            resulting_scenario = self.check_scenarios_exist(
                scenario_obj, existing_scenarios
            )

            self.scenarios[resulting_scenario.attrs.name] = {
                "name": resulting_scenario.attrs.name,
                "description": resulting_scenario.attrs.description,
                "event": resulting_scenario.attrs.event,
                "projection": resulting_scenario.attrs.projection,
                "strategy": resulting_scenario.attrs.strategy,
                "object": resulting_scenario,
            }

        self.attrs.scenarios = list(self.scenarios.keys())
        print("All scenarios checked and created successfully.")

    def run_tp_scenarios(self):
        # TODO: add more strict if clause below
        """Run all scenarios to determine tipping points."""
        if not self.scenarios:
            self.create_tp_scenarios()

        for name, scenario in self.scenarios.items():
            scenario_obj = scenario["object"]
            # IMPORTANT: commented out to run every scenario - uncomment if you want to skip scenarios once tipping point is reached (decision pending on which direction to pursue)
            # if self.attrs.status == TippingPointStatus.reached:
            #     self.scenarios[name]["tipping point reached"] = True
            #     continue

            if not self.scenario_has_run(scenario_obj):
                scenario_obj.run()
                self.has_run = True

            if self.check_tipping_point(scenario_obj):
                self.attrs.status = TippingPointStatus.reached
                self.scenarios[name]["tipping point reached"] = True
            else:
                self.scenarios[name]["tipping point reached"] = False

        self.prepare_tp_results()
        print("All scenarios run successfully.")

        self._make_html()

    def scenario_has_run(self, scenario_obj):
        # TODO: once has_run is refactored (external) we change below to make it more direct
        for db_scenario, finished in zip(
            self.database.scenarios.list_objects()["objects"],
            self.database.scenarios.list_objects()["finished"],
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

        for metric in self.attrs.tipping_point_metric:
            self.scenarios[scenario.attrs.name][f"{metric[0]}_value"] = info_df.loc[
                metric[0], "Value"
            ]

        # TODO: maybe change to a different approach if more than one tipping
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

            interpolation_function = interp1d(y, x, fill_value="extrapolate")

            # Check if the interpolated value is reasonable (not -inf, inf, NaN, etc.)
            if np.isfinite(interpolation_function(threshold)):
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
        if not tp_path.is_dir():
            tp_path.mkdir(parents=True)

        tp_results = pd.DataFrame.from_dict(self.scenarios, orient="index").reset_index(
            drop=True
        )

        tp_results["sea level"] = [
            float(i) / 10 for i in self.attrs.sealevelrise
        ]  # TODO: fix later if needed - quick solution dividing by 10

        tp_results["strategy"] = self.attrs.strategy

        tp_results_long = pd.melt(
            tp_results,
            id_vars=["sea level", "strategy"],
            value_vars=[col for col in tp_results.columns if col.endswith("_value")],
            var_name="Metric",
            value_name="Value",
        )

        tp_results_long["Metric"] = tp_results_long["Metric"].str.replace("_value", "")
        tp_results_long = self.calculate_sea_level_at_threshold(tp_results_long)
        tp_results_long.to_csv(tp_path / "tipping_point_results.csv")

    def _make_html(self):  # Make html
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
                line={
                    "color": "Red",
                    "width": 3,
                    "dash": "dash",
                },
                name=f"{metric[0]} threshold",
            )
            fig.add_annotation(
                text=f"Tipping point: {metric[0]}",
                x=0,
                y=35000,
                xref="x",
                yref="y",
            )
            fig.add_annotation(
                text="Tipping point metric: A value here",  # TODO grab tp value
                x=1,
                y=0,
                xref="paper",
                yref="paper",
                xanchor="left",
                yanchor="top",
                showarrow=False,
            )
            fig.update_layout(
                title=f"Tipping Point Analysis for {self.attrs.name}",
                xaxis_title="Sea Level Rise (m)",
                yaxis_title=f"Tipping point metric: {metric[0]}",
            )

            # write html to results folder
            html = os.path.join(tp_path, "tipping_point.html")
            fig.write_html(html)

    @staticmethod
    def load_file(filepath: Union[str, Path]) -> "TippingPoint":
        """Create risk event from toml file."""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        return TippingPoint.load_dict(toml)

    @staticmethod
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


def load_database(database_path: str, database_name: str, system_folder: str):
    # Call the read_database function with the provided path and name
    from flood_adapt.api.static import read_database
    from flood_adapt.config import Settings

    # Validate and set environment variables
    Settings(
        database_root=database_path,
        database_name=database_name,
        system_folder=system_folder,
    )
    database = read_database(database_path, database_name)

    return database


# I am keeping this for quick access to debug until review is done. Then we delete it.
if __name__ == "__main__":
    system_folder = "C:\\Users\\morenodu\\FloodAdapt\\flood_adapt\\system"
    database_path = "C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\Database"
    database_name = "charleston_test"

    # Load the database
    database = load_database(database_path, database_name, system_folder)

    tp_dict = {
        "name": "tipping_point_test",
        "description": "",
        "event_set": "extreme12ft",
        "strategy": "no_measures",
        "projection": "current",
        "sealevelrise": [0.5, 1.0, 1.5, 2],
        "tipping_point_metric": [
            ("TotalDamageEvent", 130074525.0, "greater"),
            ("DisplacedHighVulnerability", 900, "greater"),
        ],
    }
    # load
    test_point = TippingPoint.load_dict(tp_dict)
    # create scenarios for tipping points
    test_point.create_tp_scenarios()
    # run all scenarios
    test_point.run_tp_scenarios()
    # plot results
    test_point._make_html()
