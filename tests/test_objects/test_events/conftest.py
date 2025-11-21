import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.config.hazard import RiverModel
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects import (
    EventSet,
    HistoricalEvent,
    HurricaneEvent,
    Scenario,
    SubEventModel,
    SyntheticEvent,
)
from flood_adapt.objects import unit_system as us
from flood_adapt.objects.data_container import (
    CycloneTrackContainer,
)
from flood_adapt.objects.forcing import (
    DischargeConstant,
    DischargeCSV,
    ForcingType,
    RainfallConstant,
    RainfallCSV,
    RainfallMeteo,
    RainfallTrack,
    ShapeType,
    SurgeModel,
    TideModel,
    TimeseriesFactory,
    WaterlevelCSV,
    WaterlevelModel,
    WaterlevelSynthetic,
    WindConstant,
    WindCSV,
    WindMeteo,
    WindTrack,
)
from flood_adapt.objects.forcing.time_frame import (
    REFERENCE_TIME,
    TimeFrame,
)
from tests.data.create_test_input import (
    _create_cyclone_track_container,
    _create_hurricane_event,
)
from tests.test_objects.test_measures.conftest import (
    test_buyout,
    test_elevate,
    test_floodproof,
    test_green_infra,
    test_pump,
)

__all__ = [
    "test_buyout",
    "test_elevate",
    "test_floodproof",
    "test_green_infra",
    "test_pump",
]


@pytest.fixture()
def _wind_csv(dummy_2d_timeseries_df: pd.DataFrame):
    tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
    dummy_2d_timeseries_df.to_csv(tmp_path)

    return WindCSV(
        path=tmp_path,
    )


@pytest.fixture()
def _rainfall_csv(dummy_1d_timeseries_df: pd.DataFrame):
    tmp_path = Path(tempfile.gettempdir()) / "rainfall.csv"
    dummy_1d_timeseries_df.to_csv(tmp_path)

    return RainfallCSV(
        path=tmp_path,
    )


@pytest.fixture()
def _waterlevel_csv(dummy_1d_timeseries_df: pd.DataFrame):
    tmp_path = Path(tempfile.gettempdir()) / "waterlevel.csv"
    dummy_1d_timeseries_df.to_csv(tmp_path)

    return WaterlevelCSV(
        path=tmp_path,
    )


@pytest.fixture()
def test_event_all_csv(_wind_csv, _rainfall_csv, _waterlevel_csv):
    return HistoricalEvent(
        name="test_synthetic_nearshore",
        time=TimeFrame(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        forcings={
            ForcingType.WIND: [
                _wind_csv,
            ],
            ForcingType.RAINFALL: [
                _rainfall_csv,
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
                )
            ],
            ForcingType.WATERLEVEL: [
                _waterlevel_csv,
            ],
        },
    )


@pytest.fixture()
def test_event_all_synthetic():
    return SyntheticEvent(
        name="test_synthetic_nearshore",
        time=TimeFrame(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        forcings={
            ForcingType.WIND: [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                )
            ],
            ForcingType.RAINFALL: [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=20, units=us.UnitTypesIntensity.mm_hr
                    )
                )
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
                )
            ],
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=1, units=us.UnitTypesLength.meters
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                        harmonic_period=us.UnitfulTime(
                            value=12.4, units=us.UnitTypesTime.hours
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                )
            ],
        },
    )


@pytest.fixture()
def setup_hurricane_event(
    cyclone_track_container: CycloneTrackContainer,
) -> tuple[HurricaneEvent, Path]:
    cyclone_track_container.data.include_rainfall = True
    event = HurricaneEvent(
        name="hurricane",
        time=TimeFrame(),
        track_name="IAN",
        forcings={
            ForcingType.WATERLEVEL: [WaterlevelModel()],
            ForcingType.WIND: [WindTrack(track=cyclone_track_container)],
            ForcingType.RAINFALL: [RainfallTrack(track=cyclone_track_container)],
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
    return event


@pytest.fixture()
def setup_hurricane_scenario(
    test_db: IDatabase, setup_hurricane_event: HurricaneEvent
) -> tuple[Scenario, HurricaneEvent]:
    event = setup_hurricane_event
    scn = Scenario(
        name="test_scenario",
        event=event.name,
        projection="current",
        strategy="no_measures",
    )
    test_db.events.save(event)
    test_db.scenarios.save(scn)
    return scn, event


@pytest.fixture()
def setup_nearshore_event(dummy_1d_timeseries_df: pd.DataFrame):
    def _tmp_timeseries_csv(name: str):
        tmp_csv = Path(tempfile.gettempdir()) / name
        dummy_1d_timeseries_df.to_csv(tmp_csv)
        return Path(tmp_csv)

    time = TimeFrame(
        start_time=REFERENCE_TIME, end_time=REFERENCE_TIME + timedelta(hours=2)
    )

    return HistoricalEvent(
        name="nearshore_gauged",
        time=time,
        forcings={
            ForcingType.WATERLEVEL: [
                WaterlevelCSV(path=_tmp_timeseries_csv("waterlevel.csv"))
            ],
            ForcingType.WIND: [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                )
            ],
            ForcingType.RAINFALL: [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=20, units=us.UnitTypesIntensity.mm_hr
                    )
                )
            ],
            ForcingType.DISCHARGE: [
                DischargeCSV(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    path=_tmp_timeseries_csv("discharge.csv"),
                ),
            ],
        },
    )


@pytest.fixture()
def setup_offshore_meteo_event():
    time = TimeFrame(
        start_time=REFERENCE_TIME, end_time=REFERENCE_TIME + timedelta(hours=2)
    )
    return HistoricalEvent(
        name="offshore_meteo",
        time=time,
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


@pytest.fixture()
def setup_offshore_scenario(
    setup_offshore_meteo_event: HistoricalEvent, test_db: IDatabase
):
    return Scenario(
        name="offshore_meteo",
        event=setup_offshore_meteo_event.name,
        projection="current",
        strategy="no_measures",
    )


@pytest.fixture()
def test_sub_event() -> SyntheticEvent:
    return SyntheticEvent(
        name="subevent",
        time=TimeFrame(),
        forcings={
            ForcingType.WIND: [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                )
            ],
            ForcingType.RAINFALL: [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=2, units=us.UnitTypesIntensity.mm_hr
                    )
                )
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
                )
            ],
            ForcingType.WATERLEVEL: [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=TimeseriesFactory.from_args(
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=1, units=us.UnitTypesLength.meters
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                )
            ],
        },
    )


@pytest.fixture()
def test_eventset(
    test_sub_event: SyntheticEvent,
    setup_nearshore_event: HistoricalEvent,
    # setup_offshore_meteo_event: HistoricalEvent, # uncomment when hydromt-sfincs 1.3.0 is released
) -> EventSet:
    sub_event_models: list[SubEventModel] = []
    sub_events = []

    hurricane = _create_hurricane_event(
        "sub_hurricane", _create_cyclone_track_container()
    )
    synthetic = test_sub_event
    historical_nearshore = setup_nearshore_event
    # historical_offshore = setup_offshore_meteo_event # uncomment when hydromt-sfincs 1.3.0 is released

    for i, event in enumerate(
        [
            hurricane,
            synthetic,
            historical_nearshore,
        ]  # , historical_offshore] # uncomment when hydromt-sfincs 1.3.0 is released
    ):
        event.name = f"{event.name}_{i + 1:04d}"
        sub_event_models.append(SubEventModel(name=event.name, frequency=i + 1))
        sub_events.append(event)

    event_set = EventSet(
        name="test_eventset",
        sub_events=sub_event_models,
    )
    event_set.load_sub_events(sub_events=sub_events)

    return event_set


@pytest.fixture()
def setup_eventset_scenario(
    test_db: IDatabase,
    test_eventset,
    dummy_projection,
    dummy_strategy,
):
    test_db.projections.save(dummy_projection)
    for measure in dummy_strategy.get_measures():
        test_db.measures.save(measure)
    test_db.strategies.save(dummy_strategy)
    test_db.events.save(test_eventset)

    scn = Scenario(
        name="test_scenario",
        event=test_eventset.name,
        projection=dummy_projection.name,
        strategy=dummy_strategy.name,
    )
    test_db.scenarios.save(scn)

    return test_db, scn, test_eventset
