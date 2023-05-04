import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

from flood_adapt.integrator.fiat_adapter import FiatAdapter
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard, ScenarioModel
from flood_adapt.object_model.projection import Projection

# from flood_adapt.object_model.scenario import ScenarioModel
from flood_adapt.object_model.strategy import Strategy


class DirectImpacts:
    """Class holding all information related to the direct impacts of the scenario.
    Includes methods to run the impact model or check if it has already been run.
    """

    name: str
    database_input_path: Path
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy
    hazard: Hazard
    has_run: bool = False

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.name = scenario.name
        self.database_input_path = database_input_path
        self.scenario = scenario
        self.set_socio_economic_change(scenario.projection)
        self.set_impact_strategy(scenario.strategy)
        self.set_hazard(scenario, database_input_path)

    def set_socio_economic_change(self, projection: str) -> None:
        """Sets the SocioEconomicChange object of the scenario.

        Parameters
        ----------
        projection : str
            Name of the projection used in the scenario
        """
        projection_path = (
            self.database_input_path / "Projections" / projection / f"{projection}.toml"
        )
        self.socio_economic_change = Projection.load_file(
            projection_path
        ).get_socio_economic_change()

    def set_impact_strategy(self, strategy: str) -> None:
        """Sets the ImpactStrategy object of the scenario.

        Parameters
        ----------
        strategy : str
            Name of the strategy used in the scenario
        """
        strategy_path = (
            self.database_input_path / "Strategies" / strategy / f"{strategy}.toml"
        )
        self.impact_strategy = Strategy.load_file(strategy_path).get_impact_strategy()

    def set_hazard(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        """Sets the Hazard object of the scenario.

        Parameters
        ----------
        scenario : str
            Name of the scenario
        """
        self.hazard = Hazard(scenario, database_input_path)

    def run_models(self):
        self.run_fiat()

    def run_fiat(self):
        """Updates FIAT model based on scenario information and then runs the FIAT model"""
        if not self.hazard.has_run:
            raise ValueError(
                "Hazard for this scenario has not been run yet! FIAT cannot be initiated."
            )
        # Get the location of the FIAT template model
        template_path = (
            self.database_input_path.parent / "static" / "templates" / "fiat"
        )
        # Read FIAT template with FIAT adapter
        fa = FiatAdapter(
            model_root=template_path, database_path=self.database_input_path.parent
        )

        # Define results path
        results_path = (
            self.database_input_path.parent
            / "output"
            / "results"
            / self.scenario.name
            / "fiat_model"
        )
        # If path for results does not yet exist, make it
        if not results_path.is_dir():
            results_path.mkdir(parents=True)
        else:
            shutil.rmtree(results_path)

        # Get ids of existing objects
        ids_existing = fa.fiat_model.exposure.exposure_db["Object ID"].to_list()

        # Implement socioeconomic changes if needed

        # First apply economic growth to existing objects
        if self.socio_economic_change.attrs.economic_growth != 0:
            fa.apply_economic_growth(
                economic_growth=self.socio_economic_change.attrs.economic_growth,
                ids=ids_existing,
            )

        # Then we create the new population growth area if provided
        # In that area only the economic growth is taken into account
        # Order matters since for the pop growth new we only want the economic growth!
        if self.socio_economic_change.attrs.population_growth_new != 0:
            area_path = (
                self.database_input_path
                / "projections"
                / self.scenario.projection
                / self.socio_economic_change.attrs.new_development_shapefile
            )

            fa.apply_population_growth_new(
                population_growth=self.socio_economic_change.attrs.population_growth_new,
                ground_floor_height=self.socio_economic_change.attrs.new_development_elevation.value,
                elevation_type=self.socio_economic_change.attrs.new_development_elevation.type,
                area_path=area_path,
            )

        # Last apply population growth to existing objects
        if self.socio_economic_change.attrs.population_growth_existing != 0:
            fa.apply_population_growth_existing(
                population_growth=self.socio_economic_change.attrs.population_growth_existing,
                ids=ids_existing,
            )

        # Then apply Impact Strategy by iterating trough the impact measures
        for measure in self.impact_strategy.measures:
            if measure.attrs.type == "elevate_properties":
                fa.apply_elevate_properties(measure)

        # Save the updated FIAT model
        fa.fiat_model.set_root(results_path)
        fa.fiat_model.write()

        # Then run FIAT
        print("FIAT not working yet")

        # Indicator that fiat model has run
        self.__setattr__("has_run", True)

    def infographic(
        self,
    ) -> None:  # should use scenario and scenario.input_path in the future
        self.has_run_impact = (
            True  # TODO remove when this has been added through the Fiat adapter
        )
        # database_output_path = scenario.database_input_path.parent.joinpath(
        #     "output", "results"
        # )
        database_output_path = Path(
            r"p:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/database/charleston/output/results"
        )  # replace with above outside of pytest

        # name = self.scenario.name
        name = "current_kingtide2021_no_measures"  # TODO: remove when using with API
        if self.has_run_impact:
            csv_file = database_output_path.joinpath(name, f"{name}_results.csv")
            df = pd.read_csv(csv_file)
            df["Relative Damage"] = df["Total Damage Event"] / np.nansum(
                df[
                    [
                        "Max Potential Damage: Structure",
                        "Max Potential Damage: Content",
                        "Max Potential Damage: Other",
                    ]
                ],
                axis=1,
            )
            df["Relative Structure Damage"] = (
                df["Structure Damage Event"] / df["Max Potential Damage: Structure"]
            )
            df["Damage Level"] = np.where(
                df["Relative Damage"] > 0.3, "Severe  (>30%)", "Moderate (<30%)"
            )
            df["Damage Level"] = np.where(
                df["Relative Damage"] < 0.05, "Minor (<5%)", df["Damage Level"]
            )
            df["Damage Level"] = np.where(
                np.isnan(df["Relative Damage"]), "NaN", df["Damage Level"]
            )
            df["FEMA"] = np.where(
                df["Inundation Depth Event Structure"] != 0, "Affected", np.nan
            )
            df["FEMA"] = np.where(
                df["Inundation Depth Event Structure"] > 0.25, "Minor", df["FEMA"]
            )
            df["FEMA"] = np.where(
                df["Inundation Depth Event Structure"] > 1.5, "Major", df["FEMA"]
            )
            df["FEMA"] = np.where(
                df["Relative Structure Damage"] > 0.9, "Destroyed", df["FEMA"]
            )

            categories = ["Affected", "Minor", "Major", "Destroyed"]
            FEMA_count = {cat: len(df[df["FEMA"] == cat]) for cat in categories}
            df_affected = pd.DataFrame(FEMA_count.items()).rename(
                columns={0: "Category", 1: "Count"}
            )

            fig = px.pie(
                df_affected,
                values="Count",
                names="Category",
                hole=0.6,
                title=("FEMA Flood Damage Categories"),
            )

            fig.update_traces(
                sort=False,
                marker={
                    "colors": ["#F8CBAD", "#F29B60", "#9B4837", "#311611"],
                    "line": {"color": "#000000", "width": 2},
                },
            )

            fig.add_layout_image(
                {
                    "source": "https://openclipart.org/image/800px/217511",
                    "sizex": 0.3,
                    "sizey": 0.3,
                    "x": 0.5,
                    "y": 0.55,
                    "xanchor": "center",
                    "yanchor": "middle",
                    "visible": True,
                }
            )

            fig.add_annotation(
                x=0.5,
                y=0.3,
                text="{}".format(df_affected["Count"].sum()),
                font={"size": 60, "family": "Verdana", "color": "black"},
                showarrow=False,
            )

            fig.update_layout(
                autosize=True,
                height=700,
                width=700,
                margin={"r": 20, "l": 50, "b": 20, "t": 20},
                # title=("FEMA Flood Damage Categories"),
            )

            # write html to results folder
            fig.write_html(database_output_path.joinpath(name, "infographic.html"))
        else:
            raise ValueError(
                "The Direct Impact Model has not run yet. No inforgraphic can be produced."
            )
