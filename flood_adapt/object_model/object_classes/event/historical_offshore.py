import os
from pathlib import Path
from typing import Union

from flood_adapt.object_model.interface.events import (
    IHistoricalOffshore,
)
from flood_adapt.object_model.models.events import HistoricalOffshoreModel
from flood_adapt.object_model.object_classes.event.event import Event


class HistoricalOffshore(Event, IHistoricalOffshore):
    attrs = HistoricalOffshoreModel

    def load_additional_data(self, filepath: Union[str, os.PathLike]):
        """ Load additional data next to the toml file

        Parameters
        ----------
        filepath : Union[str, os.PathLike]
            path to the directory where the additional data is stored (same directory as the toml file)

        Returns
        -------
        HistoricalOffshore
            HistoricalOffshore object
        """

        if self.attrs.rainfall.source == "timeseries":
            rainfall_csv_path = Path(filepath, "rainfall.csv")
            self.rain_ts = HistoricalOffshore.read_csv(rainfall_csv_path)
        if self.attrs.wind.source == "timeseries":
            wind_csv_path = Path(filepath, "wind.csv")
            self.wind_ts = HistoricalOffshore.read_csv(wind_csv_path)
        return self