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
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
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
    UnitTypesVelocity,
)


@pytest.fixture()
def test_projection_event_all_synthetic(self):
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
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type="triangle",
                        duration=UnitfulTime(value=1, units="days"),
                        peak_time=UnitfulTime(value=8, units="hours"),
                        peak_value=UnitfulLength(value=1, units="meters"),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=UnitfulLength(value=1, units="meters"),
                    harmonic_period=UnitfulTime(value=12.4, units="hours"),
                    harmonic_phase=UnitfulTime(value=0, units="hours"),
                ),
            ),
        },
    }
    return attrs


@pytest.fixture()
def test_event_all_synthetic(self):
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
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type="triangle",
                        duration=UnitfulTime(value=1, units="days"),
                        peak_time=UnitfulTime(value=8, units="hours"),
                        peak_value=UnitfulLength(value=1, units="meters"),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=UnitfulLength(value=1, units="meters"),
                    harmonic_period=UnitfulTime(value=12.4, units="hours"),
                    harmonic_phase=UnitfulTime(value=0, units="hours"),
                ),
            ),
        },
    }
    return attrs


class TestSyntheticEvent:
    # TODO add test for for eventmodel validators

    @pytest.fixture()
    def test_event(self, test_event_all_synthetic):
        return SyntheticEvent.load_dict(test_event_all_synthetic)

    def test_save_event_toml(self, test_event_all_synthetic, tmp_path):
        path = tmp_path / "test_event.toml"
        test_event = SyntheticEvent.load_dict(test_event_all_synthetic)
        test_event.save(path)
        assert path.exists()

    def test_load_dict(self, test_event_all_synthetic):
        loaded_event = SyntheticEvent.load_dict(test_event_all_synthetic)

        assert loaded_event.attrs.name == test_event_all_synthetic["name"]
        assert loaded_event.attrs.time == test_event_all_synthetic["time"]
        assert loaded_event.attrs.template == test_event_all_synthetic["template"]
        assert loaded_event.attrs.mode == test_event_all_synthetic["mode"]
        assert loaded_event.attrs.forcings == test_event_all_synthetic["forcings"]

    def test_load_file(self, test_event_all_synthetic, tmp_path):
        path = tmp_path / "test_event.toml"
        saved_event = SyntheticEvent.load_dict(test_event_all_synthetic)
        saved_event.save(path)
        assert path.exists()

        loaded_event = SyntheticEvent.load_file(path)

        assert loaded_event == saved_event
