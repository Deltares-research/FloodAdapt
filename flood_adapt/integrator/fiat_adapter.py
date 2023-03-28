from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio

pio.renderers.default = "vscode"


class FiatAdapter:
    @staticmethod
    def infographic(
        database_path, name: str
    ):  # should use scenario and scenario.input_path in the future
        csv_file = database_path.joinpath(
            "output", "results", name, f"{name}_results.csv"
        )
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
            df["Relative Damage"] > 0.05, "Minor (<5%)", "None"
        )
        df["Damage Level"] = np.where(
            df["Relative Damage"] > 0.1, "Moderate  (<10%)", df["Damage Level"]
        )
        df["Damage Level"] = np.where(
            df["Relative Damage"] > 0.5, "Major  (>50%)", df["Damage Level"]
        )
        fig = px.pie(
            df,
            values="Relative Damage",
            names="Damage Level",
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.6,
        )
        # add house icon does not work yet
        fig.add_layout_image(
            {
                # "source": "https://game-icons.net/icons/000000/ffffff/1x1/delapouite/house.png",
                "source": "https://openclipart.org/image/800px/217511",
                "sizex": 0.2,
                "sizey": 0.2,
                "xanchor": "center",
                "yanchor": "middle",
                "visible": True,
            }
        )

        fig.update_layout(
            autosize=True,
            height=800,
            width=700,
            margin={"r": 20, "l": 50, "b": 20, "t": 20},
            title=("Severity of damages to buildings"),
        )

        fig.write_html("infographic.html")


database_path = Path(
    r"c:/Users/winter_ga/Offline_Data/project_data/DHS/CFRSS_Sep22/CFRSS/database/charleston"
)
FiatAdapter.infographic(database_path, "current_kingtide2021_no_measures")
