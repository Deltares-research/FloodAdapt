import pandas as pd
from pydantic import BaseModel

from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.hazard.new_events.timeseries import (
    CSVTimeseries,
    CSVTimeseriesModel,
    ShapeType,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulTime,
)


class IWaterlevel(IForcing):
    _type = ForcingType.WATERLEVEL
    _source = None


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
        surge = SyntheticTimeseries().load_dict(self.surge.timeseries).calculate_data()
        tide = (
            SyntheticTimeseries()
            .load_dict(self.tide.to_timeseries_model())
            .calculate_data()
        )
        return surge + tide


class WaterlevelFromFile(IWaterlevel):
    _source = ForcingSource.FILE

    timeseries: CSVTimeseriesModel

    def get_data(self) -> pd.DataFrame:
        return CSVTimeseries().load_file(self.timeseries.path).calculate_data()


class WaterlevelFromModel(IWaterlevel):
    _source = ForcingSource.MODEL

    def get_data(self) -> pd.DataFrame:
        pass
