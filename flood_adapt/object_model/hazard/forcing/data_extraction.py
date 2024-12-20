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
        return CSVTimeseries.load_file(path=discharge.path).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
        )
    elif isinstance(discharge, DischargeSynthetic):
        df = SyntheticTimeseries.load_dict(data=discharge.timeseries).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
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
        return CSVTimeseries.load_file(path=rainfall.path).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
        )
    elif isinstance(rainfall, RainfallSynthetic):
        return SyntheticTimeseries.load_dict(data=rainfall.timeseries).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
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
        return CSVTimeseries.load_file(path=waterlevel.path).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
        )
    elif isinstance(waterlevel, WaterlevelSynthetic):
        surge = SyntheticTimeseries().load_dict(data=waterlevel.surge.timeseries)

        # Calculate Surge time series
        start_surge = time_frame.start_time + surge.attrs.start_time.to_timedelta()
        end_surge = start_surge + surge.attrs.duration.to_timedelta()

        surge_ts = surge.calculate_data()
        time_surge = pd.date_range(
            start=start_surge,
            end=end_surge,
            freq=time_frame.time_step,
            name="time",
        )

        surge_df = pd.DataFrame(surge_ts, index=time_surge)
        tide_df = waterlevel.tide.to_dataframe(
            time_frame.start_time, time_frame.end_time
        )

        # Reindex the shorter DataFrame to match the longer one
        surge_df = surge_df.reindex(tide_df.index).fillna(0)

        # Combine
        return tide_df.add(surge_df, axis="index")

    elif isinstance(waterlevel, WaterlevelModel):
        raise ValueError(
            f"Cannot create a dataframe with waterlevel type: {waterlevel}"
        )
    else:
        raise ValueError(f"Unknown waterlevel type: {waterlevel}")


def get_wind_df(wind: IWind, time_frame: TimeModel) -> pd.DataFrame:
    if isinstance(wind, WindConstant):
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )
        return pd.DataFrame(
            data={
                "magnitude": [wind.speed.value for _ in range(len(time))],
                "direction": [wind.direction.value for _ in range(len(time))],
            },
            index=time,
        )
    elif isinstance(wind, WindCSV):
        return CSVTimeseries.load_file(path=wind.path).to_dataframe(
            start_time=time_frame.start_time, end_time=time_frame.end_time
        )
    elif isinstance(wind, WindSynthetic):
        magnitude = (
            SyntheticTimeseries()
            .load_dict(wind.magnitude)
            .to_dataframe(
                start_time=time_frame.start_time, end_time=time_frame.end_time
            )
        )
        direction = (
            SyntheticTimeseries()
            .load_dict(wind.direction)
            .to_dataframe(
                start_time=time_frame.start_time, end_time=time_frame.end_time
            )
        )
        time = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
            name="time",
        )

        return pd.DataFrame(
            data={
                "mag": magnitude.reindex(time).to_numpy(),
                "dir": direction.reindex(time).to_numpy(),
            },
            index=time,
        )

    elif isinstance(wind, (WindMeteo, WindTrack)):
        raise ValueError(f"Cannot create a dataframe with wind type: {wind}")
    else:
        raise ValueError(f"Unknown wind type: {wind}")
