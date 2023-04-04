from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

from flood_adapt.object_model.interface.projections import PhysicalProjectionModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class PhysicalProjection:
    """The Projection class containing various risk drivers."""

    def __init__(self, data: PhysicalProjectionModel):
        self.attrs = PhysicalProjectionModel.parse_obj(data)

    @staticmethod
    def interp_slr(
        database_input_path: Path, slr_scenario: str, year=float
    ) -> UnitfulLength:
        input_file = database_input_path.parent.joinpath("static", "slr", "slr.csv")

        df = pd.read_csv(input_file)
        slr = UnitfulLength(
            value=np.interp(year, df["year"], df[slr_scenario]), units=df["units"][0]
        )
        return slr

    @staticmethod
    def plot_slr(database_input_path: Path) -> None:
        input_file = database_input_path.parent.joinpath("static", "slr", "slr.csv")

        df = pd.read_csv(input_file)
        ncolors = len(df.columns) - 2
        try:
            units = df["units"].iloc[0]
        except ValueError(
            "Column " "units" " in input/static/slr/slr.csv file missing."
        ) as e:
            print(e)

        try:
            if "year" in df.columns:
                df = df.rename(columns={"year": "Year"})
            elif "Year" in df.columns:
                pass
        except ValueError(
            "Column " "year" " in input/static/slr/slr.csv file missing."
        ) as e:
            print(e)

        df = df.set_index("Year").drop(columns="units").stack().reset_index()
        df = df.rename(
            columns={"level_1": "Scenario", 0: "Sea level rise [{}]".format(units)}
        )

        colors = px.colors.sample_colorscale(
            "rainbow", [n / (ncolors - 1) for n in range(ncolors)]
        )
        fig = px.line(
            df,
            x="Year",
            y=f"Sea level rise [{units}]",
            color="Scenario",
            color_discrete_sequence=colors,
        )

        # fig.update_traces(marker={"line": {"color": "#000000", "width": 2}})

        fig.update_layout(
            autosize=True,
            height=200,
            width=500,
            margin={"r": 20, "l": 20, "b": 20, "t": 20},
            font={"size": 11, "family": "Arial"},
        )

        # write html to results folder
        fig.write_html(database_input_path.parent.joinpath("static", "slr", "slr.html"))
