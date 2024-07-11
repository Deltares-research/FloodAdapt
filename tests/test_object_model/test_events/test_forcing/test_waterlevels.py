import pandas as pd

from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitfulTime


class TestWaterlevelSynthetic:
    def test_waterlevel_synthetic_get_data(self):
        # Arrange
        surge_model = SurgeModel(
            timeseries=SyntheticTimeseriesModel(
                shape_type=ShapeType.constant,
                duration=UnitfulTime(4, "hours"),
                peak_time=UnitfulTime(2, "hours"),
                peak_value=UnitfulLength(2, "meters"),
            )
        )

        tide_model = TideModel(
            harmonic_amplitude=UnitfulLength(1, "meters"),
            harmonic_period=UnitfulTime(4, "hours"),
            harmonic_phase=UnitfulTime(2, "hours"),
        )

        # Act
        wl_df = WaterlevelSynthetic(surge=surge_model, tide=tide_model).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
