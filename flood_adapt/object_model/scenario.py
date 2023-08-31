import os
from pathlib import Path
from typing import Any, Union

import pandas as pd
import tomli
import tomli_w
from fiat_toolbox.infographics.infographics import InfographicsParser
from fiat_toolbox.metrics_writer.fiat_write_metrics_file import MetricsFileWriter

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.hazard.hazard import ScenarioModel
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.site import Site


class Scenario(IScenario):
    """class holding all information related to a scenario"""

    attrs: ScenarioModel
    direct_impacts: DirectImpacts
    database_input_path: Union[str, os.PathLike]

    def init_object_model(self):
        """Create a Direct Impact object"""
        self.site_info = Site.load_file(
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        self.direct_impacts = DirectImpacts(
            scenario=self.attrs, database_input_path=Path(self.database_input_path)
        )
        return self

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Scenario from toml file"""

        obj = Scenario()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ScenarioModel.parse_obj(toml)
        # if scenario is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """create Scenario from object, e.g. when initialized from GUI"""

        obj = Scenario()
        obj.attrs = ScenarioModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Scenario to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    def run(self):
        """run direct impact models for the scenario"""
        self.init_object_model()
        # preprocess model input data first, then run, then post-process
        if not self.direct_impacts.hazard.has_run:
            self.direct_impacts.hazard.preprocess_models()
            self.direct_impacts.hazard.run_models()
            self.direct_impacts.hazard.postprocess_models()
        else:
            print(f"Hazard for scenario '{self.attrs.name}' has already been run.")
        if not self.direct_impacts.has_run:
            # self.direct_impacts.preprocess_models() #TODO: separate preprocessing and running of impact models
            self.direct_impacts.run_models()
            # self.direct_impacts.postprocess_models()
        else:
            print(
                f"Direct impacts for scenario '{self.attrs.name}' has already been run."
            )

        # Create the infometrics files
        self._create_infometrics()

        # Create the infographic files
        # TODO correct infographic creation for risk mode
        if self.direct_impacts.hazard.event_mode != "risk":
            self._create_infographics()

    def _create_infometrics(self):
        # Get the metrics
        fiat_results_path = self.database_input_path.parent.joinpath(
            "output",
            "results",
            f"{self.attrs.name}",
            "fiat_model",
            "output",
            "output.csv",
        )

        # Get the metrics configuration
        if self.direct_impacts.hazard.event_mode == "risk":
            ext = "_risk"
        else:
            ext = ""

        metrics_config_path = self.database_input_path.parent.joinpath(
            "static",
            "templates",
            "infometrics",
            f"metrics_config{ext}.toml",
        )

        # Specify the metrics output path
        metrics_outputs_path = self.database_input_path.parent.joinpath(
            "output",
            "infometrics",
            f"{self.attrs.name}_metrics.csv",
        )

        # Get the results dataframe
        df = pd.read_csv(fiat_results_path)

        # Write the metrics to file
        metrics_writer = MetricsFileWriter(metrics_config_path)

        metrics_writer.parse_metrics_to_file(
            df_results=df, metrics_path=metrics_outputs_path, write_aggregate=None
        )
        metrics_writer.parse_metrics_to_file(
            df_results=df, metrics_path=metrics_outputs_path, write_aggregate="all"
        )

    def _create_infographics(self):
        # Get the infographic
        InfographicsParser().write_infographics_to_file(
            scenario_name=self.attrs.name,
            database_path=Path(self.database_input_path).parent,
            keep_metrics_file=True,
        )

    def __eq__(self, other):
        if not isinstance(other, Scenario):
            # don't attempt to compare against unrelated types
            return NotImplemented

        test1 = self.attrs.event == other.attrs.event
        test2 = self.attrs.projection == other.attrs.projection
        test3 = self.attrs.strategy == other.attrs.strategy
        return test1 & test2 & test3
