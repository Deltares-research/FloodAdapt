from datetime import datetime

import pytest

from flood_adapt.object_model.hazard.event.synthetic import SyntheticEvent
from flood_adapt.object_model.hazard.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.interface.events import (
    Mode,
    Template,
)
from flood_adapt.object_model.hazard.interface.forcing import ShapeType
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.site import RiverModel
from flood_adapt.object_model.io import unit_system as us


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
                speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                direction=us.UnitfulDirection(
                    value=60, units=us.UnitTypesDirection.degrees
                ),
            ),
            "RAINFALL": RainfallConstant(
                intensity=us.UnitfulIntensity(
                    value=20, units=us.UnitTypesIntensity.mm_hr
                )
            ),
            "DISCHARGE": {
                "cooper": DischargeConstant(
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
            },
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                        peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
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
                speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                direction=us.UnitfulDirection(
                    value=60, units=us.UnitTypesDirection.degrees
                ),
            ),
            "RAINFALL": RainfallConstant(
                intensity=us.UnitfulIntensity(
                    value=20, units=us.UnitTypesIntensity.mm_hr
                )
            ),
            "DISCHARGE": {
                "cooper": DischargeConstant(
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
            },
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                        peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
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
