from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard, ScenarioModel
from flood_adapt.object_model.projection import Projection

# from flood_adapt.object_model.scenario import ScenarioModel
from flood_adapt.object_model.strategy import Strategy


class DirectImpacts:
    """class holding all information related to the direct impacts of the scenario.
    Includes functions to run the impact model or check if it has already been run.
    """

    database_input_path: Path
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy
    hazard: Hazard
    has_run: bool = False

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.database_input_path = database_input_path
        self.set_socio_economic_change(scenario.projection)
        self.set_impact_strategy(scenario.strategy)
        self.set_hazard(scenario, database_input_path)

    def set_socio_economic_change(self, projection: str) -> None:
        """Sets the SocioEconomicChange object of the actual scenario

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
        strategy_path = (
            self.database_input_path / "Strategies" / strategy / f"{strategy}.toml"
        )
        self.impact_strategy = Strategy.load_file(strategy_path).get_impact_strategy()

    def set_hazard(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.hazard = Hazard(scenario, database_input_path)

    def infographic(
        self,
        scenario: ScenarioModel,
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

        name = scenario.attrs.name
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
            df["Damage Level"] = np.where(
                df["Relative Damage"] > 0.3, "Severe  (>30%)", "Moderate (<30%)"
            )
            df["Damage Level"] = np.where(
                df["Relative Damage"] < 0.05, "Minor (<5%)", df["Damage Level"]
            )
            df["Damage Level"] = np.where(
                np.isnan(df["Relative Damage"]), "NaN", df["Damage Level"]
            )
            df_sorted = df.sort_values("Relative Damage", ascending=False)
            fig = px.pie(
                df_sorted,
                values="Relative Damage",
                names="Damage Level",
                # color_discrete_map={
                #     "None (0%)": "rgb(255,255,255)",
                #     "Minor (<5%)": "rgb(248,203,173)",
                #     "Moderate  (<30%)": "rgb(242,155,96)",
                #     "Severe  (>30%)": "rgb(155,72,55)"
                # },
                color_discrete_sequence=px.colors.sequential.RdBu,
                category_orders={
                    "Damage Level": [
                        "Severe  (>30%)",
                        "Minor (<5%)",
                        "Moderate  (<30%)",
                    ]
                },
                hole=0.6,
            )

            fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

            fig.add_layout_image(
                {
                    "source": "https://openclipart.org/image/800px/217511",
                    "sizex": 0.3,
                    "sizey": 0.3,
                    "x": 0.5,
                    "y": 0.5,
                    "xanchor": "center",
                    "yanchor": "middle",
                    "visible": True,
                }
            )

            fig.update_layout(
                autosize=True,
                height=700,
                width=700,
                margin={"r": 20, "l": 50, "b": 20, "t": 20},
                title=("Severity of damages to buildings"),
            )

            # write html to results folder
            fig.write_html(database_output_path.joinpath(name, "infographic.html"))
        else:
            raise ValueError(
                "The Direct Impact Model has not run yet. No inforgraphic can be produced."
            )
