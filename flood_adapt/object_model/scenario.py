import os
from pathlib import Path
from typing import Any, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import tomli
import tomli_w
from plotly.subplots import make_subplots

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
        # if strategy is created by path use that to get to the database path
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
        if not self.direct_impacts.hazard.has_run:
            self.direct_impacts.hazard.run_models()
        else:
            print(f"Hazard for scenario '{self.attrs.name}' has already been run.")
        if not self.direct_impacts.has_run:
            self.direct_impacts.run_models()
        else:
            print(
                f"Direct impacts for scenario '{self.attrs.name}' has already been run."
            )

    def impact_metrics(self) -> pd.DataFrame:
        self.has_run_impact = (
            True  # TODO remove when this has been added through the Fiat adapter
        )
        output_path = Path(self.database_input_path).parent.joinpath(
            "output",
            "results",
            self.attrs.name,
        )

        if self.has_run_impact:
            # read FIAT results per object from csv file
            csv_file = output_path.joinpath(f"{self.attrs.name}_results.csv")
            df = pd.read_csv(csv_file)

            # calculate FEMA damage categories
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
            FEMA_count = pd.DataFrame()
            FEMA_count["All"] = {cat: len(df[df["FEMA"] == cat]) for cat in categories}
            for obj_type in np.unique(df["Primary Object Type"]):
                FEMA_count[obj_type] = {
                    cat: df.where(
                        df[df["Primary Object Type"] == obj_type]["FEMA"] == cat
                    ).count()["FEMA"]
                    for cat in categories
                }
            if "road" in np.unique(df["Primary Object Type"]):
                FEMA_count["buildings"] = FEMA_count["All"] - FEMA_count["road"]

            # calculate
            return FEMA_count

        else:
            raise ValueError(
                "The Direct Impact Model has not run yet. No inforgraphic can be produced."
            )

    # TODO: should probably be moved to frontend (like all plotting functions, see dbcontroller)
    def infographic(self) -> str:
        output_path = Path(self.database_input_path).parent.joinpath(
            "output",
            "results",
            self.attrs.name,
        )
        infographic_html = output_path.joinpath(f"{self.attrs.name}.html")
        if infographic_html.exists():
            return str(infographic_html)
        FEMA_count = self.impact_metrics()
        # make figure with subplots
        trace1 = go.Pie(
            values=FEMA_count["RES"].to_list(),
            labels=FEMA_count.index.to_list(),
            hole=0.6,
            name="Buildings",
            textposition="none",
            marker={
                "colors": ["#F8CBAD", "#F29B60", "#9B4837", "#311611"],
                "line": {"color": "#000000", "width": 2},
            },
        )

        trace2 = go.Pie(
            values=FEMA_count["RES"].to_list(),
            labels=FEMA_count.index.to_list(),
            hole=0.6,
            name="Businesses",
            textposition="none",
            marker={
                "colors": ["#F8CBAD", "#F29B60", "#9B4837", "#311611"],
                "line": {"color": "#000000", "width": 2},
            },
        )

        trace3 = go.Pie(
            values=FEMA_count["PUB"].to_list(),
            labels=FEMA_count.index.to_list(),
            hole=0.6,
            name="Education",
            textposition="none",
            marker={
                "colors": ["#F8CBAD", "#F29B60", "#9B4837", "#311611"],
                "line": {"color": "#000000", "width": 2},
            },
        )

        fig = make_subplots(
            rows=2,
            cols=3,
            specs=[
                [{"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
                [{"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
            ],
            subplot_titles=[
                "Homes",
                "Businesses",
                "Public",
                "Road segments",
            ],
        )

        # subplot 1,1: Homes
        fig.append_trace(trace1, 1, 1)

        fig.add_layout_image(
            {
                "source": "https://openclipart.org/image/800px/217511",
                "sizex": 0.1,
                "sizey": 0.1,
                "x": 0.145,
                "y": 0.83,
                "xanchor": "center",
                "yanchor": "middle",
                "visible": True,
            }
        )

        fig.add_annotation(
            x=0.11,
            y=0.785,
            text="{}".format(FEMA_count["RES"].sum()),
            font={"size": 14, "family": "Verdana", "color": "black"},
            align="center",
            showarrow=False,
        )

        # subplot 1,2: Businesses
        fig.append_trace(trace2, 1, 2)

        fig.add_layout_image(
            {
                "source": "https://openclipart.org/image/800px/229840",
                "sizex": 0.1,
                "sizey": 0.1,
                "x": 0.5,
                "y": 0.83,
                "xanchor": "center",
                "yanchor": "middle",
                "visible": True,
            }
        )

        fig.add_annotation(
            x=0.5,
            y=0.785,
            text="{}".format(FEMA_count["COM"].sum()),
            font={"size": 14, "family": "Verdana", "color": "black"},
            align="center",
            showarrow=False,
        )

        # subplot 1,3: Schools
        fig.append_trace(trace3, 1, 3)

        fig.add_layout_image(
            {
                "source": "https://openclipart.org/image/800px/190967",
                "sizex": 0.1,
                "sizey": 0.1,
                "x": 0.86,
                "y": 0.83,
                "xanchor": "center",
                "yanchor": "middle",
                "visible": True,
            }
        )

        fig.add_annotation(
            x=0.87,
            y=0.785,
            text="{}".format(FEMA_count["PUB"].sum()),
            font={"size": 14, "family": "Verdana", "color": "black"},
            align="center",
            showarrow=False,
        )

        # subplot 1,4: Roads
        fig.add_annotation(
            x=0.12,
            y=0.1,
            text="{}".format(FEMA_count["road"].sum()),
            font={"size": 14, "family": "Verdana", "color": "black"},
            align="center",
            showarrow=False,
        )

        fig.add_layout_image(
            {
                "source": "https://openclipart.org/image/800px/190006",
                "sizex": 0.1,
                "sizey": 0.1,
                "x": 0.145,
                "y": 0.22,
                "xanchor": "center",
                "yanchor": "middle",
                "visible": True,
            }
        )

        fig.update_layout(
            font={"size": 12, "family": "Verdana", "color": "black"},
            autosize=True,
            height=500,
            width=800,
            # margin={"r": 20, "l": 50, "b": 20, "t": 20},
            # title=("FEMA Flood Damage Categories"),
        )

        fig.update_layout_images()

        fig.write_html(infographic_html)

        return str(infographic_html)
