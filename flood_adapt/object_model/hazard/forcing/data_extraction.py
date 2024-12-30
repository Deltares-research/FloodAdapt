from typing import Optional

import pandas as pd

from flood_adapt.misc.config import Settings
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallMeteo,
    RainfallSynthetic,
    RainfallTrack,
)
from flood_adapt.object_model.hazard.forcing.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.forcing.timeseries import (
    CSVTimeseries,
    SyntheticTimeseries,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindConstant,
    WindCSV,
    WindMeteo,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IDischarge,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.interface.site import Site


def _create_time_range(time_frame: TimeModel) -> pd.DatetimeIndex:
    """Create a time range based on the given time frame."""
    return pd.date_range(
        start=time_frame.start_time,
        end=time_frame.end_time,
        freq=time_frame.time_step,
        name="time",
    )


def get_discharge_df(
    discharge: IDischarge, time_frame: TimeModel
) -> Optional[pd.DataFrame]:
    """Extract discharge data into a DataFrame."""
    time = _create_time_range(time_frame)
    if isinstance(discharge, DischargeConstant):
        return pd.DataFrame(
            data={discharge.river.name: [discharge.discharge.value] * len(time)},
            index=time,
        )
    elif isinstance(discharge, DischargeCSV):
        return CSVTimeseries.load_file(path=discharge.path).to_dataframe(time_frame)
    elif isinstance(discharge, DischargeSynthetic):
        df = SyntheticTimeseries.load_dict(data=discharge.timeseries).to_dataframe(
            time_frame
        )
        df.columns = [discharge.river.name]
        return df
    else:
        raise ValueError(f"Unknown discharge type: {discharge}")


def get_rainfall_df(rainfall: IRainfall, time_frame: TimeModel) -> pd.DataFrame:
    """Extract rainfall data into a DataFrame."""
    if isinstance(rainfall, RainfallConstant):
        time = _create_time_range(time_frame)
        return pd.DataFrame(data=[rainfall.intensity.value] * len(time), index=time)
    elif isinstance(rainfall, RainfallCSV):
        return CSVTimeseries.load_file(path=rainfall.path).to_dataframe(time_frame)
    elif isinstance(rainfall, RainfallSynthetic):
        return SyntheticTimeseries.load_dict(data=rainfall.timeseries).to_dataframe(
            time_frame
        )
    elif isinstance(rainfall, (RainfallTrack, RainfallMeteo)):
        raise ValueError(f"Cannot create a dataframe with rainfall type: {rainfall}")
    else:
        raise ValueError(f"Unknown rainfall type: {rainfall}")


def get_waterlevel_df(waterlevel: IWaterlevel, time_frame: TimeModel) -> pd.DataFrame:
    if isinstance(waterlevel, WaterlevelGauged):
        site = Site.load_file(
            Settings().database_path / "static" / "site" / "site.toml"
        )
        if site.attrs.tide_gauge is None:
            raise ValueError("No tide gauge defined for this site.")

        return TideGauge(site.attrs.tide_gauge).get_waterlevels_in_time_frame(
            time_frame
        )

    elif isinstance(waterlevel, WaterlevelCSV):
        return CSVTimeseries.load_file(path=waterlevel.path).to_dataframe(time_frame)
    elif isinstance(waterlevel, WaterlevelSynthetic):
        return waterlevel.to_dataframe(time_frame=time_frame)
    elif isinstance(waterlevel, WaterlevelModel):
        raise ValueError(
            f"Cannot create a dataframe with waterlevel type: {waterlevel}"
        )
    else:
        raise ValueError(f"Unknown waterlevel type: {waterlevel}")


def get_wind_df(wind: IWind, time_frame: TimeModel) -> pd.DataFrame:
    if isinstance(wind, WindConstant):
        return wind.to_dataframe(time_frame)
    elif isinstance(wind, WindCSV):
        return wind.to_dataframe(time_frame)
    elif isinstance(wind, WindSynthetic):
        return wind.to_dataframe(time_frame)
    elif isinstance(wind, (WindMeteo, WindTrack)):
        raise ValueError(f"Cannot create a dataframe with wind type: {wind}")
    else:
        raise ValueError(f"Unknown wind type: {wind}")
