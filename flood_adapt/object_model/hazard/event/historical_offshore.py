import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalOffshoreModel,
    IHistoricalOffshore,
)


class HistoricalOffshore(Event, IHistoricalOffshore):
    attrs = HistoricalOffshoreModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Create Synthetic from toml file."""
        obj = HistoricalOffshore()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HistoricalOffshoreModel.model_validate(toml)
        if obj.attrs.rainfall.source == "timeseries":
            rainfall_csv_path = Path(Path(filepath).parents[0], "rainfall.csv")
            obj.rain_ts = HistoricalOffshore.read_csv(rainfall_csv_path)
        if obj.attrs.wind.source == "timeseries":
            wind_csv_path = Path(Path(filepath).parents[0], "wind.csv")
            obj.wind_ts = HistoricalOffshore.read_csv(wind_csv_path)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """Create Synthetic from object, e.g. when initialized from GUI."""
        obj = HistoricalOffshore()
        obj.attrs = HistoricalOffshoreModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike], additional_files: bool = False):
        """Save event toml.

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        if additional_files:
            raise NotImplementedError(
                "Additional files are not yet implemented for HistoricalOffshore objects."
            )
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
