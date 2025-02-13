from pathlib import Path
from typing import ClassVar, Optional

import cht_observations.observation_stations as cht_station
import pandas as pd
from noaa_coops.station import COOPSAPIError

from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.forcing.timeseries import CSVTimeseries
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.interface.tide_gauge import (
    ITideGauge,
    TideGaugeModel,
)
from flood_adapt.object_model.io import unit_system as us


class TideGauge(ITideGauge):
    _cached_data: ClassVar[dict[str, pd.DataFrame]] = {}
    logger = FloodAdaptLogging.getLogger("TideGauge")

    def __init__(self, attrs: TideGaugeModel):
        if isinstance(attrs, TideGaugeModel):
            self.attrs = attrs
        else:
            self.attrs = TideGaugeModel.model_validate(attrs)

    def get_waterlevels_in_time_frame(
        self,
        time: TimeModel,
        out_path: Optional[Path] = None,
        units: us.UnitTypesLength = us.UnitTypesLength.meters,
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        time : TimeModel
            Time model with start and end time.
        tide_gauge : TideGaugeModel
            Tide gauge model.
        out_path : Optional[Path], optional
            Path to save the data, by default None.
        units : us.UnitTypesLength, optional
            Unit of the waterlevel, by default us.UnitTypesLength.meters.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel for each observation station as columns.
        """
        self.logger.info(
            f"Retrieving waterlevels for tide gauge {self.attrs.ID} for {time}"
        )
        if self.attrs.file:
            gauge_data = self._read_imported_waterlevels(
                time=time, path=self.attrs.file
            )
        else:
            gauge_data = self._download_tide_gauge_data(time=time)

        if gauge_data is None:
            self.logger.warning(
                f"Could not retrieve waterlevels for tide gauge {self.attrs.ID}"
            )
            return pd.DataFrame()

        gauge_data.columns = [f"waterlevel_{self.attrs.ID}"]
        gauge_data = gauge_data * us.UnitfulLength(
            value=1.0, units=self.attrs.units
        ).convert(units)

        if out_path is not None:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            gauge_data.to_csv(Path(out_path))
        return gauge_data

    @staticmethod
    def _read_imported_waterlevels(time: TimeModel, path: Path) -> pd.DataFrame:
        """Read waterlevels from an imported csv file.

        Parameters
        ----------
        path : Path
            Path to the csv file containing the waterlevel data. The csv file should have a column with the waterlevel data and a column with the time data.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel for each observation station as columns.
            The data is sliced to the time range specified in the time model.
        """
        return (
            CSVTimeseries[us.UnitfulLength]()
            .load_file(path)
            .to_dataframe(time_frame=time)
        )

    def _download_tide_gauge_data(self, time: TimeModel) -> pd.DataFrame | None:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        obs_point : ObsPointModel
            Observation point model.
        source : str
            Source of the data.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel of the observation station as the column.
        None
            If the data could not be downloaded.
        """
        cache_key = f"{self.attrs.ID}_{time.start_time}_{time.end_time}"
        if cache_key in self.__class__._cached_data:
            self.logger.info("Tide gauge data retrieved from cache")
            return self.__class__._cached_data[cache_key]

        try:
            source_obj = cht_station.source(self.attrs.source.value)
            series = source_obj.get_data(
                id=self.attrs.ID,
                tstart=time.start_time,
                tstop=time.end_time,
            )
            index = pd.date_range(
                start=time.start_time,
                end=time.end_time,
                freq=time.time_step,
                name="time",
            )
            series = series.reindex(index, method="nearest")
            df = pd.DataFrame(data=series, index=index)

        except COOPSAPIError as e:
            self.logger.error(
                f"Could not download tide gauge data for station {self.attrs.ID}. {e}"
            )
            return None

        # Cache the result
        self.__class__._cached_data[cache_key] = df

        return df
