from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.timeseries import (
    CSVTimeseries,
    CSVTimeseriesModel,
    ShapeType,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWaterlevel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulTime,
)

__all__ = [
    "WaterlevelSynthetic",
    "WaterlevelFromCSV",
    "WaterlevelFromModel",
    "WaterlevelFromMeteo",
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
        surge_start = surge.attrs.peak_time - surge.attrs.duration / 2
        surge_end = surge_start + surge.attrs.duration

        tide_start = tide.attrs.peak_time - tide.attrs.duration / 2
        tide_end = tide_start + tide.attrs.duration

        # TODO `START` should be the start time of the event / some defined default value
        START = datetime(2021, 1, 1, 0, 0, 0)
        start = START + min(surge_start, tide_start).to_timedelta()
        end = start + max(surge_end, tide_end).to_timedelta()

        wl_df = surge.to_dataframe(start, end) + tide.to_dataframe(start, end)

        return wl_df


class WaterlevelFromCSV(IWaterlevel):
    _source = ForcingSource.CSV

    timeseries: CSVTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            CSVTimeseries().load_file(self.timeseries.path).calculate_data()
        )


class WaterlevelFromModel(IWaterlevel):
    _source = ForcingSource.MODEL
    _model_path: str = (
        None  # simpath of the offshore model, set this when running the offshore model
    )

    def get_data(self) -> pd.DataFrame:
        # Note that this does not run the offshore simulation, it only tries to read the results from the model.
        # Running the model is done in the process method of the event.
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        with SfincsAdapter(model_root=self._model_path) as _offshore_model:
            return _offshore_model._get_wl_df_from_offshore_his_results()


class WaterlevelFromMeteo(IWaterlevel):
    _source = ForcingSource.METEO
    _meteo_path: str = (
        None  # path to the meteo data, set this when writing the downloaded meteo data to disk in event.process()
    )

    def get_data(self) -> pd.DataFrame:
        return pd.read_csv(self._meteo_path)  # read the meteo data from disk
