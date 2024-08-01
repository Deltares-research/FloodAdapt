from datetime import datetime

import pytest

from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesVelocity,
)


class TestEventSet:
    @pytest.fixture()
    def test_event_all_constant_no_waterlevels(self):
        attrs = {
            "name": "test_historical_nearshore",
            "time": TimeModel(
                start_time=datetime(2020, 1, 1),
                end_time=datetime(2020, 1, 2),
            ),
            "template": Template.Historical,
            "mode": Mode.single_event,
            "forcings": {
                "WIND": WindConstant(
                    speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                    direction=UnitfulDirection(
                        value=60, units=UnitTypesDirection.degrees
                    ),
                ),
                "RAINFALL": RainfallConstant(
                    intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
                ),
                "DISCHARGE": DischargeConstant(
                    discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
                ),
            },
        }
        return attrs

    @pytest.fixture()
    def test_event_no_waterlevels(self, test_event_all_constant_no_waterlevels):
        return HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)
