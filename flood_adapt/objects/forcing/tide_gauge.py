from enum import Enum
from pathlib import Path
from typing import ClassVar, Optional

import cht_observations.observation_stations as cht_station
import pandas as pd
from noaa_coops.station import COOPSAPIError
from pydantic import BaseModel, model_validator

from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.timeseries import CSVTimeseries


class TideGaugeSource(str, Enum):
    """The accepted input for the variable source in tide_gauge."""

    file = "file"
    noaa_coops = "noaa_coops"


class TideGauge(BaseModel):
    """The accepted input for the variable tide_gauge in Site.

    The obs_station is used for the download of tide gauge data, to be added to the hazard model as water level boundary condition.

    Attributes
    ----------
    name : Optional[int, str]
        Name of the tide gauge. Default is None.
    description : Optional[str]
        Description of the tide gauge. Default is "".
    source : TideGaugeSource
        Source of the tide gauge data.
    reference : str
        Reference of the tide gauge data. Should be defined in site.sfincs.water_level
    ID : Optional[int]
        ID of the tide gauge data. Default is None.
    file : Optional[Path]
        Only for file based tide gauges. Should be a path relative to the static folder. Default is None.
    lat : Optional[float]
        Latitude of the tide gauge data. Default is None.
    lon : Optional[float]
        Longitude of the tide gauge data. Default is None.
    units : us.UnitTypesLength
        Units of the water levels in the downloaded file. Default is us.UnitTypesLength.meters.

    """

    name: Optional[int | str] = None
    description: Optional[str] = ""
    source: TideGaugeSource
    reference: str
    ID: Optional[int] = None  # Attribute used to download from correct gauge
    file: Optional[Path] = None  # for locally stored data
    lat: Optional[float] = None
    lon: Optional[float] = None
    units: us.UnitTypesLength = (
        us.UnitTypesLength.meters
    )  # units of the water levels in the downloaded file

    _cached_data: ClassVar[dict[str, pd.DataFrame]] = {}
    logger: ClassVar = FloodAdaptLogging.getLogger("TideGauge")

    @model_validator(mode="after")
    def validate_selection_type(self) -> "TideGauge":
        if self.source == TideGaugeSource.file and self.file is None:
            raise ValueError(
                "If `source` is 'file' a file path relative to the static folder should be provided with the attribute 'file'."
            )
        elif self.source == TideGaugeSource.noaa_coops and self.ID is None:
            raise ValueError(
                "If `source` is 'noaa_coops' the id of the station should be provided with the attribute 'ID'."
            )

        return self

    def get_waterlevels_in_time_frame(
        self,
        time: TimeFrame,
        out_path: Optional[Path] = None,
        units: us.UnitTypesLength = us.UnitTypesLength.meters,
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        time : TimeFrame
            Time model with start and end time.
        tide_gauge : TideGauge
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
        self.logger.info(f"Retrieving waterlevels for tide gauge {self.ID} for {time}")
        if self.file:
            gauge_data = self._read_imported_waterlevels(time=time, path=self.file)
        else:
            gauge_data = self._download_tide_gauge_data(time=time)

        if gauge_data is None:
            self.logger.warning(
                f"Could not retrieve waterlevels for tide gauge {self.ID}"
            )
            return pd.DataFrame()

        gauge_data.columns = [f"waterlevel_{self.ID}"]
        gauge_data = gauge_data * us.UnitfulLength(value=1.0, units=self.units).convert(
            units
        )

        if out_path is not None:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            gauge_data.to_csv(Path(out_path))
        return gauge_data

    def _read_imported_waterlevels(self, time: TimeFrame, path: Path) -> pd.DataFrame:
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
        return CSVTimeseries.load_file(
            path=path, units=us.UnitfulLength(value=0, units=self.units)
        ).to_dataframe(time_frame=time)

    def _download_tide_gauge_data(self, time: TimeFrame) -> pd.DataFrame | None:
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
        cache_key = f"{self.ID}_{time.start_time}_{time.end_time}"
        if cache_key in self.__class__._cached_data:
            self.logger.info("Tide gauge data retrieved from cache")
            return self.__class__._cached_data[cache_key]

        try:
            source_obj = cht_station.source(self.source.value)
            series = source_obj.get_data(
                id=self.ID,
                tstart=time.start_time,
                tstop=time.end_time,
                datum=self.reference,
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
                f"Could not download tide gauge data for station {self.ID}. {e}"
            )
            return None

        # Cache the result
        self.__class__._cached_data[cache_key] = df

        return df
