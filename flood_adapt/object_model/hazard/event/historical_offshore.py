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
from flood_adapt.object_model.utils import import_external_file


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
            if self.attrs.rainfall.source == "timeseries":
                if self.attrs.rainfall.timeseries_file is None:
                    raise ValueError(
                        "The timeseries file for the rainfall source is not set."
                    )
                new_path = import_external_file(
                    self.attrs.rainfall.timeseries_file, Path(filepath).parent
                )
                self.attrs.rainfall.timeseries_file = str(new_path)

            if self.attrs.wind.source == "timeseries":
                if self.attrs.wind.timeseries_file is None:
                    raise ValueError(
                        "The timeseries file for the wind source is not set."
                    )
                new_path = import_external_file(
                    self.attrs.wind.timeseries_file, Path(filepath).parent
                )
                self.attrs.wind.timeseries_file = str(new_path)

            for river in self.attrs.river:
                if river.source == "timeseries":
                    if river.timeseries_file is None:
                        raise ValueError(
                            "The timeseries file for the river source is not set."
                        )
                    new_path = import_external_file(
                        river.timeseries_file, Path(filepath).parent
                    )
                    river.timeseries_file = str(new_path)

            if self.attrs.tide.source == "timeseries":
                if self.attrs.tide.timeseries_file is None:
                    raise ValueError(
                        "The timeseries file for the tide source is not set."
                    )
                new_path = import_external_file(
                    self.attrs.tide.timeseries_file, Path(filepath).parent
                )
                self.attrs.tide.timeseries_file = str(new_path)

        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
