from datetime import datetime

import pytest

from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.event.synthetic import SyntheticEvent
from flood_adapt.object_model.hazard.interface.models import (
    Mode,
    ShapeType,
    Template,
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.site import RiverModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesTime,
    UnitTypesVelocity,
)


@pytest.fixture()
def test_projection_event_all_synthetic():
    attrs = {
        "name": "test_historical_nearshore",
        "time": TimeModel(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        "template": Template.Synthetic,
        "mode": Mode.single_event,
        "forcings": {
            "WIND": WindConstant(
                speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                direction=UnitfulDirection(value=60, units=UnitTypesDirection.degrees),
            ),
            "RAINFALL": RainfallConstant(
                intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
            ),
            "DISCHARGE": DischargeConstant(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=UnitfulDischarge(
                        value=5000, units=UnitTypesDischarge.cfs
                    ),
                ),
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs),
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=UnitfulTime(value=1, units=UnitTypesTime.days),
                        peak_time=UnitfulTime(value=8, units=UnitTypesTime.hours),
                        peak_value=UnitfulLength(value=1, units=UnitTypesLength.meters),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=UnitfulLength(
                        value=1, units=UnitTypesLength.meters
                    ),
                    harmonic_period=UnitfulTime(value=12.4, units=UnitTypesTime.hours),
                    harmonic_phase=UnitfulTime(value=0, units=UnitTypesTime.hours),
                ),
            ),
        },
    }
    return attrs


@pytest.fixture()
def test_event_all_synthetic():
    attrs = {
        "name": "test_synthetic_nearshore",
        "time": TimeModel(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        "template": Template.Synthetic,
        "mode": Mode.single_event,
        "forcings": {
            "WIND": WindConstant(
                speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                direction=UnitfulDirection(value=60, units=UnitTypesDirection.degrees),
            ),
            "RAINFALL": RainfallConstant(
                intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
            ),
            "DISCHARGE": DischargeConstant(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=UnitfulDischarge(
                        value=5000, units=UnitTypesDischarge.cfs
                    ),
                ),
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs),
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=UnitfulTime(value=1, units=UnitTypesTime.days),
                        peak_time=UnitfulTime(value=8, units=UnitTypesTime.hours),
                        peak_value=UnitfulLength(value=1, units=UnitTypesLength.meters),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=UnitfulLength(
                        value=1, units=UnitTypesLength.meters
                    ),
                    harmonic_period=UnitfulTime(value=12.4, units=UnitTypesTime.hours),
                    harmonic_phase=UnitfulTime(value=0, units=UnitTypesTime.hours),
                ),
            ),
        },
    }
    return SyntheticEvent.load_dict(attrs)


class TestSyntheticEvent:
    # TODO add test for for eventmodel validators
    def test_save_event_toml(self, test_event_all_synthetic, tmp_path):
        path = tmp_path / "test_event.toml"
        test_event = test_event_all_synthetic
        test_event.save(path)
        assert path.exists()

    def test_load_file(self, test_event_all_synthetic, tmp_path):
        path = tmp_path / "test_event.toml"
        saved_event = test_event_all_synthetic
        saved_event.save(path)
        assert path.exists()

        loaded_event = SyntheticEvent.load_file(path)

        assert loaded_event == saved_event
