import os
from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import pandas as pd


class FiatModel:
    # TODO this could be replace by new FIAT?
    def __init__(self, fiat_path: Union[str, os.PathLike], crs: int = 4326) -> None:
        """_summary_

        Parameters
        ----------
        fiat_path : Union[str, os.PathLike]
            _description_
        """
        self.fiat_path = fiat_path
        self.exposure_file = Path(fiat_path) / "Exposure" / "exposure.csv"
        self.exposure_file_crs = crs

    def load_exposure(self) -> gpd.GeoDataFrame:
        """_summary_

        Returns
        -------
        gpd.GeoDataFrame
            _description_
        """
        df = pd.read_csv(self.exposure_file, low_memory=False)
        self.exposure = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(x=df["X Coordinate"], y=df["Y Coordinate"]),
            crs=self.exposure_file_crs,
        )
        return self.exposure

    def get_buildings(
        self, type=Optional[str], non_buildng_names=Optional[list[str]]
    ) -> gpd.GeoDataFrame:
        """_summary_

        Parameters
        ----------
        type : _type_, optional
            _description_, by default Optional[str]

        Returns
        -------
        gpd.GeoDataFrame
            _description_
        """

        if not hasattr(self, "exposure"):
            self.load_exposure()
        buildings = self.exposure.loc[
            ~self.exposure["Primary Object Type"].isin(non_buildng_names), :
        ]
        if type:
            if str(type).upper() != "ALL":
                buildings = buildings.loc[buildings["Primary Object Type"] == type, :]

        return buildings
