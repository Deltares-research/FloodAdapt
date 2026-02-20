from pathlib import Path

import pytest

from flood_adapt.config.hazard import RiverModel
from flood_adapt.objects.events.event_set import (
    EventSet,
    SubEventModel,
)
from flood_adapt.objects.events.historical import HistoricalEvent
from flood_adapt.objects.events.synthetic import (
    SyntheticEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import DischargeConstant
from flood_adapt.objects.forcing.forcing import (
    ForcingType,
)
from flood_adapt.objects.forcing.rainfall import RainfallConstant
from flood_adapt.objects.forcing.time_frame import (
    TimeFrame,
)
from flood_adapt.objects.forcing.timeseries import (
    ShapeType,
    TimeseriesFactory,
)
from flood_adapt.objects.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import WindConstant
from tests.data.create_test_input import _create_hurricane_event
from tests.test_objects.test_events.test_historical import (
    setup_nearshore_event,
)

__all__ = ["setup_nearshore_event"]


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
) -> EventSet:
    sub_event_models: list[SubEventModel] = []
    sub_events = []

    hurricane = _create_hurricane_event("sub_hurricane")
    synthetic = test_sub_event
    historical_nearshore = setup_nearshore_event

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


def test_save_reload_eventset(test_eventset: EventSet, tmp_path: Path):
    path = tmp_path / f"{test_eventset.name}.toml"
    test_eventset.save(path)
    reloaded = EventSet.load_file(path)
    assert reloaded == test_eventset


def test_save_all_sub_events(test_eventset: EventSet, tmp_path: Path):
    path = tmp_path / "test_eventset.toml"
    test_eventset.save(toml_path=path)
    for sub_event in test_eventset.sub_events:
        assert (path.parent / sub_event.name / f"{sub_event.name}.toml").exists()
