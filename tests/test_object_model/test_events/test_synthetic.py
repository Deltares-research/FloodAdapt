from datetime import datetime

import object_model.io.unitfulvalue as uv
import pytest
from object_model.hazard.event.forcing.discharge import DischargeConstant
from object_model.hazard.event.forcing.rainfall import RainfallConstant
from object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from object_model.hazard.event.forcing.wind import WindConstant
from object_model.hazard.event.synthetic import SyntheticEvent
from object_model.hazard.interface.models import (
    Mode,
    ShapeType,
    Template,
    TimeModel,
)
from object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from object_model.interface.site import RiverModel


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
                speed=uv.UnitfulVelocity(value=5, units=uv.UnitTypesVelocity.mps),
                direction=uv.UnitfulDirection(
                    value=60, units=uv.UnitTypesDirection.degrees
                ),
            ),
            "RAINFALL": RainfallConstant(
                intensity=uv.UnitfulIntensity(
                    value=20, units=uv.UnitTypesIntensity.mm_hr
                )
            ),
            "DISCHARGE": DischargeConstant(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=uv.UnitfulDischarge(
                        value=5000, units=uv.UnitTypesDischarge.cfs
                    ),
                ),
                discharge=uv.UnitfulDischarge(
                    value=5000, units=uv.UnitTypesDischarge.cfs
                ),
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=uv.UnitfulTime(value=1, units=uv.UnitTypesTime.days),
                        peak_time=uv.UnitfulTime(value=8, units=uv.UnitTypesTime.hours),
                        peak_value=uv.UnitfulLength(
                            value=1, units=uv.UnitTypesLength.meters
                        ),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=uv.UnitfulLength(
                        value=1, units=uv.UnitTypesLength.meters
                    ),
                    harmonic_period=uv.UnitfulTime(
                        value=12.4, units=uv.UnitTypesTime.hours
                    ),
                    harmonic_phase=uv.UnitfulTime(
                        value=0, units=uv.UnitTypesTime.hours
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
                speed=uv.UnitfulVelocity(value=5, units=uv.UnitTypesVelocity.mps),
                direction=uv.UnitfulDirection(
                    value=60, units=uv.UnitTypesDirection.degrees
                ),
            ),
            "RAINFALL": RainfallConstant(
                intensity=uv.UnitfulIntensity(
                    value=20, units=uv.UnitTypesIntensity.mm_hr
                )
            ),
            "DISCHARGE": DischargeConstant(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=uv.UnitfulDischarge(
                        value=5000, units=uv.UnitTypesDischarge.cfs
                    ),
                ),
                discharge=uv.UnitfulDischarge(
                    value=5000, units=uv.UnitTypesDischarge.cfs
                ),
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=uv.UnitfulTime(value=1, units=uv.UnitTypesTime.days),
                        peak_time=uv.UnitfulTime(value=8, units=uv.UnitTypesTime.hours),
                        peak_value=uv.UnitfulLength(
                            value=1, units=uv.UnitTypesLength.meters
                        ),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=uv.UnitfulLength(
                        value=1, units=uv.UnitTypesLength.meters
                    ),
                    harmonic_period=uv.UnitfulTime(
                        value=12.4, units=uv.UnitTypesTime.hours
                    ),
                    harmonic_phase=uv.UnitfulTime(
                        value=0, units=uv.UnitTypesTime.hours
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
