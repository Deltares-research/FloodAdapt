import pandas as pd
import pytest

from flood_adapt.config.sfincs import RiverModel
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects.events.historical import (
    HistoricalEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import DischargeConstant
from flood_adapt.objects.forcing.forcing import ForcingType
from flood_adapt.objects.forcing.rainfall import RainfallMeteo
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.timeseries import (
    CSVTimeseries,
    ShapeType,
    TimeseriesFactory,
)
from flood_adapt.objects.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelCSV,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import WindMeteo
from flood_adapt.objects.scenarios.scenarios import Scenario


class TestWaterlevelSynthetic:
    @pytest.mark.parametrize(
        "surge_shape, peak_time, surge_duration, surge_peak_value, tide_amplitude, tide_period, tide_phase",
        [  # "surge_shape,       peak_time,                surge_duration,           surge_peak_value,           tide_amplitude,             tide_period,
            (
                ShapeType.gaussian,
                us.UnitfulTime(value=12, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=24, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=3, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=1.5, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=12, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.gaussian,
                us.UnitfulTime(value=18, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=36, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=4, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=14, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=6, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.gaussian,
                us.UnitfulTime(value=14, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=28, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=0.8, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=4, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.block,
                us.UnitfulTime(value=12, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=12, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=1, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=10, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=4, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.block,
                us.UnitfulTime(value=6, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=6, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=1, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=0.5, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=6, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.block,
                us.UnitfulTime(value=10, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=20, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=3, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=1.2, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=12, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=6, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.triangle,
                us.UnitfulTime(value=12, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=18, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=1.5, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=0.5, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.triangle,
                us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=16, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=2.5, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=1, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=10, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=5, units=us.UnitTypesTime.hours),
            ),
            (
                ShapeType.triangle,
                us.UnitfulTime(value=16, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=32, units=us.UnitTypesTime.hours),
                us.UnitfulLength(value=3.5, units=us.UnitTypesLength.meters),
                us.UnitfulLength(value=1.5, units=us.UnitTypesLength.meters),
                us.UnitfulTime(value=10, units=us.UnitTypesTime.hours),
                us.UnitfulTime(value=7, units=us.UnitTypesTime.hours),
            ),
        ],
    )
    def test_waterlevel_synthetic_to_dataframe(
        self,
        peak_time,
        surge_shape,
        surge_duration,
        surge_peak_value,
        tide_amplitude,
        tide_period,
        tide_phase,
    ):
        # Arrange
        surge_model = SurgeModel(
            timeseries=TimeseriesFactory.from_args(
                shape_type=surge_shape,
                duration=surge_duration,
                peak_time=peak_time,
                peak_value=surge_peak_value,
            )
        )

        tide_model = TideModel(
            harmonic_amplitude=tide_amplitude,
            harmonic_period=tide_period,
            harmonic_phase=tide_phase,
        )

        expected_max = abs((surge_peak_value + tide_amplitude).value)
        expected_min = -abs(tide_amplitude.value)

        # Act
        waterlevel_forcing = WaterlevelSynthetic(surge=surge_model, tide=tide_model)
        wl_df = waterlevel_forcing.to_dataframe(time_frame=TimeFrame())

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert (
            wl_df["waterlevel"].max() <= expected_max
        ), f"Expected max {surge_peak_value} + {tide_amplitude} ~ {expected_max}, got {wl_df['waterlevel'].max()}"
        assert (
            wl_df["waterlevel"].min() >= expected_min
        ), f"Expected min {-abs(tide_amplitude.value)} ~ {expected_min}, got {wl_df['waterlevel'].min()}"


class TestWaterlevelCSV:
    # Arrange
    def test_waterlevel_from_csv_to_dataframe(
        self, tmp_path, dummy_1d_timeseries_df: pd.DataFrame
    ):
        path = tmp_path / "test.csv"
        dummy_1d_timeseries_df.to_csv(path)
        time = TimeFrame(
            start_time=dummy_1d_timeseries_df.index[0],
            end_time=dummy_1d_timeseries_df.index[-1],
        )

        expected_df = CSVTimeseries.load_file(
            path=path,
            units=us.UnitfulDischarge(value=0, units=us.UnitTypesDischarge.cms),
        ).to_dataframe(time_frame=time)

        # Act
        wl_df = WaterlevelCSV(path=path).to_dataframe(time_frame=time)

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert expected_df.index.equals(wl_df.index)
        assert expected_df.columns.equals(wl_df.columns)
        pd.testing.assert_frame_equal(wl_df, expected_df)


class TestWaterlevelModel:
    @pytest.fixture()
    def setup_offshore_scenario(self, test_db: IDatabase):
        event = HistoricalEvent(
            HistoricalEvent(
                name="test_historical_offshore_meteo",
                time=TimeFrame(),
                forcings={
                    ForcingType.WATERLEVEL: [
                        WaterlevelModel(),
                    ],
                    ForcingType.WIND: [
                        WindMeteo(),
                    ],
                    ForcingType.RAINFALL: [
                        RainfallMeteo(),
                    ],
                    ForcingType.DISCHARGE: [
                        DischargeConstant(
                            river=RiverModel(
                                name="cooper",
                                description="Cooper River",
                                x_coordinate=595546.3,
                                y_coordinate=3675590.6,
                                mean_discharge=us.UnitfulDischarge(
                                    value=5000, units=us.UnitTypesDischarge.cfs
                                ),
                            ),
                            discharge=us.UnitfulDischarge(
                                value=5000, units=us.UnitTypesDischarge.cfs
                            ),
                        ),
                    ],
                },
            )
        )

        test_db.events.save(event)

        scn = Scenario(
            name="test_scenario",
            event=event.name,
            projection="current",
            strategy="no_measures",
        )
        test_db.scenarios.save(scn)

        return test_db, scn, event
