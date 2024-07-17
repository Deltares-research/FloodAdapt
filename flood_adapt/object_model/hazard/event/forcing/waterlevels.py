import os

import pandas as pd
from pydantic import BaseModel, Field

from flood_adapt.object_model.hazard.event.timeseries import (
    CSVTimeseries,
    ShapeType,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWaterlevel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    DEFAULT_TIMESTEP,
    REFERENCE_TIME,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulTime,
)

__all__ = [
    "WaterlevelSynthetic",
    "WaterlevelFromCSV",
    "WaterlevelFromModel",
]


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    timeseries: SyntheticTimeseriesModel


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    harmonic_amplitude: UnitfulLength
    harmonic_period: UnitfulTime
    harmonic_phase: UnitfulTime

    def to_timeseries_model(self) -> SyntheticTimeseriesModel:
        return SyntheticTimeseriesModel(
            shape_type=ShapeType.harmonic,
            duration=self.harmonic_period,
            peak_time=self.harmonic_phase,
            peak_value=self.harmonic_amplitude,
        )


class WaterlevelSynthetic(IWaterlevel):
    _source = ForcingSource.SYNTHETIC

    surge: SurgeModel
    tide: TideModel

    def get_data(self) -> pd.DataFrame:
        surge = SyntheticTimeseries().load_dict(self.surge.timeseries)
        tide = SyntheticTimeseries().load_dict(self.tide.to_timeseries_model())

        start_tide = REFERENCE_TIME + tide.attrs.start_time.to_timedelta()
        end_tide = start_tide + tide.attrs.duration.to_timedelta()
        tide_ts = tide.calculate_data()

        time_tide = pd.date_range(
            start=start_tide, end=end_tide, freq=DEFAULT_TIMESTEP.to_timedelta()
        )
        tide_df = pd.DataFrame(tide_ts, index=time_tide)

        start_surge = REFERENCE_TIME + surge.attrs.start_time.to_timedelta()
        end_surge = start_surge + surge.attrs.duration.to_timedelta()
        surge_ts = surge.calculate_data()

        time_surge = pd.date_range(
            start=start_surge, end=end_surge, freq=DEFAULT_TIMESTEP.to_timedelta()
        )
        surge_df = pd.DataFrame(surge_ts, index=time_surge)

        wl_df = surge_df.add(tide_df, axis="index")

        import matplotlib.pyplot as plt

        plt.figure()
        plt.plot(tide_ts, label="tide")
        plt.plot(surge_ts, label="surge")
        plt.legend()
        plt.show()

        return wl_df


class WaterlevelFromCSV(IWaterlevel):
    _source = ForcingSource.CSV

    path: os.PathLike | str

    def get_data(self) -> pd.DataFrame:
        return CSVTimeseries.read_csv(self.path)


class WaterlevelFromModel(IWaterlevel):
    _source = ForcingSource.MODEL
    path: str | os.PathLike | None = Field(default=None)
    # simpath of the offshore model, set this when running the offshore model

    def get_data(self) -> pd.DataFrame:
        # Note that this does not run the offshore simulation, it only tries to read the results from the model.
        # Running the model is done in the process method of the event.
        if self.path is None:
            raise ValueError(
                "Model path is not set. Run the offshore model first using event.process() method."
            )

        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        with SfincsAdapter(model_root=self.path) as _offshore_model:
            return _offshore_model._get_wl_df_from_offshore_his_results()


class WaterlevelFromGauged(IWaterlevel):
    _source = ForcingSource.GAUGED
    # path to the gauge data, set this when writing the downloaded gauge data to disk in event.process()
    path: os.PathLike | str | None = Field(default=None)

    def get_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.path, index_col=0, parse_dates=True)
        df.index.names = ["time"]
        return df
